"""算子实现包。每个算子无副作用，返回三段内容：数据、参数、说明。"""

from __future__ import annotations

from typing import Any


def make_result(operator: str, data: Any, params: Any, note: str) -> dict:
    """构造算子返回结构。"""
    return {"operator": operator, "data": data, "params": params, "note": note}


def make_error(operator: str, note: str) -> dict:
    """构造算子失败结构。"""
    return {"operator": operator, "data": None, "params": None, "note": note}
