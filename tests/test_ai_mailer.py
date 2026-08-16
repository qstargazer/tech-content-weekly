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
