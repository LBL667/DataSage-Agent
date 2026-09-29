"""黑白名单匹配。

表白名单、字段黑名单、语句黑名单。字段支持精确匹配与通配符。
"""

from __future__ import annotations

from fnmatch import fnmatch


def check_whitelist(tables: list[str], whitelist: list[str]) -> list[str]:
    """返回不在白名单里的表。空列表表示全部通过。"""
    return [t for t in tables if t not in whitelist]


def check_column_blacklist(columns: list[str], blacklist: dict) -> list[str]:
    """返回命中敏感字段黑名单的列。精确匹配加通配符匹配。"""
    exact = blacklist.get("columns", [])
    patterns = blacklist.get("column_patterns", [])
    hits = []
    for col in columns:
        if col in exact:
            hits.append(col)
            continue
        if any(fnmatch(col, p) for p in patterns):
            hits.append(col)
    return hits


def check_statement_blacklist(sql: str, blacklist: dict) -> list[str]:
    """返回命中的语句黑名单关键字。大小写不敏感。"""
    statements = blacklist.get("statements", [])
    upper = sql.upper()
    return [s for s in statements if s.upper() in upper]
