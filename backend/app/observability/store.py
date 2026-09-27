"""事件存储。

EventStore 单例，职责三件：SQLite 持久化、内存 pub/sub 广播、历史查询。
事件结构对齐 analysis-agent-spec.md 第 12 节，target 与 approval 存 JSON 文本。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from app.observability.events import Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    trace_id TEXT DEFAULT '',
    session_id TEXT DEFAULT '',
    user_id TEXT DEFAULT '',
    node TEXT DEFAULT '',
    event TEXT NOT NULL,
    tool TEXT,
    input_digest TEXT,
    target TEXT,
    duration_ms REAL,
    status TEXT DEFAULT 'ok',
    approval TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""

_RETENTION_DAYS = 30


class EventStore:
    """事件存储，持久化到 SQLite，同时广播给内存订阅者。"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        self._conn = await aiosqlite.connect(str(self.db_path))
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        await self._cleanup()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def publish(self, event: Event) -> None:
        """持久化并广播。订阅者消费慢时丢弃，不阻塞主流程。"""
        if self._conn is not None:
            async with self._lock:
                await self._conn.execute(
                    "INSERT INTO events "
                    "(ts, trace_id, session_id, user_id, node, event, tool, input_digest, target, duration_ms, status, approval) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.ts,
                        event.trace_id,
                        event.session_id,
                        event.user_id,
                        event.node,
                        event.event,
                        event.tool,
                        event.input_digest,
                        json.dumps(event.target, ensure_ascii=False) if event.target is not None else None,
                        event.duration_ms,
                        event.status,
                        event.approval.model_dump_json() if event.approval is not None else None,
                    ),
                )
                await self._conn.commit()

        data = event.model_dump_json()
        for q in list(self._subscribers):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        """订阅事件，返回一个队列，publish 会推入 JSON 字符串。"""
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """取消订阅，SSE 连接断开时调用。"""
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def query(
        self,
        node: str | None = None,
        status: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        approval: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """按条件查历史事件，倒序。"""
        if self._conn is None:
            return []
        sql = "SELECT ts, trace_id, session_id, user_id, node, event, tool, input_digest, target, duration_ms, status, approval FROM events WHERE 1=1"
        params: list = []
        if node:
            sql += " AND node = ?"
            params.append(node)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if from_ts:
            sql += " AND ts >= ?"
            params.append(from_ts)
        if to_ts:
            sql += " AND ts <= ?"
            params.append(to_ts)
        if approval is True:
            sql += " AND event = 'approval_request'"
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        async with self._lock:
            cur = await self._conn.execute(sql, params)
            rows = await cur.fetchall()

        cols = ["ts", "trace_id", "session_id", "user_id", "node", "event", "tool", "input_digest", "target", "duration_ms", "status", "approval"]
        return [self._row_to_event(cols, r) for r in rows]

    async def query_approvals(self, limit: int = 100) -> list[dict]:
        """审批记录单独视图，取 approval 非空的事件。"""
        return await self.query(approval=True, limit=limit)

    @staticmethod
    def _row_to_event(cols: list[str], row: tuple) -> dict:
        d = dict(zip(cols, row))
        for key in ("target", "approval"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except json.JSONDecodeError:
                    pass
        return d

    async def _cleanup(self) -> None:
        """删除超过保留期的记录。"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)).isoformat()
        async with self._lock:
            await self._conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            await self._conn.commit()
