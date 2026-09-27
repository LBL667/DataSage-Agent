"""仪表盘面板接口。第 1 步为桩实现，第 9 步替换为真实现。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/results")
async def list_results() -> dict:
    return {"results": []}


@router.get("/results/{result_id}")
async def get_result(result_id: str) -> dict:
    return {
        "result_id": result_id,
        "chart_spec": None,
        "source_tables": [],
        "clean_rules_applied": [],
        "thread_id": "",
    }


@router.get("/data/{result_ref}")
async def get_data(result_ref: str, offset: int = 0, limit: int = 100) -> dict:
    return {"columns": [], "rows": [], "total": 0}
