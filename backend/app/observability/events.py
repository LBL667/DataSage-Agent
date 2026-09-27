"""事件模型。

所有节点出站前写同一种结构，供日志面板消费。字段一旦有下游消费就不再改动，
这是唯一一个下游消费方多达两三处的结构，改动代价最高。先写 stdout，后接 SSE 与数据库。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "node_start",
    "node_end",
    "tool_call",
    "approval_request",
    "error",
    "final",
]


class ApprovalInfo(BaseModel):
    """审批信息。"""

    required: bool = False
    decision: str | None = None
    actor: str | None = None


class Event(BaseModel):
    """节点级事件，结构对齐 analysis-agent-spec.md 第 12 节。"""

    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = ""
    session_id: str = ""
    user_id: str = ""
    node: str = ""
    event: EventType = "node_start"
    tool: str | None = None
    input_digest: str | None = None
    target: dict[str, Any] | None = None
    duration_ms: float | None = None
    status: str = "ok"
    approval: ApprovalInfo | None = None


def emit(event: Event) -> None:
    """写出事件。当前写 stdout，阶段一接 SSE，阶段十三接可观测平台。"""
    sys.stdout.write(event.model_dump_json() + "\n")
    sys.stdout.flush()


def emit_json(event: Event) -> str:
    """返回事件的 JSON 字符串，供 SSE 推送复用。"""
    return json.dumps(event.model_dump(), ensure_ascii=False)
