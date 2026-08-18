from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Creator:
    name: str
    platform: str
    id: str
    url: str
    enabled: bool = True
    feed_url: str | None = None


@dataclass(frozen=True)
class ContentItem:
    creator_name: str
    platform: str
    title: str
    url: str
    published: datetime
    duration_seconds: int | None = None
    view_count: int | None = None
    comment_count: int | None = None
    description: str = ""

    @property
    def engagement_rate(self) -> float | None:
        if not self.view_count:
            return None
        return (self.comment_count or 0) / self.view_count

    def as_json(self) -> dict[str, object]:
        return {
            "creator_name": self.creator_name, "platform": self.platform,
            "title": self.title, "url": self.url,
            "published": self.published.isoformat(),
            "duration_seconds": self.duration_seconds,
            "view_count": self.view_count, "comment_count": self.comment_count,
            "description": self.description,
        }

    @classmethod
    def from_json(cls, value: dict[str, object]) -> "ContentItem":
        return cls(
            creator_name=str(value["creator_name"]), platform=str(value["platform"]),
            title=str(value["title"]), url=str(value["url"]),
            published=datetime.fromisoformat(str(value["published"])),
            duration_seconds=int(value["duration_seconds"]) if value.get("duration_seconds") is not None else None,
            view_count=int(value["view_count"]) if value.get("view_count") is not None else None,
            comment_count=int(value["comment_count"]) if value.get("comment_count") is not None else None,
            description=str(value.get("description", "")),
        )


CATEGORY_COMMUTE = "commute"
CATEGORY_DEEP = "deep"
RECOMMENDATION_CATEGORIES = (CATEGORY_COMMUTE, CATEGORY_DEEP)


@dataclass(frozen=True)
class Recommendation:
    item: ContentItem
    category: str
    reason: str
