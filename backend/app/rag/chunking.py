"""切分。按内容类型定粒度，schema 按表切。"""

from __future__ import annotations


def format_table(table: dict) -> str:
    """把表结构格式化成文本。"""
    header = f"表 {table['name']}"
    extras = []
    if table.get("row_count") is not None:
        extras.append(f"{table['row_count']} 行")
    if table.get("time_range"):
        extras.append(f"时间范围 {table['time_range'][0]} 到 {table['time_range'][1]}")
    if extras:
        header += "（" + "，".join(extras) + "）"
    if table.get("comment"):
        header += f"：{table['comment']}"
    else:
        header += "："

    lines = [header]
    for col in table.get("columns", []):
        comment_text = f"，{col['comment']}" if col.get("comment") else ""
        lines.append(f"- {col['name']}：{col['data_type']}{comment_text}")
    return "\n".join(lines)


def chunk_schema(tables: list[dict]) -> list[dict]:
    """schema 集合按表切，每张表一个 chunk。"""
    chunks = []
    for table in tables:
        content = format_table(table)
        parts = [table["name"], table.get("comment", "")]
        for col in table.get("columns", []):
            parts.append(col["name"])
            parts.append(col.get("comment", ""))
        keyword_text = " ".join(p for p in parts if p)
        chunks.append(
            {
                "collection": "schema",
                "content": content,
                "keyword_text": keyword_text,
                "metadata": {"table": table["name"]},
            }
        )
    return chunks


def chunk_generic(collection: str, items: list[dict]) -> list[dict]:
    """metric 与 method 集合的通用切分，每个条目一个 chunk。"""
    chunks = []
    for item in items:
        content = item.get("content", "")
        keyword_text = item.get("keyword_text", content)
        chunks.append(
            {
                "collection": collection,
                "content": content,
                "keyword_text": keyword_text,
                "metadata": item.get("metadata", {}),
            }
        )
    return chunks
