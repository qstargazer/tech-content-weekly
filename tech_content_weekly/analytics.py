from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from .models import ContentItem


def weekly_items(items: list[ContentItem], now: datetime, days: int = 7) -> list[ContentItem]:
    cutoff = now - timedelta(days=days)
    return sorted(
        (item for item in items if cutoff <= item.published <= now),
        key=lambda item: item.published,
        reverse=True,
    )


def monthly_top(
    items: list[ContentItem], now: datetime, days: int = 30, top_n: int = 3
) -> dict[str, list[ContentItem]]:
    cutoff = now - timedelta(days=days)
    groups: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        if cutoff <= item.published <= now:
            groups[item.creator_name].append(item)
    for creator_items in groups.values():
        creator_items.sort(
            key=lambda item: (
                item.view_count is not None,
                item.view_count or 0,
                item.comment_count or 0,
                item.published,
            ),
            reverse=True,
        )
        del creator_items[top_n:]
    return dict(groups)
