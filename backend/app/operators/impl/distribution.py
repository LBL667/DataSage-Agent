"""分布算子。指标的分位数与直方图。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import DistributionParams


def op_distribution(df: pd.DataFrame, params: DistributionParams) -> dict:
    metric = params.metric
    bins = params.bins

    if metric not in df.columns:
        return make_error("distribution", f"列不存在: {metric}")

    series = df[metric].dropna()
    if series.empty:
        return make_error("distribution", "数据为空")
    if not pd.api.types.is_numeric_dtype(series):
        return make_error("distribution", f"{metric} 非数值列")

    quantiles = {str(q): round(float(v), 4) for q, v in series.quantile([0, 0.25, 0.5, 0.75, 1]).items()}
    hist, edges = pd.cut(series, bins=bins, retbins=True)
    histogram = [{"range": f"[{round(float(edges[i]), 2)}, {round(float(edges[i + 1]), 2)})", "count": int(c)} for i, c in enumerate(hist.value_counts(sort=False).sort_index())]

    data = {"quantiles": quantiles, "histogram": histogram}
    note = f"{metric} 分布，中位数 {quantiles.get('0.5')}"
    return make_result("distribution", data, params.model_dump(), note)
