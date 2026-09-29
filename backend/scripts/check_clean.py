"""验证第 8 步。质检发现 join 翻倍，清洗有完整日志，五个算子跑通。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from app.clean.rules import apply_rules  # noqa: E402
from app.operators.registry import OPERATORS, PARAM_SCHEMAS  # noqa: E402
from app.quality.probe import probe  # noqa: E402


def make_join_doubled() -> pd.DataFrame:
    """人为造一个 join 写错导致行数翻倍的数据，order_id 重复。"""
    return pd.DataFrame(
        {
            "order_id": [1, 2, 1, 2, 3, 3],
            "amount": [100, 200, 100, 200, 300, 300],
            "created_at": ["2026-09-01", "2026-09-02", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-03"],
            "channel": ["华东", "华南", "华东", "华南", "华北", "华北"],
        }
    )


def main() -> None:
    # 1. 质检发现 join 翻倍
    df = make_join_doubled()
    report = probe(df)
    print(f"[质检] join 翻倍数据 passed={report['passed']}")
    for check in report["checks"]:
        print(f"  - {check['check']}: {check['passed']}, {check['detail']}")
    pk = [c for c in report["checks"] if c["check"] == "主键唯一"]
    print("[通过] 质检发现主键重复" if pk and not pk[0]["passed"] else "[未通过] 质检未发现主键重复")

    # 2. 清洗完整日志
    df2 = pd.DataFrame(
        {
            "order_id": [1, 2, 2, 3],
            "amount": [100, 200, 200, 300],
            "created_at": ["2026-09-01", "2026-09-02", "2026-09-02", "2026-09-03"],
        }
    )
    cleaned, log, applied = apply_rules(df2)
    print(f"\n[清洗] applied={applied}, log 条数={len(log)}")
    for entry in log:
        print(f"  - {entry}")

    # 3. 五个算子跑通
    data = pd.DataFrame(
        {
            "channel": ["华东", "华南", "华北", "华东", "华南"],
            "amount": [100, 200, 300, 150, 250],
            "created_at": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-07-01", "2026-07-02", "2026-08-01"]),
            "quantity": [1, 2, 3, 2, 1],
        }
    )
    print("\n[算子验证]")
    cases = [
        ("period_compare", {"metric": "amount", "period": "mom", "time_column": "created_at", "group_by": ["channel"]}),
        ("top_n", {"metric": "amount", "n": 2}),
        ("attribution", {"metric": "amount", "group_by": ["channel"]}),
        ("distribution", {"metric": "amount", "bins": 3}),
        ("correlation", {"x": "amount", "y": "quantity"}),
    ]
    for action, params_dict in cases:
        fn = OPERATORS[action]
        params = PARAM_SCHEMAS[action](**params_dict)
        result = fn(data, params)
        ok = result.get("data") is not None
        print(f"  [{'通过' if ok else '未通过'}] {action}: {result.get('note')}")


if __name__ == "__main__":
    main()
