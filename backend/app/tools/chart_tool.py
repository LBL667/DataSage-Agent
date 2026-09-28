"""图表工具。ChartSpec 校验与渲染数据准备。"""

from __future__ import annotations

from app.chart.spec import ChartSpec
from app.chart.validate import validate


def validate_chart(spec: dict, columns: list[str]) -> tuple[bool, list[str], ChartSpec | None]:
    """校验 ChartSpec，返回 (ok, errors, spec)。字段名对不上返回错误。"""
    try:
        spec_obj = ChartSpec(**spec)
    except Exception as e:  # noqa: BLE001
        return False, [f"规格解析失败 {type(e).__name__}"], None
    ok, errors = validate(spec_obj, columns)
    return ok, errors, spec_obj
