"""配置面板接口。真读写 .env 与 yaml 配置。

数据库凭据只在此读写 .env，GET 不返回密码。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import (
    load_blacklist,
    load_clean_rules,
    load_settings,
    load_whitelist,
    save_env,
    save_yaml,
)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/db")
async def db_status() -> dict:
    s = load_settings()
    return {"host": s.db_host, "port": s.db_port, "user": s.db_user, "database": s.db_name}


@router.put("/db")
async def put_db(payload: dict) -> dict:
    save_env(
        {
            "DB_HOST": payload.get("host"),
            "DB_PORT": str(payload["port"]) if payload.get("port") else None,
            "DB_USER": payload.get("user"),
            "DB_PASSWORD": payload.get("password") or None,
            "DB_NAME": payload.get("database"),
        }
    )
    return {"ok": True}


@router.get("/whitelist")
async def get_whitelist() -> dict:
    return {"tables": load_whitelist()}


@router.put("/whitelist")
async def put_whitelist(payload: dict) -> dict:
    tables = list(payload.get("tables", []))
    save_yaml("whitelist.yaml", {"tables": tables})
    return {"tables": tables}


@router.get("/blacklist")
async def get_blacklist() -> dict:
    return load_blacklist()


@router.put("/blacklist")
async def put_blacklist(payload: dict) -> dict:
    data = {
        "columns": list(payload.get("columns", [])),
        "column_patterns": list(payload.get("column_patterns", [])),
        "statements": list(payload.get("statements", [])),
    }
    save_yaml("blacklist.yaml", data)
    return data


@router.get("/clean-rules")
async def get_clean_rules() -> dict:
    return {"rules": load_clean_rules()}


@router.put("/clean-rules")
async def put_clean_rules(payload: dict) -> dict:
    rules = list(payload.get("rules", []))
    save_yaml("clean_rules.yaml", {"rules": rules})
    return {"rules": rules}


@router.get("/thresholds")
async def get_thresholds() -> dict:
    s = load_settings()
    return {"max_scan_rows": s.max_scan_rows, "sql_timeout_s": s.sql_timeout_s, "grant_ttl_s": s.grant_ttl_s}


@router.put("/thresholds")
async def put_thresholds(payload: dict) -> dict:
    save_env(
        {
            "MAX_SCAN_ROWS": str(payload["max_scan_rows"]) if payload.get("max_scan_rows") else None,
            "SQL_TIMEOUT_S": str(payload["sql_timeout_s"]) if payload.get("sql_timeout_s") else None,
            "GRANT_TTL_S": str(payload["grant_ttl_s"]) if payload.get("grant_ttl_s") else None,
        }
    )
    return payload
