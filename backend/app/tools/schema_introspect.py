"""从 information_schema 读真实表结构，产出表结构文本。

替代硬编码 DEMO_SCHEMA，让 SQL 生成针对真实表。结果缓存，表结构不常变。
"""

from __future__ import annotations

import aiomysql

from app.middleware.credential import resolve_credential
from app.observability.logging import get_logger

logger = get_logger("app.tools.schema_introspect")

_cache: str | None = None


async def introspect_schema(force: bool = False) -> str:
    """读真实表结构，返回格式化文本。失败返回空串。"""
    global _cache
    if _cache is not None and not force:
        return _cache

    cred = resolve_credential("single")
    try:
        conn = await aiomysql.connect(
            host=cred.host, port=cred.port, user=cred.user,
            password=cred.password, db=cred.database,
        )
        try:
            cur = await conn.cursor()
            await cur.execute(
                "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT, DATA_TYPE "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION",
                (cred.database,),
            )
            rows = await cur.fetchall()
            await cur.close()
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("schema 内省失败: %s", type(e).__name__)
        return ""

    lines: list[str] = []
    current_table: str | None = None
    for table, column, comment, data_type in rows:
        if table != current_table:
            current_table = table
            lines.append(f"表 {table}：")
        comment_text = f"，{comment}" if comment else ""
        lines.append(f"- {column}：{data_type}{comment_text}")

    _cache = "\n".join(lines)
    return _cache
