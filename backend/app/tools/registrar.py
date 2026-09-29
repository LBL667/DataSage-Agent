"""工具注册表。

工具与内部函数解耦，节点通过注册表走 MCP 通道调用。MCPAdapter 装配，
调用返回值从 ContentBlock 解包。
"""

from __future__ import annotations

import json

from langchain.mcp import MCPAdapter

from app.tools.mcp_server import mcp_server

# 工具元数据清单，7 个工具，写操作一律不开
TOOL_CATALOG = [
    {"name": "mysql_query", "description": "执行只读 SQL，返回 result_ref 与 meta"},
    {"name": "quality_probe", "description": "结果五项质检，只读不改数据"},
    {"name": "clean_exec", "description": "按规则清洗结果，返回 cleaned_ref 与 clean_log"},
    {"name": "run_operator", "description": "按白名单算子执行分析"},
    {"name": "chart_validate", "description": "校验 ChartSpec 字段名"},
    {"name": "credential_resolve", "description": "解析连接配置，仅编排层可调"},
    {"name": "rag_search", "description": "检索上下文"},
]


def _unwrap(result):
    """从 MCP ContentBlock 列表解包出返回值。"""
    if isinstance(result, list) and result:
        item = result[0]
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return text
    return result


class ToolRegistry:
    """工具注册表，MCPAdapter 装配，节点走 MCP 通道调用。"""

    def __init__(self):
        self._adapter = MCPAdapter(mcp_server)
        self._tools: dict = {}
        self._ready = False

    async def init(self) -> None:
        if self._ready:
            return
        self._tools = {t.name: t for t in await self._adapter.list_tools()}
        self._ready = True

    async def call(self, name: str, **kwargs):
        """调用 MCP 工具并解包返回值。"""
        await self.init()
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"未注册的工具 {name}")
        result = await tool.ainvoke(kwargs)
        return _unwrap(result)


_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """返回全局工具注册表。"""
    return _registry
