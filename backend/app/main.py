"""FastAPI 入口与生命周期。

图在 lifespan 里编译一次，不每个请求都 compile。配置缺失时降级启动，
/health 反映真实状态，服务不会因为缺 .env 而无法起来。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, config, dashboard, logs, rag, status
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

    from app.config import DATA_DIR, load_settings
    from app.errors import ConfigError

    try:
        settings = load_settings()
        logger.info("settings loaded")
    except ConfigError as e:
        settings = None
        logger.warning("settings not loaded: %s", e.message)

    # 事件存储，SQLite 持久化加内存广播
    from app.observability.events import set_store
    from app.observability.store import EventStore

    store = EventStore(DATA_DIR / "events.sqlite")
    await store.open()
    set_store(store)
    app.state.store = store
    logger.info("event store loaded")

    # 用户存储，种子 admin 用户
    from app.storage.user_store import UserStore

    user_store = UserStore(DATA_DIR / "users.sqlite")
    await user_store.open()
    app.state.user_store = user_store
    logger.info("user store loaded")

    # 第 3 步接入图编译，失败时降级，服务仍可启动
    try:
        from app.graph.build import build_graph

        graph = await build_graph()
        logger.info("graph loaded")
    except Exception as e:  # 图未就绪时不阻断服务
        graph = None
        logger.warning("graph not loaded: %s", type(e).__name__)

    # 第 11 步入库 schema 集合，失败不阻断服务
    try:
        from app.rag.ingest import ingest_schema

        count = await ingest_schema()
        logger.info("schema 入库 %d 个 chunk", count)
    except Exception as e:  # noqa: BLE001
        logger.warning("schema 入库失败: %s", type(e).__name__)

    app.state.graph = graph
    app.state.settings = settings

    yield

    from app.graph.build import close_graph

    await close_graph()
    await store.close()
    await user_store.close()


app = FastAPI(title="DataSage Agent", lifespan=lifespan)

# 前端开发期跨域，允许 Vite 默认端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(config.router)
app.include_router(dashboard.router)
app.include_router(rag.router)
app.include_router(logs.router)
app.include_router(status.router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "settings_loaded": settings is not None,
        "graph_loaded": graph is not None,
    }
