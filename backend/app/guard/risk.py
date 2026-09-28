"""风险分级。

low 需同时满足全部条件：只有 SELECT、表全白名单、无敏感列、无 select 星号、
无语句黑名单命中。其余判 high。
"""

from __future__ import annotations

from app.guard import ast_check, policy


def assess(sql: str, whitelist: list[str], blacklist: dict) -> dict:
    """评估 SQL 风险，返回 level、reasons 与 AST 抽取结果。"""
    result: dict = {
        "level": "high",
        "reasons": [],
        "tables": [],
        "columns": [],
        "has_star": False,
        "statement_violations": [],
    }

    try:
        ast = ast_check.parse(sql)
    except ast_check.SqlParseError as e:
        result["reasons"] = [str(e)]
        return result

    result["statement_violations"] = ast_check.check_statement_types(ast)
    result["tables"] = ast_check.extract_tables(ast)
    columns, has_star = ast_check.extract_columns(ast)
    result["columns"] = columns
    result["has_star"] = has_star

    out_of_whitelist = policy.check_whitelist(result["tables"], whitelist)
    sensitive = policy.check_column_blacklist(columns, blacklist)
    statement_hits = policy.check_statement_blacklist(sql, blacklist)

    reasons: list[str] = []
    if result["statement_violations"]:
        reasons.append(f"含写操作: {result['statement_violations']}")
    if out_of_whitelist:
        reasons.append(f"表不在白名单: {out_of_whitelist}")
    if sensitive:
        reasons.append(f"命中敏感列: {sensitive}")
    if has_star:
        reasons.append("select * 无法确认列级安全")
    if statement_hits:
        reasons.append(f"命中语句黑名单: {statement_hits}")

    result["reasons"] = reasons
    result["level"] = "high" if reasons else "low"
    return result
