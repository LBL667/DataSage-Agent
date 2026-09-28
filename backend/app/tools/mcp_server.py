"""MCP 工具 server。

把能力层工具封成 MCP 形态，通过 FastMCP 注册。工具与内部函数解耦，
接口签名在本地直调时就已经按 MCP 形态设计，这一步只是装配层的替换。
写操作一律不开，只暴露只读与统计能力。
"""

from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from app.clean.rules import apply_rules
from app.config import DATA_DIR
from app.middleware.credential import resolve_credential
from app.operators.registry import OPERATORS, PARAM_SCHEMAS
from app.quality.probe import probe
from app.storage.result_store import ResultStore
from app.tools.chart_tool import validate_chart as _validate_chart
from app.tools.mysql_tool import execute_query

mcp_server = FastMCP("datasage")

_store = ResultStore(DATA_DIR / "results")


@mcp_server.tool
async def mysql_query(sql: str, max_rows: int = 100000) -> dict:
    """执行只读 SQL，落盘结果，返回 result_ref 与 meta。只读连接，超时十秒，强制 rollback。"""
    ref, meta = await execute_query(sql, max_rows=max_rows)
    return {"result_ref": ref, "meta": meta}


@mcp_server.tool
async def quality_probe(data_ref: str) -> dict:
    """对结果做五项质检，只读不改数据。"""
    df = await asyncio.to_thread(_store.load, data_ref)
    return await asyncio.to_thread(probe, df)


@mcp_server.tool
async def clean_exec(data_ref: str, rules: list | None = None) -> dict:
    """按规则清洗结果，返回 cleaned_ref 与 clean_log。只接受已登记规则。"""
    df = await asyncio.to_thread(_store.load, data_ref)
    cleaned, log, applied = await asyncio.to_thread(apply_rules, df, rules)
    cleaned_ref = await asyncio.to_thread(_store.save, cleaned) if applied else data_ref
    return {"cleaned_ref": cleaned_ref, "clean_log": log, "clean_rules_applied": applied}


@mcp_server.tool
async def run_operator(action: str, params: dict, data_ref: str) -> dict:
    """按白名单算子执行分析，不接受自由代码。"""
    df = await asyncio.to_thread(_store.load, data_ref)
    fn = OPERATORS.get(action)
    if fn is None:
        return {"operator": action, "data": None, "params": params, "note": f"未知算子 {action}"}
    params_cls = PARAM_SCHEMAS[action]
    # 参数规范化：group_by 字符串转列表，防御模型输出 str 而 schema 要 list
    normalized = dict(params)
    if isinstance(normalized.get("group_by"), str):
        normalized["group_by"] = [normalized["group_by"]]
    try:
        p = params_cls(**normalized)
    except Exception as e:  # noqa: BLE001
        return {"operator": action, "data": None, "params": params, "note": f"参数校验失败 {type(e).__name__}"}
    return await asyncio.to_thread(fn, df, p)


@mcp_server.tool
async def chart_validate(chart_spec: dict, columns: list) -> dict:
    """校验 ChartSpec 字段名，字段名必须存在于结果列。"""
    ok, errors, _ = _validate_chart(chart_spec, columns)
    return {"ok": ok, "errors": errors}


@mcp_server.tool
async def credential_resolve(user_id: str) -> dict:
    """解析连接配置，仅编排层可调，凭据不进返回结果。"""
    cred = resolve_credential(user_id)
    return {"host": cred.host, "port": cred.port, "user": cred.user, "database": cred.database}


@mcp_server.tool
async def rag_search(query: str, collection: str, top_k: int = 5) -> dict:
    """检索上下文，第 11 步接入 RAG，当前返回空。"""
    return {"chunks": []}
