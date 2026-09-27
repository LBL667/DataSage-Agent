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
from app.graph.nodes.fetching import human_sql_approve, readonly_exec, sql_generate
from app.graph.state import AnalysisState

_conn: aiosqlite.Connection | None = None


def route_after_approve(state: AnalysisState) -> str:
    """条件边纯函数，无副作用。approve 继续执行，其余结束。"""
    approval = state.get("approval") or {}
    if approval.get("decision") == "approve":
        return "readonly_exec"
    return "end"


def on_exec_failed(state: AnalysisState, error: NodeError) -> dict:
    """只读执行失败后的补偿，记录错误，图结束。"""
    errors = list(state.get("errors", [])) + [f"{error.node}:{type(error.error).__name__}"]
    return {"errors": errors}


async def build_graph():
    """组装最小图，AsyncSqliteSaver 持久化中断状态。Postgres 后续换。"""
    global _conn

    builder = StateGraph(AnalysisState)

    builder.add_node(
        "sql_generate",
        sql_generate,
        timeout=TimeoutPolicy(run_timeout=60.0, idle_timeout=15.0),
        retry_policy=RetryPolicy(max_attempts=2),
    )
    builder.add_node("human_sql_approve", human_sql_approve)
    builder.add_node(
        "readonly_exec",
        readonly_exec,
        timeout=TimeoutPolicy(run_timeout=30.0, idle_timeout=10.0),
        retry_policy=RetryPolicy(max_attempts=3),
        error_handler=on_exec_failed,
    )

    builder.add_edge(START, "sql_generate")
    builder.add_edge("sql_generate", "human_sql_approve")
    builder.add_conditional_edges(
        "human_sql_approve",
        route_after_approve,
        {"readonly_exec": "readonly_exec", "end": END},
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
