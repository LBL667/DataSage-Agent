"""取数节点。

sql_generate、risk_assess、human_sql_approve、sql_review、readonly_exec。
中断节点独立，interrupt 在第一行，不套埋点装饰器。
"""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.config import load_blacklist, load_whitelist
from app.graph.state import AnalysisState
from app.guard import grant_store, risk
from app.llm import get_structured_llm
from app.middleware.node_wrapper import node
from app.prompts.review import REVIEW_SYSTEM_PROMPT
from app.prompts.sql import DEMO_SCHEMA, SQL_SYSTEM_PROMPT
from app.tools.mysql_tool import execute_query
from app.tools.schema_introspect import introspect_schema


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


class ReviewVerdict(BaseModel):
    """审查 Agent 的结构化判定。"""

    passed: bool
    violations: list[str] = []
    rewritten_sql: str | None = None


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
    """生成 SQL 与用途说明，累计 token 到 state。支持错误回灌与澄清补充。"""
    structured = get_structured_llm(SqlOutput)

    schema_text = await introspect_schema() or DEMO_SCHEMA
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        SystemMessage(content=f"可用表结构：\n{schema_text}"),
    ]

    errors = state.get("errors", [])
    if errors:
        messages.append(HumanMessage(content=f"上次 SQL 报错：{errors}\n请修正后重新生成。"))

    goal = state["user_goal"]
    if state.get("clarify_answer"):
        goal += f"\n补充说明：{state['clarify_answer']}"
    messages.append(HumanMessage(content=goal))

    with get_usage_metadata_callback() as usage_cb:
        result: SqlOutput = await structured.ainvoke(messages)
    tokens = _sum_usage(usage_cb.usage_metadata)
    used = int(state.get("token_used", 0)) + tokens
    return {
        "sql_draft": result.sql,
        "sql_explain": result.explain,
        "token_used": used,
        "errors": [],
    }


@node("risk_assess")
async def risk_assess(state: AnalysisState) -> dict:
    """风险分级，静态校验加授权记忆。"""
    sql = state.get("sql_draft") or ""
    result = risk.assess(sql, load_whitelist(), load_blacklist())

    level = result["level"]
    tables = result["tables"]
    reasons = result["reasons"]

    # 授权记忆：仅当 high 的唯一原因是表不在白名单时，授权命中才降为 low
    other_reasons = [r for r in reasons if not r.startswith("表不在白名单")]
    if level == "high" and not other_reasons and grant_store.is_granted(state.get("session_id", ""), tables):
        level = "low"
        reasons = ["表已授权，跳过审批"] + reasons

    return {
        "sql_risk_level": level,
        "sql_risk_reasons": reasons,
        "sql_ast_tables": tables,
        "sql_ast_columns": result["columns"],
    }


async def human_sql_approve(state: AnalysisState) -> dict:
    """高风险 SQL 的人工审批。interrupt 在第一行。"""
    result: ApprovalResult = interrupt(
        {"sql": state["sql_draft"], "explain": state["sql_explain"], "reasons": state.get("sql_risk_reasons", [])},
        response_schema=ApprovalResult,
    )
    # 同意时写表级授权，恢复时仅执行一次，重复写无害
    if result.decision == "approve":
        grant_store.grant(state.get("session_id", ""), state.get("sql_ast_tables", []))
    return {"approval": {"decision": result.decision, "comment": result.comment}}


@node("sql_review")
async def sql_review(state: AnalysisState) -> dict:
    """独立审查 Agent，输入只有 SQL 草稿与黑名单，不传用户诉求。"""
    structured = get_structured_llm(ReviewVerdict)
    blacklist = load_blacklist()
    messages = [
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(
            content=f"黑名单配置：{json.dumps(blacklist, ensure_ascii=False)}\n\nSQL 草稿：\n{state['sql_draft']}"
        ),
    ]
    with get_usage_metadata_callback() as usage_cb:
        verdict: ReviewVerdict = await structured.ainvoke(messages)
    tokens = _sum_usage(usage_cb.usage_metadata)
    used = int(state.get("token_used", 0)) + tokens
    result: dict = {"review_verdict": verdict.model_dump(), "token_used": used}
    if not verdict.passed:
        result["sql_retry_count"] = int(state.get("sql_retry_count", 0)) + 1
    return result


@node("readonly_exec", needs_credential=True)
async def readonly_exec(state: AnalysisState) -> dict:
    """只读执行，结果落盘，返回引用与元信息。"""
    ref, meta = await execute_query(state["sql_draft"])
    return {"result_ref": ref, "result_meta": meta}
