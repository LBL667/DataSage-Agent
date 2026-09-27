"""验证第 4、5 步。

四类验证：事件广播与持久化、审批中断与恢复、节点超时被 TimeoutPolicy 拦截。
用 mock 图，不依赖 LLM 与 MySQL。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiosqlite  # noqa: E402
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, RetryPolicy, TimeoutPolicy, interrupt  # noqa: E402

from app.config import DATA_DIR  # noqa: E402
from app.observability.events import Event  # noqa: E402
from app.observability.store import EventStore  # noqa: E402


class MockState(TypedDict):
    sql_draft: str | None
    approval: dict | None
    result: str | None


def mock_generate(state):
    return {"sql_draft": "SELECT 1 AS ok"}


def mock_approve(state):
    decision = interrupt({"sql": state["sql_draft"]})
    return {"approval": {"decision": decision}}


def mock_exec(state):
    return {"result": "done"}


async def test_event_store() -> None:
    store = EventStore(DATA_DIR / "test_events.sqlite")
    await store.open()
    q = store.subscribe()

    await store.publish(
        Event(session_id="s1", trace_id="tr1", node="sql_generate", event="node_end", status="ok")
    )
    data = await q.get()
    print("[通过] 事件广播收到:", data[:80])

    events = await store.query(limit=10)
    print("[通过] 持久化查询行数:", len(events), "session:", events[0]["session_id"])

    store.unsubscribe(q)
    await store.close()


async def test_interrupt_resume() -> None:
    g = StateGraph(MockState)
    g.add_node("mock_generate", mock_generate)
    g.add_node("mock_approve", mock_approve)
    g.add_node("mock_exec", mock_exec)
    g.add_edge(START, "mock_generate")
    g.add_edge("mock_generate", "mock_approve")
    g.add_edge("mock_approve", "mock_exec")
    g.add_edge("mock_exec", END)

    db = DATA_DIR / "test_checkpoint.sqlite"
    conn = await aiosqlite.connect(str(db))
    graph = g.compile(checkpointer=AsyncSqliteSaver(conn))

    config = {"configurable": {"thread_id": "t1"}}

    # 首次跑到中断
    async for chunk in graph.astream({}, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            iv = chunk["__interrupt__"][0]
            print("[通过] 检测到审批中断, payload:", iv.value)

    # 恢复
    async for chunk in graph.astream(Command(resume="approve"), config, stream_mode="updates"):
        if "mock_exec" in chunk:
            print("[通过] 恢复后执行完成:", chunk["mock_exec"])

    await conn.close()


async def test_timeout() -> None:
    class TS(TypedDict):
        done: bool

    async def slow_node(state):
        await asyncio.sleep(1.0)
        return {"done": True}

    g = StateGraph(TS)
    g.add_node(
        "slow_node",
        slow_node,
        timeout=TimeoutPolicy(run_timeout=0.2),
        retry_policy=RetryPolicy(max_attempts=1),
    )
    g.add_edge(START, "slow_node")
    g.add_edge("slow_node", END)
    graph = g.compile()

    try:
        await graph.ainvoke({}, {"configurable": {"thread_id": "t2"}})
        print("[未通过] 超时节点没有被拦截")
    except Exception as e:  # noqa: BLE001
        print(f"[通过] 超时被拦截: {type(e).__name__}")


async def main() -> None:
    await test_event_store()
    await test_interrupt_resume()
    await test_timeout()


if __name__ == "__main__":
    asyncio.run(main())
