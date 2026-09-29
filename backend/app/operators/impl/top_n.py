"""前 N 算子。按指标排序取前 N，可按组取。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import TopNParams


def op_top_n(df: pd.DataFrame, params: TopNParams) -> dict:
    metric = params.metric
    n = params.n
    group_by = params.group_by

    if metric not in df.columns:
        return make_error("top_n", f"列不存在: {metric}")

    work = df.dropna(subset=[metric])
    if work.empty:
        return make_error("top_n", "数据为空")

    ascending = params.order == "asc"
    if group_by:
        valid = [g for g in group_by if g in df.columns]
        if valid:
            result = work.sort_values(metric, ascending=ascending).groupby(valid).head(n)
        else:
            result = work
    else:
        result = work.nlargest(n, metric) if not ascending else work.nsmallest(n, metric)

    data = result.to_dict("records")
    note = f"按 {metric} {'升序' if ascending else '降序'} 取前 {n}"
    return make_result("top_n", data, params.model_dump(), note)
