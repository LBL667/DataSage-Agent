"""表级授权 TTL。

同一会话重复查询同一张表不再打断。这是把打断次数从每轮三次降到接近零的关键。
内存存储，进程重启后丢失，单用户本机足够。
"""

from __future__ import annotations

import time


class GrantStore:
    """表级授权缓存，(session_id, table) 到过期时间戳。"""

    def __init__(self):
        self._grants: dict[tuple[str, str], float] = {}

    def grant(self, session_id: str, tables: list[str], ttl_s: int = 1800) -> None:
        now = time.time()
        for t in tables:
            self._grants[(session_id, t)] = now + ttl_s

    def is_granted(self, session_id: str, tables: list[str]) -> bool:
        """所有表都在授权期内才返回 True。"""
        if not tables:
            return False
        now = time.time()
        for t in tables:
            expires = self._grants.get((session_id, t))
            if expires is None or expires < now:
                return False
        return True

    def clear_session(self, session_id: str) -> None:
        keys = [k for k in self._grants if k[0] == session_id]
        for k in keys:
            del self._grants[k]


_grant_store = GrantStore()


def grant(session_id: str, tables: list[str], ttl_s: int = 1800) -> None:
    _grant_store.grant(session_id, tables, ttl_s)


def is_granted(session_id: str, tables: list[str]) -> bool:
    return _grant_store.is_granted(session_id, tables)
