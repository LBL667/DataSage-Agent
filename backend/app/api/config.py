"""配置面板接口。读取静态 yaml 配置，凭据只读 .env 不在此暴露。"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import load_blacklist, load_clean_rules, load_whitelist

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/db")
async def db_status() -> dict:
    # 方案 A 下不返回密码，只返回连接状态与目标库名
    return {"status": "unknown", "host": "127.0.0.1", "database": "", "user": "agent_ro"}


@router.post("/db/test")
async def db_test() -> dict:
    return {"ok": False, "message": "第 2 步实现真实连接测试"}


@router.get("/whitelist")
async def get_whitelist() -> dict:
    return {"tables": load_whitelist()}


@router.put("/whitelist")
async def put_whitelist(payload: dict) -> dict:
    # 第 7 步实现写回 yaml
    return {"tables": payload.get("tables", [])}


@router.get("/blacklist")
async def get_blacklist() -> dict:
    return load_blacklist()


@router.put("/blacklist")
async def put_blacklist(payload: dict) -> dict:
    return payload


@router.get("/clean-rules")
async def get_clean_rules() -> dict:
    return {"rules": load_clean_rules()}


@router.post("/clean-rules")
async def create_clean_rule(payload: dict) -> dict:
    return {"rule_id": "R_new", **payload}


@router.put("/clean-rules/{rule_id}")
async def update_clean_rule(rule_id: str, payload: dict) -> dict:
    return {"rule_id": rule_id, **payload}


@router.delete("/clean-rules/{rule_id}")
async def delete_clean_rule(rule_id: str) -> dict:
    return {"ok": True}


@router.get("/thresholds")
async def get_thresholds() -> dict:
    return {"max_scan_rows": 100000, "sql_timeout_s": 10, "grant_ttl_s": 1800}


@router.put("/thresholds")
async def put_thresholds(payload: dict) -> dict:
    return payload
