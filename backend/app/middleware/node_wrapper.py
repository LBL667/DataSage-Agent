"""节点装饰器。

只做埋点与凭据注入，不做超时与错误处理，那两件交给框架的 TimeoutPolicy
与 RetryPolicy。埋点失败不阻断节点执行。
"""

from __future__ import annotations

from functools import wraps
from time import perf_counter

from app.middleware.observability import emit_event
from app.observability.events import Event


async def _safe_emit(event: Event) -> None:
    """埋点失败不能中断流程。"""
    try:
        await emit_event(event)
    except Exception:  # noqa: BLE001
        pass


def node(name: str, *, needs_credential: bool = False):
    """节点装饰器，进入埋 node_start，退出埋 node_end 带耗时，异常埋 error 后 re-raise。

    needs_credential 标记该节点需要数据库凭据。当前单用户方案 A 下凭据仍在
    mysql_tool 内部解析，此标记仅作声明，多用户改造时在此注入。
    """

    def deco(fn):
        @wraps(fn)
        async def wrapper(state, *args, **kwargs):
            trace_id = state.get("trace_id", "")
            session_id = state.get("session_id", "")
            await _safe_emit(
                Event(trace_id=trace_id, session_id=session_id, node=name, event="node_start")
            )
            t0 = perf_counter()
            try:
                out = await fn(state, *args, **kwargs)
            except Exception:
                await _safe_emit(
                    Event(
                        trace_id=trace_id,
                        session_id=session_id,
                        node=name,
                        event="error",
                        status="error",
                    )
                )
                raise
            ms = (perf_counter() - t0) * 1000
            await _safe_emit(
                Event(
                    trace_id=trace_id,
                    session_id=session_id,
                    node=name,
                    event="node_end",
                    duration_ms=ms,
                    status="ok",
                )
            )
            return out

        return wrapper

    return deco
