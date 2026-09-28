"""sqlglot 静态校验。

用 AST 不用正则。递归检查所有子节点，抽取真实引用的表和列。
正则会被 union 拼接、子查询、select 星号绕过，这不是理论风险。
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp


class SqlParseError(Exception):
    """SQL 解析失败。解析异常一律判为高风险。"""


# 非 SELECT 的写操作类型，递归命中即违规
_WRITE_TYPES = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter)


def parse(sql: str) -> exp.Expression:
    """解析 SQL，dialect 显式传 mysql，解析失败抛 SqlParseError。"""
    try:
        return sqlglot.parse_one(sql, read="mysql")
    except Exception as e:  # noqa: BLE001
        raise SqlParseError(f"SQL 解析失败: {e}") from e


def check_statement_types(ast: exp.Expression) -> list[str]:
    """递归检查所有子节点，返回命中的写操作类型列表。空列表表示只有 SELECT。"""
    violations = []
    for node in ast.walk():
        if isinstance(node, _WRITE_TYPES):
            violations.append(type(node).__name__)
    return violations


def extract_tables(ast: exp.Expression) -> list[str]:
    """抽取引用的表名，去重保序。正确处理别名、schema 前缀、反引号。"""
    tables: list[str] = []
    for t in ast.find_all(exp.Table):
        name = t.name
        if name and name not in tables:
            tables.append(name)
    return tables


def extract_columns(ast: exp.Expression) -> tuple[list[str], bool]:
    """抽取引用的列名，返回 (columns, has_star)。"""
    columns: list[str] = []
    for c in ast.find_all(exp.Column):
        name = c.name
        if name and name not in columns:
            columns.append(name)
    has_star = any(isinstance(s, exp.Star) for s in ast.find_all(exp.Star))
    return columns, has_star


def inject_limit(sql: str, limit: int) -> str:
    """AST 层注入 LIMIT，不用字符串拼接。"""
    ast = parse(sql)
    ast = ast.limit(limit)
    return ast.sql(dialect="mysql")
