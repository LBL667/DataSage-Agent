"""状态与统计端点。可观测收尾。

慢节点耗时、错误分类、审计总览。统计在查询时聚合，当前事件量小，无需预聚合。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
async def status(request: Request) -> dict:
    """健康与总览统计。"""
    store = request.app.state.store
    return {
        "settings_loaded": request.app.state.settings is not None,
        "graph_loaded": request.app.state.graph is not None,
        "stats": await store.total_stats(),
    }


@router.get("/stats")
async def stats(request: Request) -> dict:
    """慢节点耗时与错误分类。"""
    store = request.app.state.store
    return {
        "slow_nodes": await store.node_stats(),
        "errors": await store.error_stats(),
    }
