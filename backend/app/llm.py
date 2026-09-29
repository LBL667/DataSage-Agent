"""模型客户端。

ChatOpenAI 实例，按节点温度策略，结构化输出封装。注意用 langchain_openai
而不是已弃用的 langchain.chat_models。
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import Settings, load_settings


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return load_settings()


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """按温度策略返回模型实例。SQL 生成、审查等关键节点用 0，洞察输出用 0.5 到 0.7。"""
    s = _cached_settings()
    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key or "sk-missing",
        base_url=s.llm_base_url or None,
        temperature=temperature,
    )


def get_structured_llm(schema, temperature: float = 0.0):
    """返回带结构化输出约束的 runnable。

    用 function_calling 而非 json_schema。deepseek-flash 等 thinking 模式模型
    既不支持 response_format 也不支持 tool_choice，需用 deepseek-chat。
    """
    llm = get_llm(temperature=temperature)
    return llm.with_structured_output(schema, method="function_calling")
