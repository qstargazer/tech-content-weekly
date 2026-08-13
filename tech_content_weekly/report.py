from __future__ import annotations

import html
from collections import defaultdict
from datetime import datetime

from .analytics import monthly_top, weekly_items
from .models import ContentItem, Creator


PLATFORM_NAMES = {"bilibili": "哔哩哔哩", "youtube": "YouTube", "podcast": "播客 / 小宇宙"}


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value)
    escaped = __import__("re").sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = __import__("re").sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped


def _markdown_fragment(value: str) -> str:
    parts, list_rows = [], []
    def flush() -> None:
        if list_rows:
            parts.append("<ul>" + "".join(f"<li>{row}</li>" for row in list_rows) + "</ul>")
            list_rows.clear()
    for raw in value.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush()
            parts.append(f"<h3>{_inline_markdown(line[4:])}</h3>")
        elif line.startswith("- "):
            list_rows.append(_inline_markdown(line[2:]))
        else:
            flush()
            parts.append(f"<p>{_inline_markdown(line)}</p>")
    flush()
    return "".join(parts)


def _count(value: int | None) -> str:
    if value is None:
        return "未公开"
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f} 亿"
    if value >= 10_000:
        return f"{value / 10_000:.1f} 万"
    return f"{value:,}"


def _duration(seconds: int | None) -> str:
    if seconds is None:
        return "未知"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _card(item: ContentItem, rank: int | None = None) -> str:
    badge = f'<span class="rank">{rank}</span>' if rank else ""
    metrics = [
        f"<span>时长 {_duration(item.duration_seconds)}</span>",
        f"<span>播放 {_count(item.view_count)}</span>",
        f"<span>评论 {_count(item.comment_count)}</span>",
    ]
    if item.platform == "podcast":
        metrics = [f"<span>时长 {_duration(item.duration_seconds)}</span>", "<span>公开 RSS</span>"]
    return (
        f'<article class="item">{badge}<div class="item-main"><div class="item-meta">'
        f'{html.escape(PLATFORM_NAMES[item.platform])} · {item.published:%m-%d}</div>'
        f'<h3><a href="{html.escape(item.url, quote=True)}">{html.escape(item.title)}</a></h3>'
        f'<p>{html.escape(item.description)}</p><div class="metrics">{"".join(metrics)}</div>'
        "</div></article>"
    )


def render_html(
    title: str,
    creators: tuple[Creator, ...],
    items: list[ContentItem],
    now: datetime,
    lookback_days: int = 7,
    monthly_days: int = 30,
    top_n: int = 3,
    insight: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    weekly = weekly_items(items, now, lookback_days)
    top = monthly_top(items, now, monthly_days, top_n)
    weekly_by_platform: dict[str, list[ContentItem]] = defaultdict(list)
    for item in weekly:
        weekly_by_platform[item.platform].append(item)
    platform_sections = []
    for platform in ("bilibili", "youtube", "podcast"):
        rows = weekly_by_platform.get(platform, [])
        cards = "".join(_card(item) for item in rows) or '<p class="empty">本周没有新内容。</p>'
        platform_sections.append(
            f'<section><h2>{PLATFORM_NAMES[platform]}本周更新 <span>{len(rows)}</span></h2>{cards}</section>'
        )
    creator_sections = []
    for creator in creators:
        rows = top.get(creator.name, [])
        if creator.platform == "podcast":
            label = "最近 30 天更新"
            note = "播客 RSS 通常不提供统一播放量，本节按发布时间展示最近 3 期，不代表热度排名。"
        else:
            label = "最近 30 天热门 Top 3"
            note = "按报告生成时的公开播放量排序。"
        cards = "".join(_card(item, index) for index, item in enumerate(rows, 1)) or '<p class="empty">最近 30 天没有可用内容。</p>'
        creator_sections.append(
            f'<section><h2>{html.escape(creator.name)} · {label}</h2><p class="section-note">{note}</p>{cards}</section>'
        )
    creator_count = sum(creator.enabled for creator in creators)
    subtitle = f"{now:%Y-%m-%d} · 追踪 {creator_count} 位创作者 · 本周更新 {len(weekly)} 条"
    insight_html = ""
    if insight:
        insight_html = f'<section class="insight"><h2>AI 本周导读</h2>{_markdown_fragment(insight)}</section>'
    warning_html = ""
    if warnings:
        warning_html = '<div class="warning"><strong>数据状态</strong><ul>' + "".join(f"<li>{html.escape(row)}</li>" for row in warnings) + "</ul></div>"
    attribution = f'<div class="attribution">本期内容导读由 {html.escape(provider)} 模型 <code>{html.escape(model or "")}</code> 生成。</div>' if provider else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
body{{margin:0;background:#f3f7f5;color:#1f2925;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif;line-height:1.7}}.shell{{max-width:1080px;margin:0 auto;padding:26px 16px 46px}}.report{{overflow:hidden;background:#fff;border:1px solid #dfe8e3;border-radius:16px;box-shadow:0 8px 28px rgba(20,83,61,.10)}}.hero{{padding:34px 48px 30px;background:linear-gradient(135deg,#0b3d2e,#176b4d);color:#fff}}.eyebrow{{margin:0 0 8px;color:#bfe4d4;font-size:11px;font-weight:800;letter-spacing:2.1px}}h1{{margin:0;font-size:30px;line-height:1.35}}.subtitle{{margin:10px 0 0;color:#d7ede4;font-size:14px}}.content{{padding:8px 48px 42px}}section{{margin-top:34px}}h2{{display:flex;align-items:center;gap:10px;margin:0 0 16px;padding-bottom:10px;border-bottom:2px solid #197552;color:#183b2f;font-size:22px}}h2 span{{padding:2px 8px;border-radius:99px;background:#e9f5ef;color:#176b4d;font-size:12px}}.item{{display:flex;gap:14px;padding:17px 0;border-bottom:1px solid #e8efeb}}.item:last-child{{border-bottom:0}}.item-main{{min-width:0;flex:1}}.item-meta{{color:#71837b;font-size:12px;font-weight:650}}h3{{margin:4px 0 5px;font-size:17px;line-height:1.45}}a{{color:#176b4d;text-decoration:none}}a:hover{{color:#23855f;text-decoration:underline}}.item p{{margin:0 0 9px;color:#46564f;font-size:14px}}.metrics{{display:flex;flex-wrap:wrap;gap:8px}}.metrics span{{padding:3px 9px;border-radius:6px;background:#edf5f1;color:#48675a;font-size:12px}}.rank{{flex:0 0 26px;width:26px;height:26px;margin-top:4px;border-radius:50%;background:#176b4d;color:#fff;font-size:13px;font-weight:800;line-height:26px;text-align:center}}.section-note{{margin:-8px 0 6px;color:#71837b;font-size:13px}}.insight ul{{margin:8px 0;padding-left:22px}}.insight code{{padding:2px 5px;border-radius:4px;background:#edf5f1}}.notice{{margin:32px 0 0;padding:14px 16px;border-left:4px solid #197552;border-radius:0 8px 8px 0;background:#edf7f2;color:#355b4b;font-size:13px}}.warning{{margin:28px 0 0;padding:13px 16px;border-radius:8px;background:#fff8e7;color:#70551c;font-size:13px}}.warning ul{{margin:7px 0 0;padding-left:20px}}.attribution{{margin:18px 0 0;color:#71837b;font-size:12px;text-align:right}}.attribution code{{padding:2px 5px;border-radius:4px;background:#edf5f1}}.empty{{color:#71837b}}.footer{{padding:19px 28px;background:#f3f7f5;color:#71837b;font-size:12px;text-align:center}}@media(max-width:600px){{.shell{{padding:0}}.report{{border:0;border-radius:0;box-shadow:none}}.hero,.content{{padding-left:20px;padding-right:20px}}h1{{font-size:24px}}h2{{font-size:19px}}.item{{padding:15px 0}}}}
</style></head><body><div class="shell"><article class="report"><header class="hero"><p class="eyebrow">BILIBILI · YOUTUBE · PODCAST</p><h1>{html.escape(title)}</h1><p class="subtitle">{subtitle}</p></header><main class="content"><section><h2>本周概览</h2><p>集中查看关注创作者最近一周的新视频与播客，并保留最近一个月的热门或最新内容，减少错过高价值更新。</p></section>{insight_html}{''.join(platform_sections)}{''.join(creator_sections)}{warning_html}<div class="notice">数据说明：播放量与评论数是报告生成时的公开快照；播客公开 RSS 通常没有统一播放和评论指标。单个来源失败时使用缓存并明确标注，不影响其他创作者。</div>{attribution}</main><footer class="footer">多平台科技内容长期追踪 · 重要内容请回到原始页面核验</footer></article></div></body></html>'''


def render_markdown(
    title: str, creators: tuple[Creator, ...], items: list[ContentItem], now: datetime,
    insight: str | None = None, provider: str | None = None, model: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    weekly = weekly_items(items, now)
    lines = [f"# {title}", "", f"> 生成日期：{now:%Y-%m-%d}", "", "## 本周更新"]
    for item in weekly:
        lines.append(f"- **{item.creator_name}**｜[{item.title}]({item.url})｜{_duration(item.duration_seconds)}｜播放 {_count(item.view_count)}｜评论 {_count(item.comment_count)}")
    if insight:
        lines.extend(["", "## AI 本周导读", "", insight])
    if warnings:
        lines.extend(["", "## 数据状态", "", *(f"- {row}" for row in warnings)])
    if provider:
        lines.extend(["", f"> 本期内容导读由 {provider} 模型 `{model or ''}` 生成。"])
    return "\n".join(lines) + "\n"
