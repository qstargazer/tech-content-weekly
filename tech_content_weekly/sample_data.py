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
        item("影视飓风", "bilibili", "我们如何拍摄一场极端天气纪录片", "https://www.bilibili.com/video/BV1sample01", 1, 1128, 1_286_400, 4_832, "从器材选择、现场收音到后期调色，完整拆解高难度制作流程。"),
        item("影视飓风", "bilibili", "一块手机传感器的影像上限", "https://www.bilibili.com/video/BV1sample02", 5, 905, 892_300, 2_417, "围绕动态范围、降噪与计算摄影进行对比测试。"),
        item("影视飓风", "bilibili", "8K 工作流到底需要什么电脑", "https://www.bilibili.com/video/BV1sample03", 13, 1320, 1_956_200, 6_105, "测试高分辨率素材在剪辑、代理与导出阶段的性能瓶颈。"),
        item("影视飓风", "bilibili", "高速摄影机背后的工程设计", "https://www.bilibili.com/video/BV1sample04", 21, 1082, 1_537_900, 5_112, "分析高速读出、散热与存储带宽。"),
        item("3Blue1Brown", "youtube", "The geometry behind transformer attention", "https://www.youtube.com/watch?v=sample01", 2, 1462, 2_418_000, 6_824, "A visual exploration of attention matrices and high-dimensional geometry."),
        item("3Blue1Brown", "youtube", "Why eigenvectors keep showing up", "https://www.youtube.com/watch?v=sample02", 9, 1095, 3_205_000, 8_144, "Connecting linear transformations, dynamics, and probability."),
        item("3Blue1Brown", "youtube", "A probability puzzle with a surprising limit", "https://www.youtube.com/watch?v=sample03", 17, 855, 1_784_000, 4_109, "An intuitive derivation with simulation and geometry."),
        item("3Blue1Brown", "youtube", "How Fourier transforms reveal hidden structure", "https://www.youtube.com/watch?v=sample04", 27, 1274, 4_104_000, 10_328, "Frequency-space intuition for signals and differential equations."),
        item("科技早知道", "podcast", "AI Agent 从 Demo 到产品，还缺哪几步？", "https://www.xiaoyuzhoufm.com/episode/sample01", 3, 3210, None, None, "讨论 Agent 可靠性、工具调用、评测和商业落地。"),
        item("科技早知道", "podcast", "芯片创业进入新周期", "https://www.xiaoyuzhoufm.com/episode/sample02", 11, 2840, None, None, "从融资、供应链与软件生态观察芯片创业。"),
        item("科技早知道", "podcast", "具身智能需要怎样的数据", "https://www.xiaoyuzhoufm.com/episode/sample03", 22, 3560, None, None, "关注真实世界数据采集、仿真和评测。"),
    ]
