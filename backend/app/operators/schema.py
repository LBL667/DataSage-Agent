"""算子参数 schema。

每个算子用 Pydantic 定义参数，模型的输出据此校验。参数越界在进入算子前就拦住。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PeriodCompareParams(BaseModel):
    metric: str
    period: Literal["mom", "yoy"]
    group_by: list[str] = []
    time_column: str


class TopNParams(BaseModel):
    metric: str
    n: int = Field(ge=1, le=100)
    group_by: list[str] = []
    order: Literal["desc", "asc"] = "desc"


class AttributionParams(BaseModel):
    metric: str
    group_by: list[str]


class DistributionParams(BaseModel):
    metric: str
    bins: int = Field(default=10, ge=2, le=100)


class CorrelationParams(BaseModel):
    x: str
    y: str
