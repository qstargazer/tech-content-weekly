from __future__ import annotations

from datetime import datetime, timedelta

from .models import ContentItem


def build_sample_items(now: datetime) -> list[ContentItem]:
    def item(
        creator: str,
        platform: str,
        title: str,
        url: str,
        days: int,
        duration: int,
        views: int | None,
        comments: int | None,
        description: str,
    ) -> ContentItem:
        return ContentItem(
            creator, platform, title, url, now - timedelta(days=days),
            duration, views, comments, description,
        )

    return [
        item("opus精译", "bilibili", "AI 研究者长访谈：推理模型与未来方向", "https://www.bilibili.com/video/BV1sample01", 1, 1128, 1_286_400, 4_832, "高质量英文访谈的中文精译版本。"),
        item("opus精译", "bilibili", "计算机科学先驱谈软件工程", "https://www.bilibili.com/video/BV1sample02", 5, 905, 892_300, 2_417, "围绕计算机系统与工程实践展开的深度对话。"),
        item("opus精译", "bilibili", "大模型训练背后的系统挑战", "https://www.bilibili.com/video/BV1sample03", 13, 1320, 1_956_200, 6_105, "讨论算力、数据和分布式训练瓶颈。"),
        item("opus精译", "bilibili", "科学家谈智能的本质", "https://www.bilibili.com/video/BV1sample04", 21, 1082, 1_537_900, 5_112, "从认知科学与人工智能的交叉视角展开。"),
        item("张小珺商业访谈录", "bilibili", "对话 AI 创业者：产品、组织与长期主义", "https://www.bilibili.com/video/BV1sample05", 4, 5420, 386_000, 1_205, "围绕人工智能创业、组织建设和商业化进行深度访谈。"),
        item("3Blue1Brown", "youtube", "The geometry behind transformer attention", "https://www.youtube.com/watch?v=sample01", 2, 1462, 2_418_000, 6_824, "A visual exploration of attention matrices and high-dimensional geometry."),
        item("3Blue1Brown", "youtube", "Why eigenvectors keep showing up", "https://www.youtube.com/watch?v=sample02", 9, 1095, 3_205_000, 8_144, "Connecting linear transformations, dynamics, and probability."),
        item("3Blue1Brown", "youtube", "A probability puzzle with a surprising limit", "https://www.youtube.com/watch?v=sample03", 17, 855, 1_784_000, 4_109, "An intuitive derivation with simulation and geometry."),
        item("3Blue1Brown", "youtube", "How Fourier transforms reveal hidden structure", "https://www.youtube.com/watch?v=sample04", 27, 1274, 4_104_000, 10_328, "Frequency-space intuition for signals and differential equations."),
        item("Dwarkesh Patel", "youtube", "Scaling, intelligence, and the future of AI", "https://www.youtube.com/watch?v=sample05", 3, 7210, 1_102_000, 3_892, "A deeply researched conversation about scaling and intelligence."),
        item("Dwarkesh Patel", "youtube", "Inside the economics of compute", "https://www.youtube.com/watch?v=sample06", 11, 6840, 836_000, 2_744, "Long-form analysis of compute, capital, and AI progress."),
        item("Dwarkesh Patel", "youtube", "How scientific discovery could accelerate", "https://www.youtube.com/watch?v=sample07", 22, 7560, 724_000, 2_109, "A discussion about AI-assisted scientific discovery."),
    ]
