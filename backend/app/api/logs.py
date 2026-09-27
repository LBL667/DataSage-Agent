"""日志面板接口。第 4 步真实现。

事件查询与审批记录读 SQLite，实时订阅走内存广播。
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/events")
async def query_events(
    request: Request,
    node: str | None = None,
    status: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    approval: bool | None = None,
    limit: int = 100,
) -> dict:
    store = request.app.state.store
    events = await store.query(
        node=node,
        status=status,
        from_ts=from_ts,
        to_ts=to_ts,
        approval=approval,
        limit=limit,
    )
    return {"events": events}


@router.get("/stream")
async def stream(request: Request) -> EventSourceResponse:
    """SSE 实时订阅，事件级推送。"""
    store = request.app.state.store

    async def gen() -> AsyncGenerator[dict, None]:
        q = store.subscribe()
        try:
            while True:
                data = await q.get()
                yield {"event": "event", "data": data}
        finally:
            store.unsubscribe(q)

    return EventSourceResponse(gen())


@router.get("/approvals")
async def list_approvals(request: Request, limit: int = 100) -> dict:
    store = request.app.state.store
    approvals = await store.query_approvals(limit=limit)
    return {"approvals": approvals}
