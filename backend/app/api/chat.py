"""对话面板接口。第 4 步真实现。

事件统一走 EventStore，节点事件由 node_wrapper 埋点，审批与最终结果由跑图任务
构造，chat 端点订阅当前会话的事件流转发给 SSE。实时流带 SQL 供前端弹窗，
持久化经 emit_event 脱敏。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator, Literal

from fastapi import APIRouter, Request
from langgraph.types import Command
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.middleware.observability import digest, emit_event
from app.observability.events import Event, get_store
from app.observability.logging import new_trace_id

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str


class ResumeRequest(BaseModel):
    decision: Literal["approve", "edit", "cancel"]
    comment: str | None = None


async def _run_graph(graph, stream_input, config: dict, trace_id: str, session_id: str) -> None:
    """后台跑图，构造审批请求与最终结果事件写入 EventStore。"""
    result_ref = None
    result_meta = None
    try:
        async for chunk in graph.astream(stream_input, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    for iv in update:
                        payload = iv.value or {}
                        sql = payload.get("sql", "")
                        await emit_event(
                            Event(
                                trace_id=trace_id,
                                session_id=session_id,
                                node="human_sql_approve",
                                event="approval_request",
                                input_digest=digest(sql),
                                target={"sql": sql, "explain": payload.get("explain")},
                            )
                        )
                    return
                if node == "readonly_exec":
                    result_ref = update.get("result_ref")
                    result_meta = update.get("result_meta")

        await emit_event(
            Event(
                trace_id=trace_id,
                session_id=session_id,
                node="respond",
                event="final",
                target={"result_ref": result_ref, "result_meta": result_meta},
            )
        )
    except Exception:  # noqa: BLE001
        await emit_event(
            Event(trace_id=trace_id, session_id=session_id, node="", event="error", status="error")
        )


async def _stream_graph(graph, stream_input, config: dict, trace_id: str, session_id: str) -> AsyncGenerator[dict, None]:
    """订阅 EventStore，跑图，把当前会话的事件转发到 SSE。"""
    store = get_store()
    if store is None:
        yield {"event": "error", "data": '{"event":"error","status":"error"}'}
        return

    q = store.subscribe()
    task = asyncio.create_task(_run_graph(graph, stream_input, config, trace_id, session_id))
    try:
        while True:
            data = await q.get()
            ev = json.loads(data)
            if ev.get("session_id") != session_id:
                continue
            yield {"event": ev.get("event"), "data": data}
            if ev.get("event") in ("final", "error"):
                break
    finally:
        store.unsubscribe(q)
        if not task.done():
            task.cancel()


@router.post("")
async def chat(req: ChatRequest, request: Request) -> EventSourceResponse:
    """发起对话，SSE 推事件流，跑到审批中断或完成。"""
    graph = request.app.state.graph
    thread_id = req.thread_id or f"ss_{uuid.uuid4().hex[:8]}"
    trace_id = new_trace_id()
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "user_goal": req.message,
        "session_id": thread_id,
        "trace_id": trace_id,
        "messages": [{"role": "user", "content": req.message}],
    }
    return EventSourceResponse(_stream_graph(graph, initial, config, trace_id, thread_id))


@router.post("/{thread_id}/resume")
async def resume(thread_id: str, req: ResumeRequest, request: Request) -> EventSourceResponse:
    """审批回传，恢复图继续推事件。"""
    graph = request.app.state.graph
    trace_id = new_trace_id()
    config = {"configurable": {"thread_id": thread_id}}
    cmd = Command(resume={"decision": req.decision, "comment": req.comment})
    return EventSourceResponse(_stream_graph(graph, cmd, config, trace_id, thread_id))


@router.get("/{thread_id}/history")
async def history(thread_id: str, request: Request) -> dict:
    """拉取会话历史消息。"""
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = await graph.aget_state(config)
        values = snapshot.values if snapshot else {}
        return {"thread_id": thread_id, "messages": values.get("messages", [])}
    except Exception:  # noqa: BLE001
        return {"thread_id": thread_id, "messages": []}


@router.get("/threads")
async def list_threads(request: Request) -> dict:
    """会话列表，从事件历史推导有事件的会话。"""
    store = request.app.state.store
    events = await store.query(limit=500)
    seen: dict[str, str] = {}
    for e in events:
        sid = e.get("session_id")
        if sid and sid not in seen:
            seen[sid] = e.get("ts", "")
    threads = [{"thread_id": sid, "updated_at": ts} for sid, ts in seen.items()]
    return {"threads": threads}


@router.post("/threads")
async def create_thread() -> dict:
    return {"thread_id": f"ss_{uuid.uuid4().hex[:8]}"}


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    # checkpointer 删除在后续步骤实现
    return {"ok": True}
