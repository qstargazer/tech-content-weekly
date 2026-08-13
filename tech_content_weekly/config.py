from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
import os

from .models import Creator


@dataclass(frozen=True)
class ReportConfig:
    title: str
    timezone: str
    lookback_days: int
    monthly_days: int
    monthly_top_n: int


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool
    recipients: tuple[str, ...]
    subject_prefix: str
    smtp_host: str
    smtp_port: int


@dataclass(frozen=True)
class AiConfig:
    enabled: bool
    openai_model: str
    deepseek_model: str


@dataclass(frozen=True)
class FilterConfig:
    min_video_duration_minutes: int


@dataclass(frozen=True)
class AppConfig:
    report: ReportConfig
    email: EmailConfig
    ai: AiConfig
    filters: FilterConfig
    creators: tuple[Creator, ...]


def load_config(path: Path) -> AppConfig:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return AppConfig(
        report=ReportConfig(**raw["report"]),
        email=EmailConfig(
            enabled=raw["email"]["enabled"],
            recipients=tuple(raw["email"]["recipients"]),
            subject_prefix=raw["email"]["subject_prefix"],
            smtp_host=raw["email"]["smtp_host"],
            smtp_port=raw["email"]["smtp_port"],
        ),
        ai=AiConfig(
            enabled=raw["ai"]["enabled"],
            openai_model=os.getenv("OPENAI_MODEL", "").strip() or raw["ai"]["openai_model"],
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "").strip() or raw["ai"]["deepseek_model"],
        ),
        filters=FilterConfig(
            min_video_duration_minutes=int(raw.get("filters", {}).get("min_video_duration_minutes", 10)),
        ),
        creators=tuple(Creator(**item) for item in raw.get("creators", ())),
    )
