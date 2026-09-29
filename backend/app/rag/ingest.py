"""入库。从 information_schema 读表结构，切分向量化写入 SQLite。

schema 集合先做，它对 SQL 准确率提升最大。metric 与 method 集合后续由
配置面板或上传接入，当前先留接口。
"""

from __future__ import annotations

import json

import aiomysql

from app.config import DATA_DIR
from app.middleware.credential import resolve_credential
from app.observability.logging import get_logger
from app.rag import chunking, embedding

logger = get_logger("app.rag.ingest")

RAG_DB = DATA_DIR / "rag.sqlite"

_TIME_TYPES = ("date", "datetime", "timestamp")

# 演示表的中文注释 fallback。真实库的 information_schema 有注释时优先用库里的，
# 演示表建表时未加注释，用这里的中文描述兜底，保证中文 query 能召回。
_DEMO_TABLE_COMMENTS: dict[str, dict] = {
    "channels": {
        "comment": "渠道表",
        "columns": {"channel_id": "渠道 id", "channel_name": "渠道名"},
    },
    "orders": {
        "comment": "订单表",
        "columns": {
            "order_id": "订单号",
            "user_id": "用户 id",
            "channel": "渠道",
            "amount": "金额",
            "created_at": "下单时间",
        },
    },
    "order_items": {
        "comment": "订单明细",
        "columns": {
            "item_id": "明细 id",
            "order_id": "所属订单",
            "product_id": "商品 id",
            "quantity": "数量",
            "price": "单价",
        },
    },
}


def _fallback_comment(table: str, column: str | None = None) -> str:
    demo = _DEMO_TABLE_COMMENTS.get(table)
    if not demo:
        return ""
    if column is None:
        return demo.get("comment", "")
    return demo.get("columns", {}).get(column, "")


async def read_tables() -> list[dict]:
    """从 information_schema 读表结构，返回结构化表清单。"""
    cred = resolve_credential("single")
    conn = await aiomysql.connect(
        host=cred.host, port=cred.port, user=cred.user,
        password=cred.password, db=cred.database,
    )
    try:
        cur = await conn.cursor()
        await cur.execute(
            "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
            (cred.database,),
        )
        table_rows = await cur.fetchall()
        table_comments = {t: c for t, c in table_rows}

        await cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT, DATA_TYPE "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (cred.database,),
        )
        col_rows = await cur.fetchall()

        tables: list[dict] = []
        for name, comment in table_rows:
            table_comment = comment or _fallback_comment(name)
            table = {
                "name": name,
                "comment": table_comment,
                "columns": [
                    {
                        "name": c,
                        "comment": cm or _fallback_comment(name, c),
                        "data_type": dt,
                    }
                    for t, c, cm, dt in col_rows if t == name
                ],
                "row_count": None,
                "time_range": None,
            }
            # 行数
            try:
                await cur.execute(f"SELECT COUNT(*) FROM `{name}`")
                table["row_count"] = (await cur.fetchone())[0]
            except Exception:  # noqa: BLE001
                pass
            # 时间列范围
            time_col = next((c["name"] for c in table["columns"] if c["data_type"] in _TIME_TYPES), None)
            if time_col:
                try:
                    await cur.execute(f"SELECT MIN(`{time_col}`), MAX(`{time_col}`) FROM `{name}`")
                    mn, mx = await cur.fetchone()
                    if mn is not None and mx is not None:
                        table["time_range"] = (str(mn), str(mx))
                except Exception:  # noqa: BLE001
                    pass
            tables.append(table)
        await cur.close()
        return tables
    finally:
        conn.close()


async def ingest_schema(force: bool = False) -> int:
    """入库 schema 集合，返回 chunk 数量。"""
    import aiosqlite

    tables = await read_tables()
    chunks = chunking.chunk_schema(tables)
    if not chunks:
        return 0

    embeddings = await embedding.embed([c["keyword_text"] for c in chunks])

    db = RAG_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(db))
    try:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS chunks ("
            "id TEXT PRIMARY KEY, collection TEXT, content TEXT, keyword_text TEXT, "
            "embedding TEXT, metadata TEXT, created_at TEXT)"
        )
        if force:
            await conn.execute("DELETE FROM chunks WHERE collection = 'schema'")
        for chunk, vec in zip(chunks, embeddings):
            await conn.execute(
                "INSERT OR REPLACE INTO chunks (id, collection, content, keyword_text, embedding, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    f"schema::{chunk['metadata']['table']}",
                    chunk["collection"],
                    chunk["content"],
                    chunk["keyword_text"],
                    json.dumps(vec),
                    json.dumps(chunk["metadata"], ensure_ascii=False),
                ),
            )
        await conn.commit()
    finally:
        await conn.close()

    logger.info("schema 入库 %d 个 chunk", len(chunks))
    return len(chunks)


async def load_chunks(collection: str) -> list[dict]:
    """加载集合的所有 chunks，含反序列化的向量与元数据。"""
    import aiosqlite

    db = RAG_DB
    if not db.exists():
        return []

    conn = await aiosqlite.connect(str(db))
    try:
        cur = await conn.execute(
            "SELECT id, content, keyword_text, embedding, metadata FROM chunks WHERE collection = ?",
            (collection,),
        )
        rows = await cur.fetchall()
    finally:
        await conn.close()

    chunks = []
    for cid, content, keyword_text, embedding_text, metadata_text in rows:
        chunks.append(
            {
                "id": cid,
                "content": content,
                "keyword_text": keyword_text,
                "embedding": json.loads(embedding_text) if embedding_text else [],
                "metadata": json.loads(metadata_text) if metadata_text else {},
            }
        )
    return chunks
