"""图组装与编译。图在 lifespan 里编译一次，全局复用，不每个请求都 compile。

节点全是 async def，checkpointer 必须用 AsyncSqliteSaver，它在事件循环内创建。
超时与重试用 TimeoutPolicy 与 RetryPolicy 声明式配置，不自写。
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
from app.graph.state import AnalysisState

_conn: aiosqlite.Connection | None = None


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
    """审查后分流，通过执行，不通过回生成。"""
    verdict = state.get("review_verdict") or {}
    if verdict.get("passed"):
        return "readonly_exec"
    return "sql_generate"


def on_exec_failed(state: AnalysisState, error: NodeError) -> dict:
    """只读执行失败后的补偿，记录错误，图结束。第 7 步改为纠错回路。"""
    errors = list(state.get("errors", [])) + [f"{error.node}:{type(error.error).__name__}"]
    return {"errors": errors}


async def build_graph():
    """组装取数图，AsyncSqliteSaver 持久化中断状态。Postgres 后续换。"""
    global _conn

    builder = StateGraph(AnalysisState)

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

    builder.add_edge(START, "sql_generate")
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
        {"readonly_exec": "readonly_exec", "sql_generate": "sql_generate"},
    )
    builder.add_edge("readonly_exec", END)

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
