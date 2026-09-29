"""清洗规则引擎。

读 clean_rules.yaml，执行规则，产出 clean_log。模型只能从配置里已登记的规则里选，
不能发明规则。这是分析结论可信度的前提。
"""

from __future__ import annotations

import pandas as pd

from app.clean import actions
from app.config import load_clean_rules


def apply_rules(df: pd.DataFrame, rules: list[dict] | None = None) -> tuple[pd.DataFrame, list[dict], list[str]]:
    """按规则清洗 DataFrame，返回 (新 df, clean_log, applied_rule_ids)。

    规则失败时保留原始数据并记录告警。
    """
    if rules is None:
        rules = load_clean_rules()

    log: list[dict] = []
    applied: list[str] = []
    result = df
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        action = rule.get("action")
        fn = actions.ACTIONS.get(action)
        if fn is None:
            continue

        before_rows = len(result)
        try:
            result = fn(result, rule)
        except Exception as e:  # noqa: BLE001
            log.append(
                {
                    "rule_id": rule.get("id"),
                    "action": action,
                    "status": "failed",
                    "error": type(e).__name__,
                }
            )
            continue

        entry = {
            "rule_id": rule.get("id"),
            "action": action,
            "target": rule.get("target", []),
            "before_rows": before_rows,
            "after_rows": len(result),
            "affected_rows": before_rows - len(result),
            "status": "ok",
        }
        log.append(entry)
        applied.append(rule.get("id"))

    return result, log, applied
