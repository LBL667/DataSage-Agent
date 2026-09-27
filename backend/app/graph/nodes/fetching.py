"""取数节点。第 3 步只做三个，SQL 生成、人工审批、只读执行。

中断节点必须独立，interrupt 放在函数第一行。恢复时节点函数会重跑，
中断点之前的副作用会执行两次，所以前面不放任何代码。
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.graph.state import AnalysisState
from app.llm import get_llm
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


async def sql_generate(state: AnalysisState) -> dict:
    """生成 SQL 与用途说明。"""
    llm = get_llm(temperature=0.0)
    structured = llm.with_structured_output(SqlOutput)
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        SystemMessage(content=f"可用表结构：\n{DEMO_SCHEMA}"),
        HumanMessage(content=state["user_goal"]),
    ]
    result: SqlOutput = await structured.ainvoke(messages)
    return {"sql_draft": result.sql, "sql_explain": result.explain}


async def human_sql_approve(state: AnalysisState) -> dict:
    """高风险 SQL 的人工审批。interrupt 在第一行。"""
    result: ApprovalResult = interrupt(
        {"sql": state["sql_draft"], "explain": state["sql_explain"]},
        response_schema=ApprovalResult,
    )
    return {"approval": {"decision": result.decision, "comment": result.comment}}


async def readonly_exec(state: AnalysisState) -> dict:
    """只读执行，结果落盘，返回引用与元信息。"""
    ref, meta = await execute_query(state["sql_draft"])
    return {"result_ref": ref, "result_meta": meta}
