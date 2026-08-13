from __future__ import annotations

import json
import logging
import os
import re

from .config import AiConfig
from .models import ContentItem


LOGGER = logging.getLogger(__name__)


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
