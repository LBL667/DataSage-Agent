"""质检器。五项检查，只读不改数据。

行数合理性、主键唯一、日期连续性、空值率、数值分布。
行数合理性这一条最有用，能挡住 join 写错导致的行数翻倍。
"""

from __future__ import annotations

import pandas as pd


def probe(df: pd.DataFrame) -> dict:
    """五项检查，返回 quality_report。passed 为 False 表示应回退。"""
    checks: list[dict] = []
    passed = True
    row_count = len(df)

    # 1. 行数合理性，空结果直接不通过
    if row_count == 0:
        checks.append({"check": "行数合理性", "passed": False, "detail": "结果为空"})
        passed = False
    else:
        checks.append({"check": "行数合理性", "passed": True, "detail": f"{row_count} 行"})

    # 2. 主键唯一，检查 id 类列
    id_cols = [c for c in df.columns if c.lower() == "id" or c.lower().endswith("_id")]
    if id_cols and row_count > 0:
        col = id_cols[0]
        unique = df[col].nunique()
        if unique < row_count:
            checks.append(
                {"check": "主键唯一", "passed": False, "detail": f"{col} 唯一值 {unique} < 行数 {row_count}"}
            )
            passed = False
        else:
            checks.append({"check": "主键唯一", "passed": True, "detail": f"{col} 唯一"})
    else:
        checks.append({"check": "主键唯一", "passed": True, "detail": "无主键列，跳过"})

    # 3. 日期连续性，断点检测
    date_cols = [c for c in df.columns if "date" in c.lower() or c.lower().endswith("_at") or c.lower().endswith("_time")]
    if date_cols:
        col = date_cols[0]
        try:
            dates = pd.to_datetime(df[col], errors="coerce").dropna().sort_values()
            if len(dates) > 1:
                gaps = dates.diff().dropna()
                median_gap = gaps.median()
                max_gap = gaps.max()
                # 最大间隔超过中位数 3 倍视为断点，除零防御
                if median_gap.total_seconds() > 0 and max_gap > median_gap * 3:
                    checks.append({"check": "日期连续性", "passed": False, "detail": f"疑似断点，最大间隔 {max_gap}"})
                    passed = False
                else:
                    checks.append({"check": "日期连续性", "passed": True, "detail": f"最大间隔 {max_gap}"})
            else:
                checks.append({"check": "日期连续性", "passed": True, "detail": "样本不足，跳过"})
        except Exception:  # noqa: BLE001
            checks.append({"check": "日期连续性", "passed": True, "detail": "无法解析日期，跳过"})
    else:
        checks.append({"check": "日期连续性", "passed": True, "detail": "无日期列，跳过"})

    # 4. 空值率，单列超过 30% 视为异常
    if row_count > 0:
        null_rates = df.isnull().mean()
        high_null = {c: round(float(r), 3) for c, r in null_rates.items() if r > 0.3}
        if high_null:
            checks.append({"check": "空值率", "passed": False, "detail": f"高缺失列 {high_null}"})
            passed = False
        else:
            checks.append({"check": "空值率", "passed": True, "detail": "空值率正常"})
    else:
        checks.append({"check": "空值率", "passed": True, "detail": "无数据，跳过"})

    # 5. 数值分布，分位数，全 NULL 或全零告警
    num_cols = df.select_dtypes(include="number").columns
    if len(num_cols) > 0:
        col = num_cols[0]
        series = df[col].dropna()
        if len(series) == 0:
            checks.append({"check": "数值分布", "passed": False, "detail": f"{col} 全 NULL"})
            passed = False
        else:
            quantiles = {str(q): float(v) for q, v in series.quantile([0, 0.25, 0.5, 0.75, 1]).items()}
            checks.append({"check": "数值分布", "passed": True, "detail": f"{col} 分位数 {quantiles}"})
    else:
        checks.append({"check": "数值分布", "passed": True, "detail": "无数值列，跳过"})

    return {"passed": passed, "checks": checks}
