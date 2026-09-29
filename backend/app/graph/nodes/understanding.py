"""理解节点。intent_router 判定意图与信息充分度，clarify 澄清反问。

clarify 是中断节点，interrupt 在第一行，只问一次。
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.graph.state import AnalysisState
from app.llm import get_llm, get_structured_llm
from app.middleware.node_wrapper import node
from app.prompts.intent import INTENT_SYSTEM_PROMPT
from app.rag import cache
from app.rag.retrieve import retrieve


class IntentOutput(BaseModel):
    """意图识别的结构化输出。"""

    intent: Literal["chat", "simple_query", "deep_analysis"]
    info_sufficient: bool
    clarify_questions: list[str] = []
    route_reason: str = ""


class ClarifyAnswer(BaseModel):
    """澄清回答。"""

    answer: str


@node("intent_router")
async def intent_router(state: AnalysisState) -> dict:
    """判定意图三类并评估信息充分度。"""
    structured = get_structured_llm(IntentOutput)
    messages = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=state["user_goal"]),
    ]
    result: IntentOutput = await structured.ainvoke(messages)
    return {
        "intent": result.intent,
        "route_reason": result.route_reason,
        "info_sufficient": result.info_sufficient,
        "clarify_questions": result.clarify_questions,
    }


@node("memory_compact")
async def memory_compact(state: AnalysisState) -> dict:
    """会话内压缩。消息超过阈值时摘要前面的，保留最近若干轮原文。"""
    messages = state.get("messages", [])
    if len(messages) <= 20:
        return {}
    old = messages[:-10]
    llm = get_llm(temperature=0.0)
    result = await llm.ainvoke(
        [HumanMessage(content=f"用一两句话摘要以下对话历史，去掉客套：{old}")]
    )
    return {"summary": result.content}


@node("semantic_cache")
async def semantic_cache(state: AnalysisState) -> dict:
    """语义缓存。命中回放结果，未命中继续。key 含权限指纹。"""
    hit = await cache.lookup(
        state["user_goal"],
        state.get("time_window"),
        state.get("user_id", ""),
    )
    if hit:
        return {
            "result_ref": hit["result_ref"],
            "analysis_output": hit["analysis_output"],
            "chart_spec": hit["chart_spec"],
            "result_meta": hit["result_meta"],
            "rag_cache_hit": True,
        }
    return {"rag_cache_hit": False}


async def clarify(state: AnalysisState) -> dict:
    """信息不足时反问一次，interrupt 在第一行。"""
    questions = state.get("clarify_questions", [])
    answer: ClarifyAnswer = interrupt({"questions": questions}, response_schema=ClarifyAnswer)
    return {"clarify_answer": answer.answer}


@node("rag_retrieve")
async def rag_retrieve(state: AnalysisState) -> dict:
    """检索三个集合的上下文，各自可命中或落空，返回空上下文继续。"""
    query = state["user_goal"]
    if state.get("clarify_answer"):
        query = f"{state['user_goal']} {state['clarify_answer']}"

    schema_chunks = await retrieve(query, "schema")
    metric_chunks = await retrieve(query, "metric")
    method_chunks = await retrieve(query, "method")

    return {
        "schema_context": [c["content"] for c in schema_chunks],
        "metric_context": [c["content"] for c in metric_chunks],
        "method_context": [c["content"] for c in method_chunks],
        "rag_cache_hit": bool(schema_chunks),
    }
