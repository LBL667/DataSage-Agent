"""图组装与编译。图在 lifespan 里编译一次，全局复用，不每个请求都 compile。

节点全是 async def，checkpointer 必须用 AsyncSqliteSaver，它在事件循环内创建。
超时与重试用 TimeoutPolicy 与 RetryPolicy 声明式配置，不自写。
回退回路计数写进 state，recursion_limit 在 config 里传。
"""

from __future__ import annotations

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, TimeoutPolicy

from app.config import DATA_DIR
from app.graph.nodes.fetching import (
    human_sql_approve,
    readonly_exec,
    risk_assess,
    sql_generate,
    sql_review,
)
from app.graph.nodes.presenting import (
    chart_advise,
    chart_validate,
    human_chart_approve,
    respond,
)
from app.graph.nodes.processing import analyze, data_clean, quality_check, self_check
from app.graph.nodes.understanding import clarify, intent_router
from app.graph.state import AnalysisState

_conn: aiosqlite.Connection | None = None

# SQL 重写回退上限
_SQL_RETRY_LIMIT = 2
# 图表重生成回退上限
_CHART_RETRY_LIMIT = 1


def route_after_intent(state: AnalysisState) -> str:
    """意图分流，闲聊答复，取数按信息充分度决定是否澄清。"""
    if state.get("intent") == "chat":
        return "respond"
    if state.get("info_sufficient"):
        return "sql_generate"
    return "clarify"


def route_after_risk(state: AnalysisState) -> str:
    """风险分级后分流，high 走审批，low 直接审查。"""
    if state.get("sql_risk_level") == "high":
        return "human_sql_approve"
    return "sql_review"


def route_after_approve(state: AnalysisState) -> str:
    """审批后分流，同意继续审查，修改回生成，取消结束。"""
    decision = (state.get("approval") or {}).get("decision")
    if decision == "approve":
        return "sql_review"
    if decision == "edit":
        return "sql_generate"
    return "end"


def route_after_review(state: AnalysisState) -> str:
    """审查后分流，通过执行，不通过回生成，超限结束。"""
    verdict = state.get("review_verdict") or {}
    if verdict.get("passed"):
        return "readonly_exec"
    if state.get("sql_retry_count", 0) < _SQL_RETRY_LIMIT:
        return "sql_generate"
    return "end"


def route_after_exec(state: AnalysisState) -> str:
    """执行后分流，报错回生成纠错，成功进质检。"""
    if state.get("errors"):
        if state.get("sql_retry_count", 0) < _SQL_RETRY_LIMIT:
            return "sql_generate"
        return "end"
    return "quality_check"


def route_after_quality(state: AnalysisState) -> str:
    """质检后分流，通过清洗，不通过回生成。"""
    if state.get("quality_passed"):
        return "data_clean"
    if state.get("sql_retry_count", 0) < _SQL_RETRY_LIMIT:
        return "sql_generate"
    return "end"


def route_after_self_check(state: AnalysisState) -> str:
    """自检后分流，通过出图表，不通过回生成。"""
    if state.get("self_check_passed"):
        return "chart_advise"
    if state.get("sql_retry_count", 0) < _SQL_RETRY_LIMIT:
        return "sql_generate"
    return "end"


def route_after_chart_validate(state: AnalysisState) -> str:
    """图表校验后分流，通过确认，不通过回图表建议，超限降级出文字。"""
    if state.get("chart_validate_passed"):
        return "human_chart_approve"
    if state.get("retry_count", 0) < _CHART_RETRY_LIMIT:
        return "chart_advise"
    return "respond"


def on_exec_failed(state: AnalysisState, error: NodeError) -> dict:
    """只读执行失败后的补偿，记录错误并计数。"""
    errors = list(state.get("errors", [])) + [f"{error.node}:{type(error.error).__name__}"]
    sql_retry_count = int(state.get("sql_retry_count", 0)) + 1
    return {"errors": errors, "sql_retry_count": sql_retry_count}


async def build_graph():
    """组装完整分析图，AsyncSqliteSaver 持久化中断状态。Postgres 后续换。"""
    global _conn

    builder = StateGraph(AnalysisState)

    builder.add_node("intent_router", intent_router)
    builder.add_node("clarify", clarify)
    builder.add_node("respond", respond)
    builder.add_node(
        "sql_generate",
        sql_generate,
        timeout=TimeoutPolicy(run_timeout=60.0, idle_timeout=15.0),
        retry_policy=RetryPolicy(max_attempts=2),
    )
    builder.add_node("risk_assess", risk_assess)
    builder.add_node("human_sql_approve", human_sql_approve)
    builder.add_node("sql_review", sql_review)
    builder.add_node(
        "readonly_exec",
        readonly_exec,
        timeout=TimeoutPolicy(run_timeout=30.0, idle_timeout=10.0),
        retry_policy=RetryPolicy(max_attempts=3),
        error_handler=on_exec_failed,
    )
    builder.add_node("quality_check", quality_check)
    builder.add_node("data_clean", data_clean)
    builder.add_node("analyze", analyze)
    builder.add_node("self_check", self_check)
    builder.add_node("chart_advise", chart_advise)
    builder.add_node("chart_validate", chart_validate)
    builder.add_node("human_chart_approve", human_chart_approve)

    builder.add_edge(START, "intent_router")
    builder.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {"respond": "respond", "sql_generate": "sql_generate", "clarify": "clarify"},
    )
    builder.add_edge("clarify", "sql_generate")
    builder.add_edge("respond", END)
    builder.add_edge("sql_generate", "risk_assess")
    builder.add_conditional_edges(
        "risk_assess",
        route_after_risk,
        {"human_sql_approve": "human_sql_approve", "sql_review": "sql_review"},
    )
    builder.add_conditional_edges(
        "human_sql_approve",
        route_after_approve,
        {"sql_review": "sql_review", "sql_generate": "sql_generate", "end": END},
    )
    builder.add_conditional_edges(
        "sql_review",
        route_after_review,
        {"readonly_exec": "readonly_exec", "sql_generate": "sql_generate", "end": END},
    )
    builder.add_conditional_edges(
        "readonly_exec",
        route_after_exec,
        {"sql_generate": "sql_generate", "end": END, "quality_check": "quality_check"},
    )
    builder.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {"data_clean": "data_clean", "sql_generate": "sql_generate", "end": END},
    )
    builder.add_edge("data_clean", "analyze")
    builder.add_edge("analyze", "self_check")
    builder.add_conditional_edges(
        "self_check",
        route_after_self_check,
        {"chart_advise": "chart_advise", "sql_generate": "sql_generate", "end": END},
    )
    builder.add_edge("chart_advise", "chart_validate")
    builder.add_conditional_edges(
        "chart_validate",
        route_after_chart_validate,
        {"human_chart_approve": "human_chart_approve", "chart_advise": "chart_advise", "respond": "respond"},
    )
    builder.add_edge("human_chart_approve", "respond")

    checkpoint_db = DATA_DIR / "checkpoint.sqlite"
    checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    if _conn is None:
        _conn = await aiosqlite.connect(str(checkpoint_db))
    checkpointer = AsyncSqliteSaver(_conn)
    return builder.compile(checkpointer=checkpointer)


async def close_graph() -> None:
    """关闭 checkpointer 连接，供应用停机与脚本结束时调用。"""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None
