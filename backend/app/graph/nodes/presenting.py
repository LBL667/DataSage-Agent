"""呈现节点。图表建议、校验、确认、洞察。

human_chart_approve 是第三个中断节点，interrupt 在第一行。
"""

from __future__ import annotations

import asyncio
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.chart.spec import ChartSpec
from app.config import DATA_DIR
from app.graph.state import AnalysisState
from app.llm import get_llm, get_structured_llm
from app.middleware.node_wrapper import node
from app.storage.dashboard_store import DashboardStore
from app.storage.result_store import ResultStore
from app.tools.registrar import get_registry

_store = ResultStore(DATA_DIR / "results")


class ChartApproval(BaseModel):
    """图表确认返回结构。"""

    decision: Literal["approve", "reject"]


CHART_SYSTEM_PROMPT = """你是图表建议器。根据分析结果与结果列名，输出一个 ChartSpec。

图表类型只给五种：line 折线、bar 柱状、scatter 散点、pie 饼图、table 表格。
x_field 与 y_field 必须是结果列名，series 可选。
description 用一句中文说明这个图表展示什么，例如「用柱状图对比各渠道的订单金额，横轴是渠道，纵轴是金额」。
"""


def _result_columns(state: AnalysisState) -> list[str]:
    ref = state.get("cleaned_ref") or state.get("result_ref")
    if not ref:
        return []
    meta = _store.load_meta(ref)
    return list(meta.get("columns", []))


@node("chart_advise")
async def chart_advise(state: AnalysisState) -> dict:
    """生成受 Schema 约束的 ChartSpec。"""
    columns = await asyncio.to_thread(_result_columns, state)
    structured = get_structured_llm(ChartSpec)
    messages = [
        SystemMessage(content=CHART_SYSTEM_PROMPT),
        HumanMessage(
            content=f"结果列名：{columns}\n用户诉求：{state['user_goal']}\n分析结果：{state.get('analysis_output')}"
        ),
    ]
    spec: ChartSpec = await structured.ainvoke(messages)
    return {"chart_spec": spec.model_dump()}


@node("chart_validate")
async def chart_validate(state: AnalysisState) -> dict:
    """校验字段名是否存在于结果列，对不上回炉。走 MCP 通道。"""
    columns = await asyncio.to_thread(_result_columns, state)
    result = await get_registry().call("chart_validate", chart_spec=state.get("chart_spec") or {}, columns=columns)
    if result["ok"]:
        return {"chart_validate_passed": True}
    return {
        "chart_validate_passed": False,
        "retry_count": int(state.get("retry_count", 0)) + 1,
        "errors": list(state.get("errors", [])) + [f"图表字段不匹配: {result['errors']}"],
    }


async def human_chart_approve(state: AnalysisState) -> dict:
    """图表确认，interrupt 在第一行。"""
    result: ChartApproval = interrupt(
        {"chart_spec": state.get("chart_spec")},
        response_schema=ChartApproval,
    )
    return {"chart_approved": result.decision == "approve"}


@node("respond")
async def respond(state: AnalysisState) -> dict:
    """文字洞察。缓存命中回放，分析类基于分析结果并落盘，chat 类简单答复。"""
    from app.rag import cache

    analysis = state.get("analysis_output") or {}

    # 缓存命中，直接回放
    if state.get("rag_cache_hit") and analysis.get("text"):
        return {"analysis_output": analysis}

    llm = get_llm(temperature=0.5)
    if analysis.get("data"):
        result = await llm.ainvoke(
            [HumanMessage(content=f"根据分析结果生成一段简洁洞察，避免套话：{analysis}")]
        )
        text = result.content
        store = DashboardStore(DATA_DIR / "dashboard")
        result_ref = state.get("cleaned_ref") or state.get("result_ref")
        rid = store.save(
            {
                "title": state.get("user_goal", "")[:50],
                "thread_id": state.get("session_id", ""),
                "result_ref": result_ref,
                "chart_spec": state.get("chart_spec"),
                "chart_approved": state.get("chart_approved"),
                "analysis_output": analysis,
                "clean_rules_applied": state.get("clean_rules_applied", []),
                "text": text,
            }
        )
        # 写语义缓存，key 含权限指纹
        await cache.store(
            state["user_goal"],
            state.get("time_window"),
            state.get("user_id", ""),
            {
                "result_ref": result_ref,
                "analysis_output": {**analysis, "text": text},
                "chart_spec": state.get("chart_spec"),
                "result_meta": state.get("result_meta"),
            },
        )
        return {"analysis_output": {**analysis, "text": text, "result_id": rid}}
    result = await llm.ainvoke([HumanMessage(content=state["user_goal"])])
    return {"analysis_output": {"text": result.content}}
