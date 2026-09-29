"""三个集合定义。schema、metric、method，不把业务文档和 schema 混进一个库。"""

from __future__ import annotations

COLLECTIONS = {
    "schema": {
        "description": "表结构、字段注释、外键关系",
        "consumer": "sql_generate",
        "top_k": 20,
        "require_rerank": False,
    },
    "metric": {
        "description": "指标口径、计算规则、数据血缘",
        "consumer": "intent_router, sql_generate",
        "top_k": 5,
        "require_rerank": True,
    },
    "method": {
        "description": "分析方法、归因套路、漏斗模板",
        "consumer": "analyze",
        "top_k": 3,
        "require_rerank": False,
    },
}
