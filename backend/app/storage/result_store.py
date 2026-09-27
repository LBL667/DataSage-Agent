"""结果集落盘与引用。

查询结果进对象存储，不进 state。state 里只放 result_ref 与元信息，
否则 checkpoint 会迅速膨胀。用 CSV 落盘避免引入 pyarrow 依赖。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class ResultStore:
    """结果集对象存储，落盘 CSV 加元信息 JSON。"""

    def __init__(self, result_dir: Path):
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)

    def save(self, df: pd.DataFrame, meta: dict | None = None) -> str:
        """落盘 DataFrame，返回 result_ref。"""
        ref = f"res_{uuid.uuid4().hex[:12]}"
        csv_path = self.result_dir / f"{ref}.csv"
        df.to_csv(csv_path, index=False)

        meta_full = {
            "ref": ref,
            "columns": list(df.columns),
            "row_count": len(df),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        if meta:
            meta_full.update(meta)

        meta_path = self.result_dir / f"{ref}.meta.json"
        meta_path.write_text(json.dumps(meta_full, ensure_ascii=False), encoding="utf-8")
        return ref

    def load(self, ref: str) -> pd.DataFrame:
        """按引用读回数据。"""
        csv_path = self.result_dir / f"{ref}.csv"
        return pd.read_csv(csv_path)

    def load_meta(self, ref: str) -> dict:
        """读回元信息。"""
        meta_path = self.result_dir / f"{ref}.meta.json"
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def exists(self, ref: str) -> bool:
        """判断引用是否存在。"""
        return (self.result_dir / f"{ref}.csv").exists()
