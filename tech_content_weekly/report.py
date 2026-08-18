from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime

from .analytics import monthly_top, weekly_items
from .models import ContentItem, Creator


PLATFORM_NAMES = {"bilibili": "哔哩哔哩", "youtube": "YouTube", "podcast": "播客 / 小宇宙", "douban": "豆瓣读书"}


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
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


def _book_rating(item: ContentItem) -> str | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*分", item.description)
    return match.group(1) if match else None


def _anchor(value: str) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if ascii_slug:
        return ascii_slug
    return "section-" + str(abs(hash(value)))


def _compact_title(value: str, limit: int = 58) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _table_row(item: ContentItem) -> str:
    if item.platform == "douban":
        rating = _book_rating(item)
        metrics = f"评分 {rating}" if rating else "豆瓣榜单"
    elif item.platform == "podcast":
        metrics = f"{_duration(item.duration_seconds)} / RSS / -"
    else:
        metrics = f"{_duration(item.duration_seconds)} / {_count(item.view_count)} / {_count(item.comment_count)}"
    return (
        "<tr>"
        f'<td><span class="pill">{html.escape(PLATFORM_NAMES[item.platform])}</span></td>'
        f"<td>{html.escape(item.creator_name)}</td>"
        f'<td><a href="{html.escape(item.url, quote=True)}" title="{html.escape(item.title, quote=True)}">'
        f"{html.escape(_compact_title(item.title))}</a></td>"
        f"<td>{item.published:%m-%d}</td>"
        f"<td>{metrics}</td>"
        "</tr>"
    )


def _card(item: ContentItem, rank: int | None = None) -> str:
    badge = f'<span class="rank">{rank}</span>' if rank else ""
    if item.platform == "douban":
        rating = _book_rating(item)
        metrics = [f"<span>评分 {rating}</span>"] if rating else ["<span>豆瓣图书</span>"]
    elif item.platform == "podcast":
        metrics = [f"<span>时长 {_duration(item.duration_seconds)}</span>", "<span>公开 RSS</span>"]
    else:
        metrics = [
            f"<span>时长 {_duration(item.duration_seconds)}</span>",
            f"<span>播放 {_count(item.view_count)}</span>",
            f"<span>评论 {_count(item.comment_count)}</span>",
        ]
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
    for platform in ("bilibili", "youtube", "podcast", "douban"):
        rows = weekly_by_platform.get(platform, [])
        cards = "".join(_card(item) for item in rows) or '<p class="empty">本周没有新内容。</p>'
        platform_sections.append(
            f'<details id="{platform}" class="detail"><summary>{PLATFORM_NAMES[platform]}本周更新 '
            f'<span>{len(rows)}</span></summary>{cards}</details>'
        )

    creator_sections = []
    for creator in creators:
        rows = top.get(creator.name, [])
        if creator.platform == "podcast":
            label = "最近 30 天更新"
            note = "播客 RSS 通常不提供统一播放量，本节按发布时间展示最近 3 期，不代表热度排名。"
        elif creator.platform == "douban":
            label = "本周榜单 Top 3"
            note = "豆瓣榜单每周更新，按榜单热度排序；本书评分来自豆瓣公开数据。"
        else:
            label = "最近 30 天热门 Top 3"
            note = "按报告生成时的公开播放量排序。"
        cards = "".join(_card(item, index) for index, item in enumerate(rows, 1)) or '<p class="empty">最近 30 天没有可用内容。</p>'
        section_id = _anchor(f"creator-{creator.name}")
        creator_sections.append(
            f'<details id="{section_id}" class="detail"><summary>{html.escape(creator.name)} · {label}</summary>'
            f'<p class="section-note">{note}</p>{cards}</details>'
        )

    creator_count = sum(creator.enabled for creator in creators)
    subtitle = f"{now:%Y-%m-%d} · 追踪 {creator_count} 位创作者 · 本周更新 {len(weekly)} 条"
    platform_nav = "".join(
        f'<a href="#{platform}">{PLATFORM_NAMES[platform]} <span>{len(weekly_by_platform.get(platform, []))}</span></a>'
        for platform in ("bilibili", "youtube", "podcast", "douban")
    )
    creator_nav = "".join(
        f'<a href="#{_anchor(f"creator-{creator.name}")}">{html.escape(creator.name)}</a>'
        for creator in creators if creator.enabled
    )
    weekly_table = (
        '<div class="table-wrap"><table><thead><tr><th>平台</th><th>创作者</th><th>内容</th><th>日期</th>'
        '<th>时长 / 播放 / 评论</th></tr></thead><tbody>'
        + "".join(_table_row(item) for item in weekly)
        + "</tbody></table></div>"
    ) if weekly else '<p class="empty">本周没有新内容。</p>'
    insight_html = ""
    if insight:
        insight_html = f'<section class="insight"><h2>AI 本周导读</h2>{_markdown_fragment(insight)}</section>'
    warning_html = ""
    if warnings:
        warning_html = '<div class="warning"><strong>数据状态</strong><ul>' + "".join(f"<li>{html.escape(row)}</li>" for row in warnings) + "</ul></div>"
    attribution = f'<div class="attribution">本期内容导读由 {html.escape(provider)} 模型 <code>{html.escape(model or "")}</code> 生成。</div>' if provider else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
body{{margin:0;background:#f3f7f5;color:#1f2925;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif;line-height:1.55}}.shell{{max-width:1160px;margin:0 auto;padding:18px 14px 34px}}.report{{overflow:hidden;background:#fff;border:1px solid #dfe8e3;border-radius:12px;box-shadow:0 8px 24px rgba(20,83,61,.08)}}.hero{{padding:24px 34px 22px;background:linear-gradient(135deg,#0b3d2e,#176b4d);color:#fff}}.eyebrow{{margin:0 0 6px;color:#bfe4d4;font-size:11px;font-weight:800;letter-spacing:2px}}h1{{margin:0;font-size:28px;line-height:1.25}}.subtitle{{margin:8px 0 0;color:#d7ede4;font-size:14px}}.content{{padding:20px 34px 34px}}section{{margin-top:24px}}h2{{display:flex;align-items:center;gap:10px;margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid #197552;color:#183b2f;font-size:20px}}h2 span,summary span,.nav a span{{padding:1px 7px;border-radius:99px;background:#e9f5ef;color:#176b4d;font-size:12px}}a{{color:#176b4d;text-decoration:none}}a:hover{{color:#23855f;text-decoration:underline}}.overview{{margin-top:0}}.overview p{{margin:0 0 14px;color:#46564f}}.nav{{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}}.nav a{{padding:6px 10px;border:1px solid #d8e6df;border-radius:8px;background:#f7fbf9;color:#315b4a;font-size:13px}}.nav.creator a{{font-size:12px}}.table-wrap{{overflow:auto;border:1px solid #dfe8e3;border-radius:10px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:8px 10px;border-bottom:1px solid #edf3f0;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#f1f8f4;color:#315b4a;font-weight:750}}td:nth-child(1){{width:96px}}td:nth-child(2){{width:150px}}td:nth-child(4),td:nth-child(5){{white-space:nowrap;color:#60756c}}tr:last-child td{{border-bottom:0}}.pill{{display:inline-block;padding:2px 7px;border-radius:999px;background:#edf5f1;color:#48675a;font-size:12px}}.detail{{margin-top:14px;border:1px solid #dfe8e3;border-radius:10px;background:#fbfdfc}}summary{{cursor:pointer;padding:10px 12px;color:#183b2f;font-size:16px;font-weight:760}}.item{{display:flex;gap:12px;padding:12px;border-top:1px solid #e8efeb}}.item-main{{min-width:0;flex:1}}.item-meta{{color:#71837b;font-size:12px;font-weight:650}}h3{{margin:3px 0 4px;font-size:15px;line-height:1.35}}.item p{{margin:0 0 7px;color:#46564f;font-size:13px}}.metrics{{display:flex;flex-wrap:wrap;gap:6px}}.metrics span{{padding:2px 7px;border-radius:6px;background:#edf5f1;color:#48675a;font-size:12px}}.rank{{flex:0 0 24px;width:24px;height:24px;margin:13px 0 0 12px;border-radius:50%;background:#176b4d;color:#fff;font-size:12px;font-weight:800;line-height:24px;text-align:center}}.section-note{{margin:0 12px 2px;color:#71837b;font-size:13px}}.insight{{padding:14px 16px;border:1px solid #dfe8e3;border-radius:10px;background:#fbfdfc}}.insight h2{{margin-bottom:10px}}.insight h3{{margin:12px 0 6px;font-size:16px}}.insight p{{margin:7px 0;color:#33463e}}.insight ul{{margin:6px 0;padding-left:20px}}.insight li{{margin:4px 0}}.insight code{{padding:2px 5px;border-radius:4px;background:#edf5f1}}.notice{{margin:24px 0 0;padding:12px 14px;border-left:4px solid #197552;border-radius:0 8px 8px 0;background:#edf7f2;color:#355b4b;font-size:13px}}.warning{{margin:22px 0 0;padding:12px 14px;border-radius:8px;background:#fff8e7;color:#70551c;font-size:13px}}.warning ul{{margin:7px 0 0;padding-left:20px}}.attribution{{margin:16px 0 0;color:#71837b;font-size:12px;text-align:right}}.attribution code{{padding:2px 5px;border-radius:4px;background:#edf5f1}}.empty{{color:#71837b}}.footer{{padding:15px 24px;background:#f3f7f5;color:#71837b;font-size:12px;text-align:center}}@media(max-width:700px){{.shell{{padding:0}}.report{{border:0;border-radius:0;box-shadow:none}}.hero,.content{{padding-left:16px;padding-right:16px}}h1{{font-size:23px}}h2{{font-size:18px}}td:nth-child(5),th:nth-child(5){{display:none}}table{{min-width:620px}}}}
</style></head><body><div class="shell"><article class="report"><header class="hero"><p class="eyebrow">BILIBILI · YOUTUBE · PODCAST · DOUBAN</p><h1>{html.escape(title)}</h1><p class="subtitle">{subtitle}</p></header><main class="content"><section class="overview"><h2>本周概览</h2><p>先用表格扫完所有更新；需要细看时，使用下方目录跳转到平台或创作者详情，或直接打开原始页面。</p><nav class="nav">{platform_nav}</nav><nav class="nav creator">{creator_nav}</nav></section>{insight_html}<section><h2>本周更新 <span>{len(weekly)}</span></h2>{weekly_table}</section><section><h2>按平台展开</h2>{''.join(platform_sections)}</section><section><h2>创作者近 30 天</h2>{''.join(creator_sections)}</section>{warning_html}<div class="notice">数据说明：播放量与评论数是报告生成时的公开快照；播客公开 RSS 通常没有统一播放和评论指标。单个来源失败时使用缓存并明确标注，不影响其他创作者。</div>{attribution}</main><footer class="footer">多平台科技内容长期追踪 · 重要内容请回到原始页面核验</footer></article></div></body></html>'''


def render_markdown(
    title: str, creators: tuple[Creator, ...], items: list[ContentItem], now: datetime,
    insight: str | None = None, provider: str | None = None, model: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    weekly = weekly_items(items, now)
    lines = [f"# {title}", "", f"> 生成日期：{now:%Y-%m-%d}", "", "## 本周更新"]
    for item in weekly:
        if item.platform == "douban":
            rating = _book_rating(item)
            lines.append(f"- **{item.creator_name}**｜[{item.title}]({item.url})｜评分 {rating or '未公开'}")
        elif item.platform == "podcast":
            lines.append(f"- **{item.creator_name}**｜[{item.title}]({item.url})｜{_duration(item.duration_seconds)}｜公开 RSS")
        else:
            lines.append(f"- **{item.creator_name}**｜[{item.title}]({item.url})｜{_duration(item.duration_seconds)}｜播放 {_count(item.view_count)}｜评论 {_count(item.comment_count)}")
    if insight:
        lines.extend(["", "## AI 本周导读", "", insight])
    if warnings:
        lines.extend(["", "## 数据状态", "", *(f"- {row}" for row in warnings)])
    if provider:
        lines.extend(["", f"> 本期内容导读由 {provider} 模型 `{model or ''}` 生成。"])
    return "\n".join(lines) + "\n"
