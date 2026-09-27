"""只读执行工具。

只读连接、只读事务、执行超时、分片读取、行数上限，finally 里强制 rollback。
这一层与只读账号共同构成真正的安全边界，前面的静态校验都只是效率优化。
"""

from __future__ import annotations

import asyncio

import aiomysql
import pandas as pd

from app.config import DATA_DIR
from app.errors import BusinessError
from app.middleware.credential import resolve_credential
from app.observability.logging import get_logger
from app.storage.result_store import ResultStore

logger = get_logger("app.tools.mysql_tool")

_pool: aiomysql.Pool | None = None
_store = ResultStore(DATA_DIR / "results")


async def _get_pool() -> aiomysql.Pool:
    """懒加载全局连接池，限制最大连接数防止并发打爆数据库。"""
    global _pool
    if _pool is None or getattr(_pool, "closed", False):
        cred = resolve_credential("single")
        _pool = await aiomysql.create_pool(
            host=cred.host,
            port=cred.port,
            user=cred.user,
            password=cred.password,
            db=cred.database,
            autocommit=False,
            minsize=1,
            maxsize=5,
        )
    return _pool


async def execute_query(
    sql: str,
    max_rows: int = 100_000,
    timeout_s: float = 10.0,
) -> tuple[str, dict]:
    """执行只读查询，落盘结果，返回 (result_ref, meta)。

    meta 含列名与行数。UPDATE 等写操作会被只读账号或只读事务拒绝，
    不会被这里的前置检查拦住。
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        try:
            # 只读事务，在开启事务前设置
            await conn.query("SET SESSION TRANSACTION READ ONLY")

            rows: list[tuple] = []
            columns: list[str] = []
            # 服务端游标分片读取，不 fetchall
            async with conn.cursor(aiomysql.SSCursor) as cur:
                async with asyncio.timeout(timeout_s):
                    await cur.execute(sql)
                    columns = [d[0] for d in cur.description] if cur.description else []
                    while True:
                        batch = await cur.fetchmany(1000)
                        if not batch:
                            break
                        rows.extend(batch)
                        if len(rows) > max_rows:
                            raise BusinessError(f"结果行数超过上限 {max_rows}")
        finally:
            # 强制 rollback，连接不带未结束事务回池
            await conn.rollback()

    df = pd.DataFrame(rows, columns=columns)
    ref = _store.save(df)
    meta = {"columns": columns, "row_count": len(df)}
    logger.info("query done, rows=%d", len(df))
    return ref, meta


async def close_pool() -> None:
    """关闭连接池，供应用停机时调用。"""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
