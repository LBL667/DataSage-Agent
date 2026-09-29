"""相关性算子。两列皮尔逊相关系数。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import CorrelationParams


def op_correlation(df: pd.DataFrame, params: CorrelationParams) -> dict:
    x = params.x
    y = params.y

    if x not in df.columns or y not in df.columns:
        return make_error("correlation", f"列不存在: {x} 或 {y}")

    work = df[[x, y]].dropna()
    if len(work) < 2:
        return make_error("correlation", "有效样本不足")

    corr = work[x].corr(work[y])
    if pd.isna(corr):
        return make_error("correlation", "相关系数无法计算")

    data = {"x": x, "y": y, "correlation": round(float(corr), 4), "samples": len(work)}
    note = f"{x} 与 {y} 相关系数 {round(float(corr), 4)}"
    return make_result("correlation", data, params.model_dump(), note)
