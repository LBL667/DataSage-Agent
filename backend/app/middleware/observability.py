"""事件写入。

统一 async 发布入口。脱敏在写入前做，不存原文再展示时脱敏。
"""

from __future__ import annotations

import hashlib
import sys

from app.observability.events import Event, get_store

# 事件 target 里不允许出现这些键，命中即摘除
_SENSITIVE_TARGET_KEYS = {"sql", "password", "credential", "token", "secret"}


def digest(text: str) -> str:
    """计算输入摘要，避免把 SQL 原文写进事件。"""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _sanitize(event: Event) -> Event:
    """脱敏兜底，摘除 target 里的敏感键。"""
    if event.target:
        event.target = {k: v for k, v in event.target.items() if k not in _SENSITIVE_TARGET_KEYS}
    return event


async def emit_event(event: Event) -> None:
    """写入事件到全局 EventStore，未初始化时降级写 stdout。"""
    event = _sanitize(event)
    store = get_store()
    if store is not None:
        await store.publish(event)
        return
    sys.stdout.write(event.model_dump_json() + "\n")
    sys.stdout.flush()
