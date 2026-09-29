"""语义缓存。key 为规范化问题加时间窗口加用户权限指纹。

命中直接回放结果引用，省一次全流程。权限指纹必须进 key，否则 A 用户的结果
会被 B 用户命中，这是数据越权。
"""

from __future__ import annotations

import json
import uuid

import aiosqlite

from app.config import DATA_DIR
from app.rag import embedding

CACHE_DB = DATA_DIR / "semantic_cache.sqlite"

# 余弦相似度命中阈值
_HIT_THRESHOLD = 0.9


def _time_key(time_window: tuple | list | None) -> str:
    if not time_window:
        return ""
    return f"{time_window[0]}~{time_window[1]}"


async def lookup(query: str, time_window, user_id: str) -> dict | None:
    """查缓存，命中返回结果，未命中返回 None。"""
    db = CACHE_DB
    if not db.exists():
        return None

    query_emb = (await embedding.embed([query]))[0]
    time_key = _time_key(time_window)

    conn = await aiosqlite.connect(str(db))
    try:
        cur = await conn.execute(
            "SELECT query_embedding, result_ref, analysis_output, chart_spec, result_meta "
            "FROM cache WHERE user_id = ? AND time_window = ?",
            (user_id, time_key),
        )
        rows = await cur.fetchall()
    finally:
        await conn.close()

    best = None
    best_score = 0.0
    for emb_text, result_ref, analysis_text, chart_text, meta_text in rows:
        try:
            emb = json.loads(emb_text)
        except (json.JSONDecodeError, TypeError):
            continue
        score = embedding.cosine(query_emb, emb)
        if score > best_score:
            best_score = score
            best = {
                "result_ref": result_ref,
                "analysis_output": json.loads(analysis_text) if analysis_text else None,
                "chart_spec": json.loads(chart_text) if chart_text else None,
                "result_meta": json.loads(meta_text) if meta_text else None,
            }

    if best is not None and best_score >= _HIT_THRESHOLD:
        return best
    return None


async def store(query: str, time_window, user_id: str, result: dict) -> None:
    """存缓存。result 含 result_ref、analysis_output、chart_spec、result_meta。"""
    db = CACHE_DB
    db.parent.mkdir(parents=True, exist_ok=True)
    query_emb = (await embedding.embed([query]))[0]
    time_key = _time_key(time_window)

    conn = await aiosqlite.connect(str(db))
    try:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "id TEXT PRIMARY KEY, query TEXT, query_embedding TEXT, time_window TEXT, "
            "user_id TEXT, result_ref TEXT, analysis_output TEXT, chart_spec TEXT, "
            "result_meta TEXT, created_at TEXT)"
        )
        await conn.execute(
            "INSERT OR REPLACE INTO cache "
            "(id, query, query_embedding, time_window, user_id, result_ref, analysis_output, chart_spec, result_meta, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                uuid.uuid4().hex,
                query,
                json.dumps(query_emb),
                time_key,
                user_id,
                result.get("result_ref"),
                json.dumps(result.get("analysis_output"), ensure_ascii=False),
                json.dumps(result.get("chart_spec"), ensure_ascii=False),
                json.dumps(result.get("result_meta"), ensure_ascii=False),
            ),
        )
        await conn.commit()
    finally:
        await conn.close()
