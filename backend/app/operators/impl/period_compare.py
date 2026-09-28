"""周期对比算子。环比 mom 或同比 yoy。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import PeriodCompareParams


def op_period_compare(df: pd.DataFrame, params: PeriodCompareParams) -> dict:
    metric = params.metric
    time_col = params.time_column
    group_by = params.group_by

    if metric not in df.columns or time_col not in df.columns:
        return make_error("period_compare", f"列不存在: {metric} 或 {time_col}")

    work = df.copy()
    work[time_col] = pd.to_datetime(work[time_col], errors="coerce")
    work = work.dropna(subset=[time_col, metric])
    if work.empty:
        return make_error("period_compare", "数据为空")

    period = "M" if params.period == "mom" else "Y"
    work["_period"] = work[time_col].dt.to_period(period)

    keys = ["_period"] + [g for g in group_by if g in df.columns]
    grouped = work.groupby(keys)[metric].sum().reset_index()

    if group_by:
        grouped["_change"] = grouped.groupby(group_by)[metric].pct_change()
    else:
        grouped["_change"] = grouped[metric].pct_change()

    grouped["_period"] = grouped["_period"].astype(str)
    data = grouped.to_dict("records")
    note = f"{metric} 按 {params.period} 对比，共 {len(data)} 个周期"
    return make_result("period_compare", data, params.model_dump(), note)
