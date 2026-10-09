from unittest.mock import MagicMock, patch
import os
import unittest

from tech_content_weekly.ai import generate_insight, generate_recommendations, parse_recommendations
from tech_content_weekly.config import AiConfig, EmailConfig
from tech_content_weekly.mailer import send_email
from tech_content_weekly.config import load_config
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AiAndMailerTest(unittest.TestCase):
    @patch.dict(os.environ, {"OPENAI_MODEL": "account-model", "DEEPSEEK_MODEL": "deepseek-reasoner"}, clear=False)
    def test_model_environment_overrides_toml(self):
        config = load_config(ROOT / "config.toml")
        self.assertEqual(config.ai.openai_model, "account-model")
        self.assertEqual(config.ai.deepseek_model, "deepseek-reasoner")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "open-key", "DEEPSEEK_API_KEY": "deep-key"}, clear=True)
    @patch("tech_content_weekly.ai._openai")
    @patch("tech_content_weekly.ai._deepseek", return_value="DeepSeek result")
    def test_deepseek_is_preferred(self, deepseek, openai):
        result = generate_insight([], AiConfig(True, "open-model", "deep-model"))
        self.assertEqual(result[0:3], ("DeepSeek result", "DeepSeek", "deep-model"))
        openai.assert_not_called()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "open-key", "DEEPSEEK_API_KEY": "deep-key"}, clear=True)
    @patch("tech_content_weekly.ai._deepseek", side_effect=RuntimeError("deepseek down"))
    @patch("tech_content_weekly.ai._openai", return_value="OpenAI result")
    def test_openai_fallback(self, _openai, _deepseek):
        result = generate_insight([], AiConfig(True, "open-model", "deep-model"))
        self.assertEqual(result[0:3], ("OpenAI result", "OpenAI", "open-model"))
        self.assertIn("DeepSeek 摘要失败", result[3][0])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "open-key"}, clear=True)
    @patch("tech_content_weekly.ai._openai", side_effect=RuntimeError("quota exhausted"))
    def test_openai_quota_failure_is_not_report_warning(self, _openai):
        result = generate_insight([], AiConfig(True, "open-model", "deep-model"))
        self.assertNotIn("OpenAI 摘要失败", "\n".join(result[3]))

    @patch.dict(os.environ, {"SMTP_USER": "sender@gmail.com", "SMTP_PASSWORD": "app-pass", "EMAIL_RECIPIENTS": "a@test.com, b@test.com"}, clear=True)
    @patch("tech_content_weekly.mailer.smtplib.SMTP_SSL")
    def test_mailer_supports_multiple_recipients(self, smtp_ssl):
        smtp_ssl.return_value.__enter__.return_value.send_message.return_value = {}
        count = send_email(EmailConfig(True, ("fallback@test.com",), "[x]", "smtp.gmail.com", 465), "subject", "<b>html</b>", "text")
        self.assertEqual(count, 2)
        message = smtp_ssl.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(message["To"], "a@test.com, b@test.com")

    def test_parse_recommendations(self):
        from tech_content_weekly.models import ContentItem
        from datetime import datetime, timezone
        items = [
            ContentItem("a", "podcast", "轻松聊天", "https://1", datetime(2026, 8, 12, tzinfo=timezone.utc)),
            ContentItem("b", "bilibili", "数学可视化", "https://2", datetime(2026, 8, 12, tzinfo=timezone.utc)),
        ]
        text = '{"recommendations": [{"index": 0, "category": "commute", "reason": "轻松"}, {"index": 1, "category": "deep", "reason": "较深"}], "top_pick": {"index": 1, "reason": "最值得"}}'
        recs, top = parse_recommendations(text, items)
        self.assertEqual([rec.category for rec in recs], ["commute", "deep"])
        self.assertEqual(top.item.title, "数学可视化")

    def test_parse_recommendations_by_id_resists_ordering(self):
        """id 配对：即使模型输出的行顺序与数据顺序不同，理由也不会错位。"""
        from tech_content_weekly.models import ContentItem
        from datetime import datetime, timezone
        items = [
            ContentItem("a", "podcast", "#755 深度技术访谈", "https://episode-755", datetime(2026, 10, 7, tzinfo=timezone.utc)),
            ContentItem("b", "bilibili", "广播体操视频", "https://video-1", datetime(2026, 10, 7, tzinfo=timezone.utc)),
            ContentItem("c", "bilibili", "城市漫步 4K", "https://video-2", datetime(2026, 10, 7, tzinfo=timezone.utc)),
        ]
        id_755, id_gym, id_walk = (item.stable_id() for item in items)
        # 行序故意打乱：广播体操的理由排在 #755 之前
        text = (
            '{"recommendations": ['
            f'{{"id": "{id_gym}", "category": "commute", "reason": "广播体操视频，轻松怀旧"}},'
            f'{{"id": "{id_walk}", "category": "commute", "reason": "城市漫步4K视频，纯视觉欣赏"}},'
            f'{{"id": "{id_755}", "category": "deep", "reason": "如何把 PR 上到生产环境"}}'
            '], "top_pick": {"id": "%s", "reason": "最值得"}}' % id_755
        )
        recs, top = parse_recommendations(text, items)
        self.assertEqual(recs[0].item.title, "广播体操视频")
        self.assertEqual(recs[0].reason, "广播体操视频，轻松怀旧")
        self.assertEqual(recs[1].item.title, "城市漫步 4K")
        self.assertEqual(recs[2].item.title, "#755 深度技术访谈")
        self.assertEqual(top.item.title, "#755 深度技术访谈")

    def test_parse_recommendations_skips_unknown_id(self):
        """模型编造 id 时跳过该行，而不是错位到其他条目。"""
        from tech_content_weekly.models import ContentItem
        from datetime import datetime, timezone
        items = [
            ContentItem("a", "podcast", "轻松聊天", "https://1", datetime(2026, 8, 12, tzinfo=timezone.utc)),
        ]
        text = (
            '{"recommendations": ['
            '{"id": "deadbeef", "category": "commute", "reason": "编造的"},'
            f'{{"id": "{items[0].stable_id()}", "category": "commute", "reason": "正确"}}'
            '], "top_pick": {"id": "deadbeef", "reason": "x"}}'
        )
        recs, top = parse_recommendations(text, items)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].reason, "正确")
        self.assertIsNone(top)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deep-key"}, clear=True)
    @patch("tech_content_weekly.ai._deepseek", return_value='{"recommendations": [{"index": 0, "category": "commute", "reason": "轻松"}], "top_pick": {"index": 0, "reason": "值得"}}')
    def test_recommendations_uses_ai_when_available(self, deepseek):
        from tech_content_weekly.models import ContentItem
        from datetime import datetime, timezone
        items = [ContentItem("a", "podcast", "轻松聊天", "https://1", datetime(2026, 8, 12, tzinfo=timezone.utc))]
        recs, top, provider, model, warnings = generate_recommendations(items, AiConfig(True, "open", "deep"))
        self.assertEqual(provider, "DeepSeek")
        self.assertEqual(recs[0].category, "commute")
        self.assertEqual(top.item.title, "轻松聊天")

    @patch.dict(os.environ, {}, clear=True)
    def test_recommendations_fall_back_to_heuristic(self):
        from tech_content_weekly.models import ContentItem
        from datetime import datetime, timezone
        items = [ContentItem("a", "bilibili", "数学可视化教程", "https://1", datetime(2026, 8, 12, tzinfo=timezone.utc))]
        recs, top, provider, model, warnings = generate_recommendations(items, AiConfig(True, "open", "deep"))
        self.assertIsNone(provider)
        self.assertEqual(recs[0].category, "deep")
        self.assertIn("规则分类", warnings[0])


if __name__ == "__main__":
    unittest.main()
