"""AnalysisState 状态契约。

所有节点只读写这个结构，节点之间不私传参数。字段一次抄全，不先写一半后面补。
查询结果与 DataFrame 绝不进 state，只放引用与元信息，否则 checkpoint 会迅速膨胀。
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class AnalysisState(TypedDict):
    # 会话标识
    session_id: str
    user_id: str
    trace_id: str
    messages: Annotated[list, operator.add]

    # 意图与澄清
    user_goal: str
    time_window: tuple[str, str]
    intent: Literal["chat", "simple_query", "deep_analysis"]
    route_reason: str
    info_sufficient: bool
    clarify_questions: list[str]
    clarify_answer: str | None
    parent_result_ref: str | None
    summary: str | None

    # 检索上下文
    schema_context: list[str]
    metric_context: list[str]
    method_context: list[str]
    rag_cache_hit: bool

    # SQL 环节
    sql_draft: str | None
    sql_explain: str | None
    sql_risk_level: Literal["low", "high"] | None
    sql_risk_reasons: list[str]
    sql_ast_tables: list[str]
    sql_ast_columns: list[str]
    review_verdict: dict | None
    approval: dict | None

    # 执行结果，只放引用
    result_ref: str | None
    result_meta: dict | None

    # 质检与清洗
    quality_report: dict | None
    quality_passed: bool | None
    cleaned_ref: str | None
    clean_log: list[dict]
    clean_rules_applied: list[str]
    self_check_passed: bool | None
    self_check_notes: list[str]

    # 分析
    analysis_output: dict | None

    # 可视化
    chart_spec: dict | None
    chart_validate_passed: bool | None
    chart_approved: bool | None

    # 异常与预算
    retry_count: int
    sql_retry_count: int
    errors: list[str]
    token_used: int
    sql_calls: int
