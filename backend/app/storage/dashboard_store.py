"""仪表盘结果存储。分析结果落盘，供仪表盘读取。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DashboardStore:
    """仪表盘分析结果，一个结果一个 JSON 文件。"""

    def __init__(self, store_dir: Path):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save(self, result: dict) -> str:
        rid = f"r_{uuid.uuid4().hex[:12]}"
        result["result_id"] = rid
        result["created_at"] = datetime.now(timezone.utc).isoformat()
        path = self.store_dir / f"{rid}.json"
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return rid

    def list(self) -> list[dict]:
        results = []
        for f in self.store_dir.glob("*.json"):
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    def get(self, rid: str) -> dict | None:
        path = self.store_dir / f"{rid}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
