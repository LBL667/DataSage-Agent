"""仪表盘面板接口。第 9 步真实现。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.config import DATA_DIR
from app.storage.dashboard_store import DashboardStore
from app.storage.result_store import ResultStore

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_dashboard = DashboardStore(DATA_DIR / "dashboard")
_results = ResultStore(DATA_DIR / "results")


@router.get("/results")
async def list_results() -> dict:
    return {"results": _dashboard.list()}


@router.get("/results/{result_id}")
async def get_result(result_id: str) -> dict:
    result = _dashboard.get(result_id)
    if result is None:
        return {
            "result_id": result_id,
            "chart_spec": None,
            "source_tables": [],
            "clean_rules_applied": [],
            "thread_id": "",
        }
    return result


@router.get("/data/{result_ref}")
async def get_data(result_ref: str, offset: int = 0, limit: int = 100) -> dict:
    if not _results.exists(result_ref):
        return {"columns": [], "rows": [], "total": 0}
    df = await asyncio.to_thread(_results.load, result_ref)
    total = len(df)
    page = df.iloc[offset : offset + limit]
    return {"columns": list(df.columns), "rows": page.values.tolist(), "total": total}
