from datetime import datetime, timezone
from pathlib import Path
import unittest

from tech_content_weekly.analytics import monthly_top, weekly_items
from tech_content_weekly.cli import _timezone
from tech_content_weekly.config import load_config
from tech_content_weekly.models import CATEGORY_COMMUTE, CATEGORY_DEEP, Recommendation
from tech_content_weekly.report import render_html, render_markdown
from tech_content_weekly.sample_data import build_sample_items


ROOT = Path(__file__).resolve().parents[1]


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 13, 18, tzinfo=timezone.utc)
        self.config = load_config(ROOT / "config.toml")
        self.items = build_sample_items(self.now)

    def test_config_contains_requested_creators(self):
        video_creators = {
            creator.id: creator.platform
            for creator in self.config.creators
            if creator.platform in {"bilibili", "youtube"}
        }
        self.assertEqual(
            video_creators,
            {
                "163682133": "bilibili",
                "280780745": "bilibili",
                "88461692": "bilibili",
                "517221395": "bilibili",
                "1787393235": "bilibili",
                "3691003189922747": "bilibili",
                "UCYO_jab_esuFRV4b17AJtAw": "youtube",
            },
        )
        bilibili = next(c for c in self.config.creators if c.id == "88461692")
        self.assertEqual(bilibili.name, "3Blue1Brown（B站官方）")
        youtube = next(c for c in self.config.creators if c.id == "UCYO_jab_esuFRV4b17AJtAw")
        self.assertEqual(youtube.name, "3Blue1Brown（YouTube）")
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
        self.assertIn("max-width:1160px", result)
        self.assertIn("linear-gradient(135deg,#0b3d2e,#176b4d)", result)
        self.assertIn("border-bottom:2px solid #197552", result)
        self.assertNotIn("#1772f6", result)
        self.assertIn("<table>", result)
        self.assertIn("<details id=\"bilibili\" class=\"detail\">", result)
        self.assertIn("哔哩哔哩本周更新", result)
        self.assertIn("YouTube本周更新", result)
        self.assertIn("播客 / 小宇宙本周更新", result)
        self.assertIn("18:48 / 128.6 万 / 4,832", result)
        self.assertIn("播客公开 RSS 通常没有统一播放和评论指标", result)
        self.assertIn("@media(max-width:700px)", result)

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

    def test_action_runs_wednesday_friday_sunday_0543_shanghai(self):
        workflow = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "43 21 * * 2,4,6"', workflow)
        self.assertIn("Wednesday/Friday/Sunday 05:43 Asia/Shanghai", workflow)

    def test_html_renders_recommendation_sections(self):
        weekly = weekly_items(self.items, self.now, 7)
        recommendations = [
            Recommendation(item, CATEGORY_COMMUTE, "通勤时收听即可。") for item in weekly[:2]
        ] + [Recommendation(item, CATEGORY_DEEP, "内容较深，需要专注。") for item in weekly[2:4]]
        top_pick = Recommendation(weekly[2], "top", "本周最值得投入。")
        result = render_html(
            self.config.report.title, self.config.creators, self.items, self.now,
            recommendations=recommendations, top_pick=top_pick,
            rec_provider="DeepSeek", rec_model="deepseek-chat",
        )
        self.assertIn("本周推荐", result)
        self.assertIn("本周最值得投入", result)
        self.assertIn("通勤 / 碎片时间", result)
        self.assertIn("需要专门时间深入研究", result)
        self.assertIn("通勤时收听即可。", result)
        self.assertIn("内容较深，需要专注。", result)
        self.assertIn("场景分类由 DeepSeek 模型", result)

    def test_markdown_renders_recommendations(self):
        weekly = weekly_items(self.items, self.now, 7)
        recommendations = [Recommendation(weekly[0], CATEGORY_COMMUTE, "适合通勤。")]
        result = render_markdown(
            self.config.report.title, self.config.creators, self.items, self.now,
            recommendations=recommendations, rec_provider="OpenAI", rec_model="gpt-5-mini",
        )
        self.assertIn("## 本周推荐", result)
        self.assertIn("### 通勤 / 碎片时间", result)
        self.assertIn("适合通勤。", result)
        self.assertIn("场景分类由 OpenAI 模型 `gpt-5-mini` 生成", result)


if __name__ == "__main__":
    unittest.main()
