"""日志面板接口。第 1 步为桩实现，第 4 步接 SSE 真实现。"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/events")
async def query_events(
    node: str | None = None,
    status: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    approval: bool | None = None,
) -> dict:
    return {"events": []}


@router.get("/stream")
async def stream() -> EventSourceResponse:
    """SSE 实时订阅。桩实现每 5 秒推一条心跳。"""

    async def gen() -> AsyncGenerator[dict, None]:
        while True:
            yield {"event": "ping", "data": '{"status": "ok"}'}
            await asyncio.sleep(5)

    return EventSourceResponse(gen())


@router.get("/approvals")
async def list_approvals() -> dict:
    return {"approvals": []}
