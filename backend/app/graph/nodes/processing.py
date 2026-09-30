"""加工节点。质检、清洗、分析、自检四段。

质检只读，清洗改写，顺序固定 readonly_exec → quality_check → data_clean → analyze。
工具调用走 MCP 通道，通过 ToolRegistry 装配。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.graph.state import AnalysisState
from app.llm import get_structured_llm
from app.middleware.node_wrapper import node
from app.tools.registrar import get_registry


class OperatorCall(BaseModel):
    """模型输出的算子调用指令。"""

    action: str
    params: dict[str, Any] = {}


ANALYZE_SYSTEM_PROMPT = """你是数据分析算子编排器。根据用户诉求与结果列名，选一个算子并给出参数。

可用算子：
- enumerate：枚举某列的唯一取值与计数，参数 column。适合「有哪些类别」「列出 XX」这类查询，或结果只有一列文本分类时
- period_compare：周期对比，参数 metric、period(mom 或 yoy)、group_by、time_column
- top_n：前 N，参数 metric、n、group_by、order(desc 或 asc)
- attribution：归因，参数 metric、group_by
- distribution：分布，参数 metric、bins
- correlation：相关性，参数 x、y

规则：
1. 只从这些算子里选
2. metric、x、y、time_column 必须是结果列里的列名
3. group_by 是字符串数组，例如 ["channel"]，即使只有一个分组列也要用数组
4. 结果只有文本分类列、用户想看有哪些取值时，用 enumerate 而不是 distribution
"""


@node("quality_check")
async def quality_check(state: AnalysisState) -> dict:
    """质检五项，只读不改数据。走 MCP 通道。"""
    ref = state.get("result_ref")
    if not ref:
        return {
            "quality_passed": False,
            "quality_report": {"passed": False, "checks": [{"check": "结果引用", "passed": False, "detail": "无结果"}]},
            "sql_retry_count": int(state.get("sql_retry_count", 0)) + 1,
        }
    report = await get_registry().call("quality_probe", data_ref=ref)
    if not report["passed"]:
        # 质检不通过，递增重试计数，避免无限回退
        return {
            "quality_passed": False,
            "quality_report": report,
            "sql_retry_count": int(state.get("sql_retry_count", 0)) + 1,
        }
    return {"quality_passed": True, "quality_report": report}


@node("data_clean")
async def data_clean(state: AnalysisState) -> dict:
    """按配置规则清洗，产出 cleaned_ref 与 clean_log。走 MCP 通道。"""
    ref = state.get("result_ref")
    if not ref:
        return {"clean_log": [], "clean_rules_applied": []}
    result = await get_registry().call("clean_exec", data_ref=ref)
    return {
        "cleaned_ref": result["cleaned_ref"],
        "clean_log": result["clean_log"],
        "clean_rules_applied": result["clean_rules_applied"],
    }


@node("analyze")
async def analyze(state: AnalysisState) -> dict:
    """按算子白名单执行分析。模型只输出算子名与参数，执行走 MCP 通道。"""
    ref = state.get("cleaned_ref") or state.get("result_ref")
    if not ref:
        return {"analysis_output": {"operator": None, "note": "无数据可分析"}}

    meta = state.get("result_meta") or {}
    columns = list(meta.get("columns", []))

    structured = get_structured_llm(OperatorCall)
    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=f"结果列名：{columns}\n用户诉求：{state['user_goal']}"),
    ]
    call: OperatorCall = await structured.ainvoke(messages)

    output = await get_registry().call("run_operator", action=call.action, params=call.params, data_ref=ref)
    return {"analysis_output": output}


@node("self_check")
async def self_check(state: AnalysisState) -> dict:
    """分析结果自检。异常则回退重写 SQL。"""
    output = state.get("analysis_output") or {}
    notes: list[str] = []
    passed = True
    note = output.get("note", "")
    if note.startswith("列不存在") or note.startswith("数据为空") or note.startswith("未知算子") or note.startswith("参数校验"):
        passed = False
        notes.append(note)
    if output.get("data") is None:
        passed = False
        notes.append("算子无有效输出")
    result: dict = {"self_check_passed": passed, "self_check_notes": notes}
    if not passed:
        # 自检不通过，递增重试计数，避免无限回退
        result["sql_retry_count"] = int(state.get("sql_retry_count", 0)) + 1
    return result
