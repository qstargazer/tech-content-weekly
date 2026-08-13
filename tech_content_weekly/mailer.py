from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .config import EmailConfig


def send_email(config: EmailConfig, subject: str, html_body: str, text_body: str) -> int:
    if not config.enabled:
        raise RuntimeError("config.toml 中 email.enabled 尚未设为 true")
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip() or user
    recipients_env = os.getenv("EMAIL_RECIPIENTS", "").strip()
    recipients = tuple(x.strip() for x in recipients_env.split(",") if x.strip()) if recipients_env else config.recipients
    if not user or not password or not recipients:
        raise RuntimeError("SMTP_USER、SMTP_PASSWORD 或邮件收件人未完整配置")
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = subject, sender, ", ".join(recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=30) as smtp:
        smtp.login(user, password)
        refused = smtp.send_message(message)
    if refused:
        raise RuntimeError(f"部分收件人被拒绝: {', '.join(refused)}")
    return len(recipients)
