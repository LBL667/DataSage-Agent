"""凭据解析。

方案 A，单用户，直接返回环境变量里的配置。这个接口现在看起来多余，
但它是将来改多用户的唯一改动点。凭据明文只在这里出现，调用方不得打印。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.config import Settings, load_settings


@dataclass(frozen=True)
class DbCredential:
    """数据库连接配置。"""

    host: str
    port: int
    user: str
    password: str
    database: str


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return load_settings()


def resolve_credential(user_id: str) -> DbCredential:
    """方案 A 直接返回环境变量配置。将来改多用户只改这一个函数。"""
    s = _cached_settings()
    return DbCredential(
        host=s.db_host,
        port=s.db_port,
        user=s.db_user,
        password=s.db_password,
        database=s.db_name,
    )
