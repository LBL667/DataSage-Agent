"""图表规格。图表类型限定五种，让 ChartSpec 可校验。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ChartType = Literal["line", "bar", "scatter", "pie", "table"]


class ChartSpec(BaseModel):
    """图表规格。字段名必须来自结果列。"""

    chart_type: ChartType
    x_field: str
    y_field: str
    series: str | None = None
    title: str = ""
    description: str = ""
