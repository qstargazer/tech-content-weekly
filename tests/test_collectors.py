from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest
from unittest.mock import patch

from tech_content_weekly.collectors import _iso_duration, _rss_items, collect_all, collect_feed, collect_youtube
from tech_content_weekly.models import ContentItem, Creator


class CollectorTest(unittest.TestCase):
    def test_duration_and_rss(self):
        self.assertEqual(_iso_duration("PT1H2M3S"), 3723)
        creator = Creator("节目", "podcast", "show", "https://show", feed_url="https://feed")
        xml = b'''<rss><channel><item><title>Episode 1</title><link>https://show/1</link>
        <pubDate>Thu, 13 Aug 2026 08:00:00 GMT</pubDate><itunes:duration xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">42:05</itunes:duration>
        <description><![CDATA[<b>AI compiler</b> news]]></description></item></channel></rss>'''
        item = _rss_items(creator, xml)[0]
        self.assertEqual(item.duration_seconds, 2525)
        self.assertEqual(item.title, "Episode 1")

    @patch.dict(os.environ, {"YOUTUBE_API_KEY": "secret"}, clear=False)
    @patch("tech_content_weekly.collectors._json")
    def test_youtube_uses_official_api_fields(self, mock_json):
        mock_json.side_effect = [
            {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]},
            {"items": [{"contentDetails": {"videoPublishedAt": "2026-08-12T08:00:00Z", "videoId": "v1"}, "snippet": {"title": "Video"}}]},
            {"items": [{"id": "v1", "contentDetails": {"duration": "PT12M5S"}, "statistics": {"viewCount": "1200", "commentCount": "18"}, "snippet": {"title": "Video", "description": "desc"}}]},
        ]
        creator = Creator("频道", "youtube", "UC1", "https://youtube.test")
        rows = collect_youtube(creator, datetime(2026, 8, 1, tzinfo=timezone.utc))
        self.assertEqual((rows[0].duration_seconds, rows[0].view_count, rows[0].comment_count), (725, 1200, 18))

    @patch("tech_content_weekly.collectors.collect_feed", side_effect=RuntimeError("offline"))
    def test_one_source_failure_uses_cache_and_does_not_stop_others(self, _mock):
        creator = Creator("节目", "podcast", "show", "https://show", feed_url="https://feed")
        cached = ContentItem("节目", "podcast", "Cached", "https://show/1", datetime(2026, 8, 12, tzinfo=timezone.utc))
        with TemporaryDirectory() as raw:
            path = Path(raw) / "podcast-show.json"
            path.write_text(json.dumps([cached.as_json()], ensure_ascii=False), encoding="utf-8")
            rows, warnings = collect_all((creator,), datetime(2026, 8, 1, tzinfo=timezone.utc), Path(raw))
        self.assertEqual(rows[0].title, "Cached")
        self.assertTrue(any("已使用最近缓存" in row for row in warnings))

    @patch.dict(os.environ, {"RSSHUB_BASE_URL": "http://rsshub:1200", "RSSHUB_ACCESS_KEY": "secret"}, clear=False)
    @patch("tech_content_weekly.collectors._get")
    def test_rsshub_base_url_is_expanded(self, mock_get):
        mock_get.return_value = b'''<rss><channel><item><title>Video</title><link>https://bilibili.com/video/1</link>
        <pubDate>Thu, 13 Aug 2026 08:00:00 GMT</pubDate></item></channel></rss>'''
        creator = Creator("UP", "bilibili", "1", "https://space.bilibili.com/1", feed_url="$RSSHUB_BASE_URL/bilibili/user/video/1?key=$RSSHUB_ACCESS_KEY")
        collect_feed(creator, datetime(2026, 8, 1, tzinfo=timezone.utc))
        mock_get.assert_called_once_with("http://rsshub:1200/bilibili/user/video/1?key=secret")

    @patch("tech_content_weekly.collectors.collect_feed")
    def test_short_video_is_filtered_but_unknown_duration_is_kept(self, mock_feed):
        creator = Creator("UP", "bilibili", "1", "https://space.bilibili.com/1", feed_url="https://feed")
        base = datetime(2026, 8, 12, tzinfo=timezone.utc)
        mock_feed.return_value = [
            ContentItem("UP", "bilibili", "short", "https://short", base, 599),
            ContentItem("UP", "bilibili", "long", "https://long", base, 600),
            ContentItem("UP", "bilibili", "unknown", "https://unknown", base),
        ]
        with TemporaryDirectory() as raw:
            rows, _ = collect_all((creator,), datetime(2026, 8, 1, tzinfo=timezone.utc), Path(raw), 600)
        self.assertEqual([row.title for row in rows], ["long", "unknown"])


if __name__ == "__main__":
    unittest.main()
