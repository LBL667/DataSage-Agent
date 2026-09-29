"""用户存储。SQLite，简单用户管理。

按用户要求从简，无验证码与重安全防护，密码做 sha256 摘要即可。
"""

from __future__ import annotations

import hashlib

import aiosqlite

from app.config import DATA_DIR

USER_DB = DATA_DIR / "users.sqlite"


def hash_password(password: str) -> str:
    """密码摘要。"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class UserStore:
    """用户存储，登录、重置密码、查用户。"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._conn = await aiosqlite.connect(str(self.db_path))
        await self._conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL, "
            "nickname TEXT DEFAULT '', "
            "avatar TEXT DEFAULT '', "
            "email TEXT DEFAULT '')"
        )
        # 种子用户 admin
        cur = await self._conn.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if (await cur.fetchone())[0] == 0:
            await self._conn.execute(
                "INSERT INTO users (username, password_hash, nickname, avatar, email) VALUES (?, ?, ?, ?, ?)",
                ("admin", hash_password("admin123"), "管理员", "", "admin@datasage.local"),
            )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def authenticate(self, username: str, password: str) -> dict | None:
        """校验用户名密码，成功返回用户信息。"""
        cur = await self._conn.execute(
            "SELECT id, username, nickname, avatar, email FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password)),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "nickname": row[2],
            "avatar": row[3],
            "email": row[4],
        }

    async def reset_password(self, username: str, new_password: str) -> bool:
        """重置密码，用户名存在则更新并返回 True。"""
        cur = await self._conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        if (await cur.fetchone()) is None:
            return False
        await self._conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username),
        )
        await self._conn.commit()
        return True

    async def get_user(self, username: str) -> dict | None:
        cur = await self._conn.execute(
            "SELECT id, username, nickname, avatar, email FROM users WHERE username = ?",
            (username,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "nickname": row[2],
            "avatar": row[3],
            "email": row[4],
        }

    async def create_user(self, username: str, password: str, nickname: str = "") -> dict | None:
        """注册用户，用户名已存在返回 None。"""
        try:
            await self._conn.execute(
                "INSERT INTO users (username, password_hash, nickname, avatar, email) VALUES (?, ?, ?, '', '')",
                (username, hash_password(password), nickname or username),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError:
            return None
        return await self.get_user(username)
