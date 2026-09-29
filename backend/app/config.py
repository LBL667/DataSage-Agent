"""配置加载。

Pydantic 模型读环境变量，yaml 读黑白名单与清洗规则。启动时校验必填项。
凭据明文只在这里读取，不进日志、不进 state、不进异常堆栈。
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from app.errors import ConfigError

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"


class Settings(BaseModel):
    """应用配置，从环境变量读取。"""

    # 数据库，只读账号
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "agent_ro"
    db_password: str = ""
    db_name: str = ""

    # 模型
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"

    # 结果存储与 checkpoint
    result_dir: Path = DATA_DIR / "results"
    upload_dir: Path = DATA_DIR / "uploads"
    checkpoint_db: Path = DATA_DIR / "checkpoint.sqlite"

    # 审批阈值
    max_scan_rows: int = 100_000
    sql_timeout_s: float = 10.0
    grant_ttl_s: int = 1800


def load_settings() -> Settings:
    """读取 .env 并构建 Settings，必填项缺失时报错。"""
    load_dotenv(BASE_DIR / ".env")
    env = os.environ

    settings = Settings(
        db_host=env.get("DB_HOST", "127.0.0.1"),
        db_port=int(env.get("DB_PORT", "3306")),
        db_user=env.get("DB_USER", "agent_ro"),
        db_password=env.get("DB_PASSWORD", ""),
        db_name=env.get("DB_NAME", ""),
        llm_api_key=env.get("LLM_API_KEY", ""),
        llm_base_url=env.get("LLM_BASE_URL", ""),
        llm_model=env.get("LLM_MODEL", "gpt-4o-mini"),
        max_scan_rows=int(env.get("MAX_SCAN_ROWS", "100000")),
        sql_timeout_s=float(env.get("SQL_TIMEOUT_S", "10.0")),
        grant_ttl_s=int(env.get("GRANT_TTL_S", "1800")),
    )

    if not settings.db_password:
        raise ConfigError("缺少 DB_PASSWORD，请复制 .env.example 为 .env 并填写")
    if not settings.db_name:
        raise ConfigError("缺少 DB_NAME，请复制 .env.example 为 .env 并填写")

    return settings


def load_yaml(name: str) -> dict:
    """读取 config 目录下的 yaml 配置，文件缺失时返回空结构。"""
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_whitelist() -> list[str]:
    """读取可访问表白名单。"""
    data = load_yaml("whitelist.yaml")
    return list(data.get("tables", []))


def load_blacklist() -> dict:
    """读取敏感字段与语句黑名单。"""
    data = load_yaml("blacklist.yaml")
    return {
        "columns": list(data.get("columns", [])),
        "column_patterns": list(data.get("column_patterns", [])),
        "statements": list(data.get("statements", [])),
    }


def load_clean_rules() -> list[dict]:
    """读取清洗规则。"""
    data = load_yaml("clean_rules.yaml")
    return list(data.get("rules", []))


def save_yaml(name: str, data: dict) -> None:
    """写回 config 目录下的 yaml 配置。"""
    path = CONFIG_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def save_env(updates: dict[str, str]) -> None:
    """更新 .env 指定键，保留其他行。值为 None 的键跳过。"""
    env_path = BASE_DIR / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        key = ""
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
        if key in updates and updates[key] is not None:
            out.append(f"{key}={updates[key]}")
            updated.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in updated and value is not None:
            out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
