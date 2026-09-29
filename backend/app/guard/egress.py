"""出域控制基础版。

字段分级三类：可出域、脱敏可出域、禁止出域。第 6 步提供分级与检测函数，
第 8 步在结果进模型前接入。
"""

from __future__ import annotations

from fnmatch import fnmatch


def classify_columns(columns: list[str], blacklist: dict) -> dict[str, list[str]]:
    """把列分为 allowed、masked、forbidden 三类。

    forbidden 命中精确黑名单，masked 命中通配符模式，其余 allowed。
    """
    forbidden = blacklist.get("columns", [])
    patterns = blacklist.get("column_patterns", [])
    result: dict[str, list[str]] = {"allowed": [], "masked": [], "forbidden": []}
    for col in columns:
        if col in forbidden:
            result["forbidden"].append(col)
        elif any(fnmatch(col, p) for p in patterns):
            result["masked"].append(col)
        else:
            result["allowed"].append(col)
    return result


def detect_pii(columns: list[str], blacklist: dict) -> list[str]:
    """返回需要脱敏或禁止出域的列。"""
    classification = classify_columns(columns, blacklist)
    return classification["forbidden"] + classification["masked"]


def sample(rows: list, limit: int) -> list:
    """采样，最多返回 limit 行。"""
    return rows[:limit]
