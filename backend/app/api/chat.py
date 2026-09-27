"""对话面板接口。第 1 步为桩实现，第 4 步替换为真实现。"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str


class ResumeRequest(BaseModel):
    decision: str
    comment: str | None = None


@router.post("")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """发起对话。桩实现返回演示事件流。"""

    async def gen() -> AsyncGenerator[dict, None]:
        yield {
            "event": "node_start",
            "data": '{"node": "sql_generate", "status": "ok", "trace_id": "tr_demo"}',
        }
        await asyncio.sleep(0.05)
        yield {
            "event": "final",
            "data": '{"content": "这是桩数据，第 4 步替换为真实现", "trace_id": "tr_demo"}',
        }

    return EventSourceResponse(gen())


@router.get("/threads")
async def list_threads() -> dict:
    return {"threads": []}


@router.post("/threads")
async def create_thread() -> dict:
    return {"thread_id": "ss_demo"}


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    return {"ok": True}


@router.get("/{thread_id}/history")
async def history(thread_id: str) -> dict:
    return {"thread_id": thread_id, "messages": []}


@router.post("/{thread_id}/resume")
async def resume(thread_id: str, req: ResumeRequest) -> dict:
    return {"ok": True, "trace_id": "tr_demo"}
