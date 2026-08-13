from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ContentItem, Creator


USER_AGENT = "tech-content-weekly/0.2 (+personal weekly report)"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def _json(url: str) -> dict:
    return json.loads(_get(url))


def _iso_duration(value: str) -> int | None:
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def collect_youtube(creator: Creator, since: datetime) -> list[ContentItem]:
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY 未配置")
    query = urllib.parse.urlencode({"part": "contentDetails", "id": creator.id, "key": key})
    channel = _json(f"https://www.googleapis.com/youtube/v3/channels?{query}")
    rows = channel.get("items", [])
    if not rows:
        raise RuntimeError(f"YouTube channel 未找到: {creator.id}")
    uploads = rows[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    query = urllib.parse.urlencode({"part": "snippet,contentDetails", "playlistId": uploads, "maxResults": 50, "key": key})
    playlist = _json(f"https://www.googleapis.com/youtube/v3/playlistItems?{query}")
    candidates = []
    for row in playlist.get("items", []):
        published = datetime.fromisoformat(row["contentDetails"]["videoPublishedAt"].replace("Z", "+00:00"))
        if published >= since:
            candidates.append((row["contentDetails"]["videoId"], row["snippet"], published))
    if not candidates:
        return []
    query = urllib.parse.urlencode({"part": "contentDetails,statistics,snippet", "id": ",".join(row[0] for row in candidates), "key": key})
    details = _json(f"https://www.googleapis.com/youtube/v3/videos?{query}")
    by_id = {row["id"]: row for row in details.get("items", [])}
    result = []
    for video_id, snippet, published in candidates:
        row = by_id.get(video_id, {})
        stats = row.get("statistics", {})
        detail_snippet = row.get("snippet", snippet)
        result.append(ContentItem(
            creator.name, "youtube", detail_snippet.get("title", snippet.get("title", video_id)),
            f"https://www.youtube.com/watch?v={video_id}", published,
            _iso_duration(row.get("contentDetails", {}).get("duration", "")),
            int(stats["viewCount"]) if "viewCount" in stats else None,
            int(stats["commentCount"]) if "commentCount" in stats else None,
            detail_snippet.get("description", "")[:240].replace("\n", " "),
        ))
    return result


def _text(node: ET.Element, *names: str) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def _parse_date(value: str) -> datetime:
    from email.utils import parsedate_to_datetime
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def _rss_items(creator: Creator, data: bytes) -> list[ContentItem]:
    root = ET.fromstring(data)
    result = []
    if root.tag.endswith("feed"):
        ns = {"a": "http://www.w3.org/2005/Atom"}
        nodes = root.findall("a:entry", ns)
        for node in nodes:
            link = next((item.get("href", "") for item in node.findall("a:link", ns) if item.get("rel", "alternate") == "alternate"), "")
            result.append(ContentItem(creator.name, creator.platform, _text(node, "{http://www.w3.org/2005/Atom}title"), link,
                                      _parse_date(_text(node, "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")),
                                      description=_text(node, "{http://www.w3.org/2005/Atom}summary")))
    else:
        for node in root.findall(".//item"):
            duration = _text(node, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
            parts = [int(part) for part in duration.split(":") if part.isdigit()]
            seconds = (parts[0] * 3600 + parts[1] * 60 + parts[2]) if len(parts) == 3 else (parts[0] * 60 + parts[1] if len(parts) == 2 else None)
            result.append(ContentItem(creator.name, creator.platform, _text(node, "title"), _text(node, "link"),
                                      _parse_date(_text(node, "pubDate", "{http://purl.org/dc/elements/1.1/}date")),
                                      seconds, description=re.sub(r"<[^>]+>", " ", _text(node, "description"))[:240]))
    return result


def collect_feed(creator: Creator, since: datetime) -> list[ContentItem]:
    if not creator.feed_url:
        raise RuntimeError(f"{creator.platform} 创作者未配置 feed_url")
    return [item for item in _rss_items(creator, _get(creator.feed_url)) if item.published >= since]


def _cache_path(cache_dir: Path, creator: Creator) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", creator.id)
    return cache_dir / f"{creator.platform}-{safe_id}.json"


def collect_all(creators: tuple[Creator, ...], since: datetime, cache_dir: Path) -> tuple[list[ContentItem], list[str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    items, warnings = [], []
    for creator in creators:
        if not creator.enabled:
            continue
        cache = _cache_path(cache_dir, creator)
        try:
            fresh = collect_youtube(creator, since) if creator.platform == "youtube" else collect_feed(creator, since)
            cache.write_text(json.dumps([item.as_json() for item in fresh], ensure_ascii=False, indent=2), encoding="utf-8")
            items.extend(fresh)
        except Exception as error:
            message = str(error)
            key = os.getenv("YOUTUBE_API_KEY", "").strip()
            if key:
                message = message.replace(key, "***")
            warnings.append(f"{creator.name} ({creator.platform}): {type(error).__name__}: {message}")
            if cache.exists():
                cached = [ContentItem.from_json(row) for row in json.loads(cache.read_text(encoding="utf-8"))]
                items.extend(item for item in cached if item.published >= since)
                warnings.append(f"{creator.name}: 已使用最近缓存")
    return items, warnings
