"""验证第 11 步。schema 入库与检索质量对照。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.ingest import ingest_schema, load_chunks  # noqa: E402
from app.rag.retrieve import retrieve  # noqa: E402


async def main() -> None:
    # 1. 入库
    count = await ingest_schema(force=True)
    print(f"[入库] schema {count} 个 chunk")
    chunks = await load_chunks("schema")
    for c in chunks:
        print(f"  - {c['metadata']['table']}: {c['content'].splitlines()[0]}")

    # 2. 检索对照
    queries = [
        ("各渠道订单金额总和", "orders"),
        ("订单明细商品数量", "order_items"),
        ("渠道名称列表", "channels"),
    ]
    print("\n[检索对照]")
    for query, expect in queries:
        results = await retrieve(query, "schema", top_k=3)
        recalled = [r["metadata"]["table"] for r in results]
        top = recalled[0] if recalled else "无"
        ok = top == expect
        print(f"  [{'通过' if ok else '未通过'}] '{query}' → {recalled}, 期望 {expect}")

    # 3. 语义同义（订单 → orders）
    results = await retrieve("下单记录金额", "schema", top_k=3)
    print(f"  [语义] '下单记录金额' → {[r['metadata']['table'] for r in results]}")


if __name__ == "__main__":
    asyncio.run(main())
