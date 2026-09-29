"""向量化。ollama 的 qwen3-embedding 优先，不可用时 fallback 关键词哈希向量。

关键词哈希向量不具真实语义，但能捕捉字符 n-gram 重叠，对 schema 字段名与
中文注释的匹配足够。ollama 修复后自动切回真实 embedding，无需改调用方。
"""

from __future__ import annotations

import hashlib
import math

import httpx

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
OLLAMA_EMBED_MODEL = "qwen3-embedding:0.6b"

_KEYWORD_DIM = 256


async def embed(texts: list[str]) -> list[list[float]]:
    """向量化，ollama 优先，失败回退关键词哈希。"""
    if not texts:
        return []
    try:
        return await _ollama_embed(texts)
    except Exception:  # noqa: BLE001
        return _keyword_embed(texts)


async def _ollama_embed(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise ValueError("ollama embedding 返回数量不匹配")
        return embeddings


def _keyword_embed(texts: list[str], dim: int = _KEYWORD_DIM) -> list[list[float]]:
    result: list[list[float]] = []
    for text in texts:
        vec = [0.0] * dim
        lowered = text.lower()
        for i in range(len(lowered) - 1):
            gram = lowered[i : i + 2]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        result.append(vec)
    return result


def cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度，维度不一致时按较小维度对齐。"""
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
