"""加工节点。质检、清洗、分析、自检四段。

质检只读，清洗改写，顺序固定 readonly_exec → quality_check → data_clean → analyze。
CPU 密集的 pandas 操作用 to_thread 包裹，不阻塞事件循环。
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.clean.rules import apply_rules
from app.config import DATA_DIR
from app.graph.state import AnalysisState
from app.llm import get_structured_llm
from app.middleware.node_wrapper import node
from app.operators.registry import OPERATORS, PARAM_SCHEMAS
from app.quality.probe import probe
from app.storage.result_store import ResultStore

_store = ResultStore(DATA_DIR / "results")


class OperatorCall(BaseModel):
    """模型输出的算子调用指令。"""

    action: str
    params: dict[str, Any] = {}


ANALYZE_SYSTEM_PROMPT = """你是数据分析算子编排器。根据用户诉求与结果列名，选一个算子并给出参数。

可用算子：
- period_compare：周期对比，参数 metric、period(mom 或 yoy)、group_by、time_column
- top_n：前 N，参数 metric、n、group_by、order(desc 或 asc)
- attribution：归因，参数 metric、group_by
- distribution：分布，参数 metric、bins
- correlation：相关性，参数 x、y

只从这些算子里选，参数里的列名必须来自结果列。
"""


@node("quality_check")
async def quality_check(state: AnalysisState) -> dict:
    """质检五项，只读不改数据。"""
    ref = state.get("result_ref")
    if not ref:
        return {
            "quality_passed": False,
            "quality_report": {"passed": False, "checks": [{"check": "结果引用", "passed": False, "detail": "无结果"}]},
        }
    df = await asyncio.to_thread(_store.load, ref)
    report = await asyncio.to_thread(probe, df)
    return {"quality_passed": report["passed"], "quality_report": report}


@node("data_clean")
async def data_clean(state: AnalysisState) -> dict:
    """按配置规则清洗，产出 cleaned_ref 与 clean_log。原始 result_ref 保留。"""
    ref = state.get("result_ref")
    if not ref:
        return {"clean_log": [], "clean_rules_applied": []}
    df = await asyncio.to_thread(_store.load, ref)
    cleaned, log, applied = await asyncio.to_thread(apply_rules, df)
    if not applied:
        return {"cleaned_ref": ref, "clean_log": log, "clean_rules_applied": applied}
    cleaned_ref = await asyncio.to_thread(_store.save, cleaned)
    return {"cleaned_ref": cleaned_ref, "clean_log": log, "clean_rules_applied": applied}


@node("analyze")
async def analyze(state: AnalysisState) -> dict:
    """按算子白名单执行分析。模型只输出算子名与参数，代码由项目自己实现。"""
    ref = state.get("cleaned_ref") or state.get("result_ref")
    if not ref:
        return {"analysis_output": {"operator": None, "note": "无数据可分析"}}
    df = await asyncio.to_thread(_store.load, ref)

    structured = get_structured_llm(OperatorCall)
    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=f"结果列名：{list(df.columns)}\n用户诉求：{state['user_goal']}"),
    ]
    call: OperatorCall = await structured.ainvoke(messages)

    fn = OPERATORS.get(call.action)
    if fn is None:
        return {"analysis_output": {"operator": call.action, "note": f"未知算子 {call.action}"}}

    params_cls = PARAM_SCHEMAS[call.action]
    try:
        params = params_cls(**call.params)
    except Exception as e:  # noqa: BLE001
        return {"analysis_output": {"operator": call.action, "note": f"参数校验失败 {type(e).__name__}"}}

    output = await asyncio.to_thread(fn, df, params)
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
    return {"self_check_passed": passed, "self_check_notes": notes}
