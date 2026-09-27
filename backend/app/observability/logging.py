"""结构化日志。

JSON 格式，每条带 trace_id。trace_id 用 contextvar 全链路透传，
从 HTTP 请求进入生成，一路带到每个事件与日志行。
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    """生成新的 trace_id。"""
    return f"tr_{uuid.uuid4().hex[:8]}"


def set_trace_id(trace_id: str) -> None:
    """在当前上下文设置 trace_id。"""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """读取当前上下文的 trace_id，未设置时返回空串。"""
    return _trace_id_var.get()


class JsonFormatter(logging.Formatter):
    """把日志格式化成单行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": get_trace_id(),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc_type"] = record.exc_info[0].__name__
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """初始化根日志，输出到 stdout。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """返回带名字的 logger。"""
    return logging.getLogger(name)
