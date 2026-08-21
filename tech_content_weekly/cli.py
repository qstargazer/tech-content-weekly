from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import load_config
from .collectors import collect_all
from .analytics import weekly_items
from .ai import generate_insight, generate_recommendations, heuristic_recommendations
from .mailer import send_email
from .report import render_html, render_markdown
from .sample_data import build_sample_items


def _timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Shanghai":
            return timezone(timedelta(hours=8), name)
        raise


def _dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def run(config_path: Path, output_dir: Path, sample: bool, send: bool = False) -> tuple[Path, Path]:
    _dotenv(config_path.resolve().parent / ".env")
    config = load_config(config_path)
    now = datetime.now(_timezone(config.report.timezone))
    if sample:
        items, warnings = build_sample_items(now), []
        min_seconds = config.filters.min_video_duration_minutes * 60
        items = [
            item for item in items
            if item.platform not in {"youtube", "bilibili"}
            or item.duration_seconds is None
            or item.duration_seconds >= min_seconds
        ]
    else:
        since = now.astimezone(timezone.utc) - timedelta(days=config.report.monthly_days)
        items, warnings = collect_all(
            config.creators, since, config_path.resolve().parent / "data/cache",
            config.filters.min_video_duration_minutes * 60,
        )
        if not items:
            raise RuntimeError("所有在线来源均无可用内容或缓存")
    if sample:
        insight = "### 本周优先内容\n- **视觉计算**：关注高帧率制作流程。\n- **数学可视化**：适合系统理解抽象概念。\n- `AI 编译器`访谈：补充工程实践视角。"
        provider, model, ai_warnings = "离线样例", "preview-model", []
        recommendations, top_pick = heuristic_recommendations(weekly_items(items, now, config.report.lookback_days))
        rec_provider, rec_model = None, None
    else:
        insight, provider, model, ai_warnings = generate_insight(
            weekly_items(items, now, config.report.lookback_days), config.ai
        )
        recommendations, top_pick, rec_provider, rec_model, rec_warnings = generate_recommendations(
            weekly_items(items, now, config.report.lookback_days), config.ai
        )
        ai_warnings.extend(rec_warnings)
    warnings.extend(ai_warnings)
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(
        config.report.title, config.creators, items, now,
        insight, provider, model, warnings,
        recommendations, top_pick, rec_provider, rec_model,
        config.report.schedule_note,
    )
    page = render_html(
        config.report.title, config.creators, items, now,
        config.report.lookback_days, config.report.monthly_days, config.report.monthly_top_n,
        insight, provider, model, warnings,
        recommendations, top_pick, rec_provider, rec_model,
        config.report.schedule_note,
    )
    stem = now.date().isoformat()
    md_path = output_dir / f"weekly-{stem}.md"
    html_path = output_dir / f"weekly-{stem}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(page, encoding="utf-8")
    if warnings:
        (output_dir / "warnings.log").write_text("\n".join(warnings) + "\n", encoding="utf-8")
    if send:
        count = send_email(
            config.email, f"{config.email.subject_prefix} {stem}", page, markdown
        )
        print(f"Email sent to {count} recipient(s)")
    return md_path, html_path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Generate a multi-platform technology content weekly report")
    result.add_argument("--config", type=Path, default=Path("config.toml"))
    result.add_argument("--output-dir", type=Path, default=Path("output"))
    result.add_argument("--sample", action="store_true", help="使用内置模拟数据生成排版样例")
    result.add_argument("--send", action="store_true", help="生成后通过 Gmail SMTP 发送")
    return result


def main() -> None:
    args = parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    markdown, page = run(args.config, args.output_dir, args.sample, args.send)
    print(f"Markdown: {markdown}")
    print(f"HTML: {page}")


if __name__ == "__main__":
    main()
