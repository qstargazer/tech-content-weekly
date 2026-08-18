from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ContentItem, Creator


USER_AGENT = "tech-content-weekly/0.3 (+personal weekly report)"

_RETRIABLE_CODES = {429, 500, 502, 503, 504}


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in _RETRIABLE_CODES:
                raise
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _json(url: str) -> dict:
    return json.loads(_get(url))


def _iso_duration(value: str) -> int | None:
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _clock_duration(value: str) -> int | None:
    parts = [part.strip() for part in (value or "").split(":")]
    if not parts or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    if len(numbers) == 1:
        return numbers[0]
    return None


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
    candidates = []
    page_token = ""
    while True:
        params = {"part": "snippet,contentDetails", "playlistId": uploads, "maxResults": 50, "key": key}
        if page_token:
            params["pageToken"] = page_token
        playlist = _json(f"https://www.googleapis.com/youtube/v3/playlistItems?{urllib.parse.urlencode(params)}")
        page_candidates = []
        for row in playlist.get("items", []):
            published = datetime.fromisoformat(row["contentDetails"]["videoPublishedAt"].replace("Z", "+00:00"))
            if published >= since:
                page_candidates.append((row["contentDetails"]["videoId"], row["snippet"], published))
        candidates.extend(page_candidates)
        next_token = playlist.get("nextPageToken")
        if not next_token or not page_candidates:
            break
        page_token = next_token
    if not candidates:
        return []
    details = {}
    for start in range(0, len(candidates), 50):
        chunk = candidates[start:start + 50]
        query = urllib.parse.urlencode({"part": "contentDetails,statistics,snippet", "id": ",".join(row[0] for row in chunk), "key": key})
        details.update({row["id"]: row for row in _json(f"https://www.googleapis.com/youtube/v3/videos?{query}").get("items", [])})
    result = []
    for video_id, snippet, published in candidates:
        row = details.get(video_id, {})
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


def _rss_duration(node: ET.Element) -> int | None:
    value = _text(
        node,
        "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration",
        "duration",
        "{http://search.yahoo.com/mrss/}duration",
    )
    if value:
        return _clock_duration(value)
    for child in node.iter():
        raw = child.attrib.get("duration", "")
        if raw:
            parsed = _clock_duration(raw)
            if parsed is not None:
                return parsed
    return None


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    from email.utils import parsedate_to_datetime
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def _feed_updated(root: ET.Element) -> datetime | None:
    if root.tag.endswith("feed"):
        return _parse_date(_text(root, "{http://www.w3.org/2005/Atom}updated"))
    for name in ("lastBuildDate", "pubDate"):
        node = root.find(f".//{name}")
        if node is not None and node.text:
            return _parse_date(node.text.strip())
    return None


def _rss_items(creator: Creator, data: bytes) -> list[ContentItem]:
    root = ET.fromstring(data)
    fallback = _feed_updated(root)
    result = []
    if root.tag.endswith("feed"):
        ns = {"a": "http://www.w3.org/2005/Atom"}
        nodes = root.findall("a:entry", ns)
        for node in nodes:
            published = _parse_date(_text(node, "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")) or fallback
            if published is None:
                continue
            link = next((item.get("href", "") for item in node.findall("a:link", ns) if item.get("rel", "alternate") == "alternate"), "")
            result.append(ContentItem(creator.name, creator.platform, _text(node, "{http://www.w3.org/2005/Atom}title"), link,
                                      published,
                                      _rss_duration(node), description=_text(node, "{http://www.w3.org/2005/Atom}summary")))
    else:
        for node in root.findall(".//item"):
            published = _parse_date(_text(node, "pubDate", "{http://purl.org/dc/elements/1.1/}date")) or fallback
            if published is None:
                continue
            seconds = _rss_duration(node)
            result.append(ContentItem(creator.name, creator.platform, _text(node, "title"), _text(node, "link"),
                                      published,
                                      seconds, description=re.sub(r"<[^>]+>", " ", _text(node, "description"))[:240]))
    return result


def collect_feed(creator: Creator, since: datetime) -> list[ContentItem]:
    if not creator.feed_url:
        raise RuntimeError(f"{creator.platform} 创作者未配置 feed_url")
    feed_url = os.path.expandvars(creator.feed_url).strip()
    for variable, label in (("$RSSHUB_BASE_URL", "RSSHUB_BASE_URL"), ("$RSSHUB_ACCESS_KEY", "RSSHUB_ACCESS_KEY")):
        if variable in feed_url:
            raise RuntimeError(f"{label} 未配置")
    return [item for item in _rss_items(creator, _get(feed_url)) if item.published >= since]


def _cache_path(cache_dir: Path, creator: Creator) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", creator.id)
    return cache_dir / f"{creator.platform}-{safe_id}.json"


def _collect_one(
    creator: Creator, since: datetime, cache_dir: Path, min_video_duration_seconds: int
) -> tuple[list[ContentItem], list[str]]:
    cache = _cache_path(cache_dir, creator)
    try:
        fresh = collect_youtube(creator, since) if creator.platform == "youtube" else collect_feed(creator, since)
        if creator.platform in {"youtube", "bilibili"}:
            fresh = [item for item in fresh if item.duration_seconds is None or item.duration_seconds >= min_video_duration_seconds]
        cache.write_text(json.dumps([item.as_json() for item in fresh], ensure_ascii=False, indent=2), encoding="utf-8")
        return fresh, []
    except Exception as error:
        message = str(error)
        key = os.getenv("YOUTUBE_API_KEY", "").strip()
        if key:
            message = message.replace(key, "***")
        warnings = [f"{creator.name} ({creator.platform}): {type(error).__name__}: {message}"]
        fallback = []
        if cache.exists():
            cached = [ContentItem.from_json(row) for row in json.loads(cache.read_text(encoding="utf-8"))]
            fallback = [item for item in cached if item.published >= since]
            if creator.platform in {"youtube", "bilibili"}:
                fallback = [item for item in fallback if item.duration_seconds is None or item.duration_seconds >= min_video_duration_seconds]
            warnings.append(f"{creator.name}: 已使用最近缓存")
        return fallback, warnings


def collect_all(
    creators: tuple[Creator, ...], since: datetime, cache_dir: Path,
    min_video_duration_seconds: int = 600,
) -> tuple[list[ContentItem], list[str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    enabled = [creator for creator in creators if creator.enabled]
    if not enabled:
        return [], []
    items, warnings = [], []
    with ThreadPoolExecutor(max_workers=min(8, len(enabled))) as executor:
        futures = [
            executor.submit(_collect_one, creator, since, cache_dir, min_video_duration_seconds)
            for creator in enabled
        ]
        for future in futures:
            fresh, creator_warnings = future.result()
            items.extend(fresh)
            warnings.extend(creator_warnings)
    return items, warnings
