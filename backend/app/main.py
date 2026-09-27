"""FastAPI 入口与生命周期。

图在 lifespan 里编译一次，不每个请求都 compile。配置缺失时降级启动，
/health 反映真实状态，服务不会因为缺 .env 而无法起来。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import chat, config, dashboard, logs, rag
from app.errors import AppError
from app.observability.logging import (
    get_logger,
    get_trace_id,
    new_trace_id,
    set_trace_id,
    setup_logging,
)

logger = get_logger("app.main")

# lifespan 里赋值，图编译一次后全局复用
graph: Any = None
settings: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, settings

    setup_logging()

    from app.config import load_settings
    from app.errors import ConfigError

    try:
        settings = load_settings()
        logger.info("settings loaded")
    except ConfigError as e:
        settings = None
        logger.warning("settings not loaded: %s", e.message)

    # 第 3 步接入图编译，失败时降级，服务仍可启动
    try:
        from app.graph.build import build_graph

        graph = await build_graph()
        logger.info("graph loaded")
    except Exception as e:  # 图未就绪时不阻断服务
        graph = None
        logger.warning("graph not loaded: %s", type(e).__name__)

    yield

    from app.graph.build import close_graph

    await close_graph()


app = FastAPI(title="DataSage Agent", lifespan=lifespan)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or new_trace_id()
    set_trace_id(trace_id)
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "trace_id": get_trace_id(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "code": "PARAM_ERROR",
            "message": "请求体字段缺失或类型不符",
            "retryable": False,
            "trace_id": get_trace_id(),
        },
    )


app.include_router(chat.router)
app.include_router(config.router)
app.include_router(dashboard.router)
app.include_router(rag.router)
app.include_router(logs.router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "settings_loaded": settings is not None,
        "graph_loaded": graph is not None,
    }
