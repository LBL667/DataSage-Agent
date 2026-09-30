"""枚举算子。列出某列的唯一取值与计数，处理类别列表类查询。"""

from __future__ import annotations

import pandas as pd

from app.operators.impl import make_error, make_result
from app.operators.schema import EnumerateParams


def op_enumerate(df: pd.DataFrame, params: EnumerateParams) -> dict:
    column = params.column
    if column not in df.columns:
        return make_error("enumerate", f"列不存在: {column}")

    counts = df[column].value_counts().reset_index()
    counts.columns = [column, "count"]
    data = counts.head(params.top).to_dict("records")
    total = int(df[column].nunique())
    note = f"{column} 共 {total} 个取值"
    return make_result("enumerate", data, params.model_dump(), note)
