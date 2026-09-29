"""检索。关键词全文与向量混合召回，RRF 融合，截断。

schema 集合字段名是精确匹配场景，关键词召回权重不低。向量管语义同义。
先多召回再截断，候选少时直接全部返回。
"""

from __future__ import annotations

from app.rag import embedding, ingest

# 第一段召回上限与 RRF 融合参数
_RECALL_LIMIT = 40
_RRF_K = 60


def _grams(text: str) -> set[str]:
    lowered = text.lower()
    return {lowered[i : i + 2] for i in range(len(lowered) - 1)}


def _keyword_score(query: str, keyword_text: str) -> float:
    """关键词打分，query 的字符 n-gram 在关键词文本的覆盖率。"""
    q_grams = _grams(query)
    if not q_grams:
        return 0.0
    k_text = keyword_text.lower()
    matched = sum(1 for g in q_grams if g in k_text)
    return matched / len(q_grams)


def _rank(scores: dict[str, float]) -> dict[str, int]:
    """按分数降序排名，返回 id 到名次。"""
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {cid: i + 1 for i, (cid, _) in enumerate(ordered)}


def _rrf(scores_a: dict[str, float], scores_b: dict[str, float], k: int = _RRF_K) -> dict[str, float]:
    """倒数排名融合，规避两种打分量纲不一致。"""
    rank_a = _rank(scores_a)
    rank_b = _rank(scores_b)
    fused: dict[str, float] = {}
    for cid in set(rank_a) | set(rank_b):
        fused[cid] = 1.0 / (k + rank_a.get(cid, len(rank_a) + 1)) + 1.0 / (k + rank_b.get(cid, len(rank_b) + 1))
    return fused


async def retrieve(query: str, collection: str, top_k: int | None = None) -> list[dict]:
    """检索集合，返回 top_k 个 chunk 的 content 与 metadata。"""
    chunks = await ingest.load_chunks(collection)
    if not chunks:
        return []

    if top_k is None:
        from app.rag.collections import COLLECTIONS

        top_k = COLLECTIONS.get(collection, {}).get("top_k", 5)

    # 第一段并行召回
    kw_scores = {c["id"]: _keyword_score(query, c["keyword_text"]) for c in chunks}
    query_emb = (await embedding.embed([query]))[0]
    vec_scores = {c["id"]: embedding.cosine(query_emb, c["embedding"]) for c in chunks if c["embedding"]}

    # 第二段 RRF 融合
    fused = _rrf(kw_scores, vec_scores)

    # 先多召回再截断
    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:_RECALL_LIMIT]
    by_id = {c["id"]: c for c in chunks}
    results = [
        {"content": by_id[cid]["content"], "metadata": by_id[cid]["metadata"], "score": round(score, 6)}
        for cid, score in ordered[:top_k]
    ]
    return results


async def rag_search(query: str, collection: str, top_k: int = 5) -> list[dict]:
    """MCP 形态入口，供工具层调用。"""
    return await retrieve(query, collection, top_k)
