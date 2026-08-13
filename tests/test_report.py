from datetime import datetime, timezone
from pathlib import Path
import unittest

from tech_content_weekly.analytics import monthly_top, weekly_items
from tech_content_weekly.cli import _timezone
from tech_content_weekly.config import load_config
from tech_content_weekly.report import render_html, render_markdown
from tech_content_weekly.sample_data import build_sample_items


ROOT = Path(__file__).resolve().parents[1]


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 13, 18, tzinfo=timezone.utc)
        self.config = load_config(ROOT / "config.toml")
        self.items = build_sample_items(self.now)

    def test_config_contains_requested_creators(self):
        self.assertEqual(
            [creator.name for creator in self.config.creators],
            [
                "opus精译",
                "张小珺商业访谈录",
                "3Blue1Brown",
                "Dwarkesh Patel",
                "自习室 STUDY ROOM",
            ],
        )

    def test_weekly_filter_and_monthly_top(self):
        weekly = weekly_items(self.items, self.now, 7)
        self.assertEqual(len(weekly), 5)
        top = monthly_top(self.items, self.now, 30, 3)
        self.assertEqual(len(top["opus精译"]), 3)
        self.assertGreaterEqual(
            top["opus精译"][0].view_count,
            top["opus精译"][1].view_count,
        )

    def test_html_contains_metrics_podcast_caveat_and_wide_layout(self):
        result = render_html(
            self.config.report.title, self.config.creators, self.items, self.now
        )
        self.assertIn("max-width:1080px", result)
        self.assertIn("linear-gradient(135deg,#0b3d2e,#176b4d)", result)
        self.assertIn("border-bottom:2px solid #197552", result)
        self.assertNotIn("#1772f6", result)
        self.assertIn("哔哩哔哩本周更新", result)
        self.assertIn("YouTube本周更新", result)
        self.assertIn("播客 / 小宇宙本周更新", result)
        self.assertIn("播放 128.6 万", result)
        self.assertIn("评论 4,832", result)
        self.assertIn("播客公开 RSS 通常没有统一播放和评论指标", result)
        self.assertIn("@media(max-width:600px)", result)

    def test_ai_markdown_markers_render_as_html(self):
        result = render_html(
            self.config.report.title, self.config.creators, self.items, self.now,
            insight="### 优先观看\n- **编译器**更新与`性能分析`",
            provider="DeepSeek", model="deepseek-chat",
        )
        self.assertIn("<h3>优先观看</h3>", result)
        self.assertIn("<li><strong>编译器</strong>更新与<code>性能分析</code></li>", result)
        self.assertNotIn("**编译器**", result)
        self.assertIn("本期内容导读由 DeepSeek 模型 <code>deepseek-chat</code> 生成", result)

    def test_plain_markdown_includes_model_attribution(self):
        result = render_markdown(
            self.config.report.title, self.config.creators, self.items, self.now,
            insight="摘要", provider="OpenAI", model="gpt-5-mini",
        )
        self.assertIn("本期内容导读由 OpenAI 模型 `gpt-5-mini` 生成", result)

    def test_shanghai_timezone_fallback_is_available(self):
        shanghai_time = datetime(2026, 8, 13, 12, tzinfo=_timezone("Asia/Shanghai"))
        self.assertEqual(shanghai_time.utcoffset().total_seconds(), 8 * 3600)

    def test_action_runs_wednesday_0700_shanghai(self):
        workflow = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 23 * * 2"', workflow)
        self.assertIn("Wednesday 07:00 Asia/Shanghai", workflow)


if __name__ == "__main__":
    unittest.main()
