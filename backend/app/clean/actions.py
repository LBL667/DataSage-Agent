"""清洗动作。

每个动作无副作用，返回新 DataFrame。防御空数据、全 NULL 列、除零。
"""

from __future__ import annotations

import pandas as pd


def _numeric_cols(df: pd.DataFrame, target: list[str]) -> list[str]:
    """过滤出目标列中的数值列。"""
    return [c for c in target if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]


def drop_duplicate(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """去重。有 key 按 key 去重，否则全列去重。"""
    key = [k for k in rule.get("key", []) if k in df.columns]
    if key:
        return df.drop_duplicates(subset=key).reset_index(drop=True)
    return df.drop_duplicates().reset_index(drop=True)


def fill_null(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """空值填充。数值列按策略填充，非数值列填空串。"""
    target = rule.get("target", [])
    strategy = rule.get("strategy", "zero")
    cols = [c for c in target if c in df.columns] or list(df.columns)
    result = df.copy()
    for col in cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            if strategy == "mean":
                result[col] = df[col].fillna(df[col].mean())
            else:
                result[col] = df[col].fillna(0)
        else:
            result[col] = df[col].fillna("")
    return result


def cast(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """类型转换。转换失败保留原值。"""
    target = rule.get("target", [])
    to = rule.get("to", "str")
    dtype_map = {
        "datetime": "datetime64[ns]",
        "int": "int64",
        "float": "float64",
        "str": "string",
    }
    cols = [c for c in target if c in df.columns]
    result = df.copy()
    for col in cols:
        try:
            result[col] = df[col].astype(dtype_map.get(to, to))
        except Exception:  # noqa: BLE001
            continue
    return result


def clip_outlier(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """异常值裁剪。IQR 方法，除零防御。"""
    target = rule.get("target", [])
    factor = float(rule.get("factor", 3))
    cols = _numeric_cols(df, target)
    result = df.copy()
    for col in cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - factor * iqr
        upper = q3 + factor * iqr
        result[col] = df[col].clip(lower, upper)
    return result


def unit_convert(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """单位统一，按因子缩放。"""
    target = rule.get("target", [])
    factor = float(rule.get("factor", 1))
    cols = _numeric_cols(df, target)
    result = df.copy()
    for col in cols:
        result[col] = df[col] * factor
    return result


ACTIONS = {
    "drop_duplicate": drop_duplicate,
    "fill_null": fill_null,
    "cast": cast,
    "clip_outlier": clip_outlier,
    "unit_convert": unit_convert,
}
