"""图表校验。字段名必须存在于结果列，对不上就回炉。"""

from __future__ import annotations

from app.chart.spec import ChartSpec


def validate(spec: ChartSpec, columns: list[str]) -> tuple[bool, list[str]]:
    """校验 ChartSpec 的字段名是否存在于结果列。"""
    errors: list[str] = []
    for field in ("x_field", "y_field", "series"):
        value = getattr(spec, field, None)
        if value and value not in columns:
            errors.append(f"字段 {value} 不存在于结果列 {columns}")
    return len(errors) == 0, errors
