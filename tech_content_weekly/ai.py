from __future__ import annotations

import json
import logging
import os
import re

from .config import AiConfig
from .models import (
    CATEGORY_COMMUTE,
    CATEGORY_DEEP,
    RECOMMENDATION_CATEGORIES,
    ContentItem,
    Recommendation,
)


LOGGER = logging.getLogger(__name__)

_DEEP_TERMS = (
    "数学", "算法", "系统", "架构", "编译器", "论文", "研究", "模型", "证明", "可视化",
    "transformer", "attention", "eigenvector", "fourier", "scaling", "大模型", "训练",
    "推理", "深度学习", "compute",
)
_COMMUTE_TERMS = (
    "闲聊", "Q&A", "问答", "日常", "生活", "访谈", "热点", "家庭", "婚姻", "亲密关系",
    "饭圈", "轻松", "对话", "聊天", "live",
)


def _safe_error(error: Exception) -> str:
    message = str(error)
    for name in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        secret = os.getenv(name, "").strip()
        if secret:
            message = message.replace(secret, "***")
    return f"{type(error).__name__}: {message}"


def build_prompt(items: list[ContentItem]) -> str:
    evidence = [item.as_json() for item in items]
    return """你是严谨的中文科技内容编辑。只根据下面的结构化条目撰写 250-500 字的“本周内容导读”。
要求：按主题聚类，指出优先观看/收听的 3 项并说明理由；不得虚构视频或播客内容；缺少播放数据时不得推断热度。输出 Markdown，只用 ###、-、** 和行内代码。

数据：
""" + json.dumps(evidence, ensure_ascii=False, indent=2)


def build_recommendation_prompt(items: list[ContentItem]) -> str:
    evidence = [item.as_json() for item in items]
    return """你是中文科技内容编辑。下面是本周内容的结构化条目。
请把每条内容按「适合的消费场景」分成两类：
- "commute"：适合通勤、排队等碎片时间听/看，内容轻松、信息密度低、不需要做笔记，通常是播客或轻松的访谈。
- "deep"：内容较深、信息密度高、需要专门时间坐下来认真研究，可能需要看屏幕、暂停思考或做笔记，通常是数学/系统/论文讲解或深度技术访谈。
再从中选出一个你本周最推荐投入时间的内容作为 top_pick。
只输出 JSON，不要输出其他文字，格式：
{"recommendations": [{"index": 0, "category": "commute", "reason": "简短中文理由"}, ...], "top_pick": {"index": 3, "reason": "简短中文理由"}}
index 对应数据列表顺序（从 0 开始）。
数据：
""" + json.dumps(evidence, ensure_ascii=False, indent=2)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def parse_recommendations(text: str, items: list[ContentItem]) -> tuple[list[Recommendation], Recommendation | None]:
    data = _extract_json(text)
    if not data:
        return [], None
    recommendations = []
    for row in data.get("recommendations", []):
        index = row.get("index")
        if not isinstance(index, int) or not (0 <= index < len(items)):
            continue
        category = row.get("category")
        if category not in RECOMMENDATION_CATEGORIES:
            continue
        recommendations.append(
            Recommendation(items[index], category, str(row.get("reason", "")).strip())
        )
    top = None
    pick = data.get("top_pick") or {}
    index = pick.get("index")
    if isinstance(index, int) and 0 <= index < len(items):
        top = Recommendation(
            items[index], "top",
            str(pick.get("reason", "")).strip() or "本周最值得投入时间的内容",
        )
    return recommendations, top


def _heuristic_category(item: ContentItem) -> str:
    text = f"{item.title} {item.description}".lower()
    deep_hits = sum(text.count(term.lower()) for term in _DEEP_TERMS)
    commute_hits = sum(text.count(term.lower()) for term in _COMMUTE_TERMS)
    if deep_hits > commute_hits:
        return CATEGORY_DEEP
    if item.platform == "podcast":
        if commute_hits > deep_hits:
            return CATEGORY_COMMUTE
        if item.duration_seconds is not None and item.duration_seconds >= 3600:
            return CATEGORY_DEEP
        return CATEGORY_COMMUTE
    if commute_hits >= deep_hits and item.duration_seconds is not None and item.duration_seconds <= 1800:
        return CATEGORY_COMMUTE
    return CATEGORY_DEEP


def _heuristic_reason(item: ContentItem, category: str) -> str:
    if category == CATEGORY_DEEP:
        if item.duration_seconds is not None and item.duration_seconds >= 3600:
            return "时长较长且内容较深，建议留出专门时间认真观看并适当做笔记。"
        return "内容较深、信息密度高，建议留出专门时间认真研究。"
    if item.duration_seconds is not None and item.duration_seconds > 3600:
        return "音频内容，适合通勤或做其他事情时收听。"
    return "内容轻松、信息密度适中，适合通勤或碎片时间收听。"


def heuristic_recommendations(items: list[ContentItem]) -> tuple[list[Recommendation], Recommendation | None]:
    recommendations = [
        Recommendation(item, _heuristic_category(item), _heuristic_reason(item, _heuristic_category(item)))
        for item in items
    ]
    ranked = sorted(items, key=lambda item: (item.view_count or 0, item.published), reverse=True)
    top_item = next((item for item in ranked if _heuristic_category(item) == CATEGORY_DEEP), ranked[0])
    top = Recommendation(top_item, "top", "综合内容深度、时长与公开热度，本周最值得投入时间。")
    return recommendations, top


def _openai(prompt: str, model: str) -> str:
    from openai import OpenAI
    return (OpenAI().responses.create(model=model, input=prompt).output_text or "").strip()


def _deepseek(prompt: str, model: str) -> str:
    from openai import OpenAI
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    response = OpenAI(api_key=key, base_url="https://api.deepseek.com").chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()


def generate_insight(items: list[ContentItem], config: AiConfig) -> tuple[str | None, str | None, str | None, list[str]]:
    if not config.enabled:
        return None, None, None, []
    prompt, warnings = build_prompt(items), []
    if os.getenv("DEEPSEEK_API_KEY", "").strip():
        try:
            text = _deepseek(prompt, config.deepseek_model)
            if not text:
                raise RuntimeError("模型返回空内容")
            return text, "DeepSeek", config.deepseek_model, warnings
        except Exception as error:
            message = f"DeepSeek 摘要失败: {_safe_error(error)}"
            warnings.append(message)
            LOGGER.warning(message)
    if os.getenv("OPENAI_API_KEY", "").strip():
        try:
            text = _openai(prompt, config.openai_model)
            if not text:
                raise RuntimeError("模型返回空内容")
            return text, "OpenAI", config.openai_model, warnings
        except Exception as error:
            # OpenAI quota failures are expected here: keep them in Actions logs,
            # but do not add them to the emailed/HTML report.
            LOGGER.warning("OpenAI 摘要失败: %s", _safe_error(error))
    warnings.append("没有可用的 AI API Key，已保留基础数据报告")
    return None, None, None, warnings


def generate_recommendations(
    items: list[ContentItem], config: AiConfig,
) -> tuple[list[Recommendation], Recommendation | None, str | None, str | None, list[str]]:
    if not items:
        return [], None, None, None, []
    warnings = []
    if config.enabled and (
        os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    ):
        prompt = build_recommendation_prompt(items)
        for provider, model, key, call in (
            ("DeepSeek", config.deepseek_model, "DEEPSEEK_API_KEY", _deepseek),
            ("OpenAI", config.openai_model, "OPENAI_API_KEY", _openai),
        ):
            if not os.getenv(key, "").strip():
                continue
            try:
                text = call(prompt, model)
                if not text:
                    raise RuntimeError("模型返回空内容")
                recommendations, top = parse_recommendations(text, items)
                if not recommendations:
                    raise RuntimeError("分类结果无法解析")
                return recommendations, top, provider, model, warnings
            except Exception as error:
                message = f"{provider} 分类失败: {_safe_error(error)}"
                warnings.append(message)
                LOGGER.warning(message)
    recommendations, top = heuristic_recommendations(items)
    warnings.append("AI 分类不可用，已使用规则分类")
    return recommendations, top, None, None, warnings
