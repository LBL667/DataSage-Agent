"""归因算子。各分组对总体的贡献占比。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import AttributionParams


def op_attribution(df: pd.DataFrame, params: AttributionParams) -> dict:
    metric = params.metric
    group_by = params.group_by

    if metric not in df.columns:
        return make_error("attribution", f"列不存在: {metric}")

    work = df.dropna(subset=[metric])
    if work.empty:
        return make_error("attribution", "数据为空")

    total = work[metric].sum()
    if total == 0:
        return make_error("attribution", "指标总和为零")

    valid = [g for g in group_by if g in df.columns]
    if not valid:
        return make_error("attribution", "无有效分组列")

    grouped = work.groupby(valid)[metric].sum().reset_index()
    grouped["share"] = (grouped[metric] / total).round(4)
    grouped = grouped.sort_values(metric, ascending=False)

    data = grouped.to_dict("records")
    top = data[0] if data else {}
    note = f"{metric} 归因，最大贡献 {top.get(valid[0]) if data else '无'} 占比 {top.get('share') if data else '无'}"
    return make_result("attribution", data, params.model_dump(), note)
