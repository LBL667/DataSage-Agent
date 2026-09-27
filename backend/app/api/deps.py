"""依赖注入。图实例、事件存储、配置，从 app.state 读取。"""

from __future__ import annotations

from typing import Any

from fastapi import Request


def get_graph(request: Request) -> Any:
    """返回编译后的图实例，lifespan 里已注入。"""
    return request.app.state.graph


def get_store(request: Request) -> Any:
    """返回 EventStore 实例。"""
    return request.app.state.store


def get_settings(request: Request) -> Any:
    """返回 Settings 实例，配置缺失时可能为 None。"""
    return request.app.state.settings
