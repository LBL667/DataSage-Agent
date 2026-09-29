"""从 information_schema 读真实表结构，产出表结构文本。

替代硬编码 DEMO_SCHEMA，让 SQL 生成针对真实表。附带每表行数与时间列范围，
避免模型对数据时间边界产生幻觉。结果缓存，表结构不常变。
"""

from __future__ import annotations

import aiomysql

from app.middleware.credential import resolve_credential
from app.observability.logging import get_logger

logger = get_logger("app.tools.schema_introspect")

_cache: str | None = None

_TIME_TYPES = ("date", "datetime", "timestamp")


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
    except Exception as e:  # noqa: BLE001
        logger.warning("schema 内省连接失败: %s", type(e).__name__)
        return ""

    rows = []
    tables = []
    table_stats: dict[str, dict] = {}
    try:
        cur = await conn.cursor()
        await cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT, DATA_TYPE "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (cred.database,),
        )
        rows = await cur.fetchall()
        tables = sorted({r[0] for r in rows})

        # 每表行数与时间列范围
        for table in tables:
            stats: dict = {}
            try:
                await cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                stats["row_count"] = (await cur.fetchone())[0]
            except Exception:  # noqa: BLE001
                pass

            time_col = next(
                (c for t, c, _, dt in rows if t == table and dt in _TIME_TYPES), None
            )
            if time_col:
                try:
                    await cur.execute(f"SELECT MIN(`{time_col}`), MAX(`{time_col}`) FROM `{table}`")
                    mn, mx = await cur.fetchone()
                    if mn is not None and mx is not None:
                        stats["time_range"] = (str(mn), str(mx))
                except Exception:  # noqa: BLE001
                    pass
            table_stats[table] = stats

        await cur.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("schema 内省失败: %s", type(e).__name__)
        return ""
    finally:
        conn.close()

    lines: list[str] = []
    current_table: str | None = None
    for table, column, comment, data_type in rows:
        if table != current_table:
            current_table = table
            header = f"表 {table}"
            extras = []
            stats = table_stats.get(table, {})
            if "row_count" in stats:
                extras.append(f"{stats['row_count']} 行")
            if "time_range" in stats:
                extras.append(f"时间范围 {stats['time_range'][0]} 到 {stats['time_range'][1]}")
            if extras:
                header += "（" + "，".join(extras) + "）"
            lines.append(header + "：")
        comment_text = f"，{comment}" if comment else ""
        lines.append(f"- {column}：{data_type}{comment_text}")

    _cache = "\n".join(lines)
    return _cache
