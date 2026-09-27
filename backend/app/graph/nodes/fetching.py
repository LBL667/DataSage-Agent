"""取数节点。第 3 步只做三个，SQL 生成、人工审批、只读执行。

中断节点必须独立，interrupt 放在函数第一行，因此 human_sql_approve 不套
埋点装饰器，它的审批事件由 chat.py 的 approval_request 表示。
"""

from __future__ import annotations

from typing import Literal

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.graph.state import AnalysisState
from app.llm import get_llm
from app.middleware.node_wrapper import node
from app.prompts.sql import DEMO_SCHEMA, SQL_SYSTEM_PROMPT
from app.tools.mysql_tool import execute_query


class SqlOutput(BaseModel):
    """SQL 生成的结构化输出。"""

    sql: str
    explain: str
    tables: list[str] = []
    assumptions: list[str] = []


class ApprovalResult(BaseModel):
    """审批返回结构，三个动作加一条修改意见。"""

    decision: Literal["approve", "edit", "cancel"]
    comment: str | None = None


def _sum_usage(usage_metadata: dict) -> int:
    """从 usage callback 收集的字典里累加 total token。"""
    total = 0
    for usage in usage_metadata.values():
        if not isinstance(usage, dict):
            continue
        if usage.get("total_tokens") is not None:
            total += int(usage["total_tokens"])
        else:
            total += int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
    return total


@node("sql_generate")
async def sql_generate(state: AnalysisState) -> dict:
    """生成 SQL 与用途说明，累计 token 到 state。"""
    llm = get_llm(temperature=0.0)
    structured = llm.with_structured_output(SqlOutput)
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        SystemMessage(content=f"可用表结构：\n{DEMO_SCHEMA}"),
        HumanMessage(content=state["user_goal"]),
    ]
    with get_usage_metadata_callback() as usage_cb:
        result: SqlOutput = await structured.ainvoke(messages)
    tokens = _sum_usage(usage_cb.usage_metadata)
    used = int(state.get("token_used", 0)) + tokens
    return {"sql_draft": result.sql, "sql_explain": result.explain, "token_used": used}


async def human_sql_approve(state: AnalysisState) -> dict:
    """高风险 SQL 的人工审批。interrupt 在第一行。"""
    result: ApprovalResult = interrupt(
        {"sql": state["sql_draft"], "explain": state["sql_explain"]},
        response_schema=ApprovalResult,
    )
    return {"approval": {"decision": result.decision, "comment": result.comment}}


@node("readonly_exec", needs_credential=True)
async def readonly_exec(state: AnalysisState) -> dict:
    """只读执行，结果落盘，返回引用与元信息。"""
    ref, meta = await execute_query(state["sql_draft"])
    return {"result_ref": ref, "result_meta": meta}
