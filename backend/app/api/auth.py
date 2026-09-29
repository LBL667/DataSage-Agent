"""用户认证端点。登录、忘记密码、用户信息。

按用户要求从简，无验证码与安全防护。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str = ""


class ResetRequest(BaseModel):
    username: str
    new_password: str


@router.post("/register")
async def register(req: RegisterRequest, request: Request) -> dict:
    store = request.app.state.user_store
    user = await store.create_user(req.username, req.password, req.nickname)
    if user is None:
        return {"ok": False, "message": "用户名已存在"}
    return {"ok": True, "user": user}


@router.post("/login")
async def login(req: LoginRequest, request: Request) -> dict:
    store = request.app.state.user_store
    user = await store.authenticate(req.username, req.password)
    if user is None:
        return {"ok": False, "message": "用户名或密码错误"}
    return {"ok": True, "user": user}


@router.post("/reset-password")
async def reset_password(req: ResetRequest, request: Request) -> dict:
    store = request.app.state.user_store
    ok = await store.reset_password(req.username, req.new_password)
    if not ok:
        return {"ok": False, "message": "用户不存在"}
    return {"ok": True}


@router.get("/me")
async def me(username: str, request: Request) -> dict:
    store = request.app.state.user_store
    user = await store.get_user(username)
    if user is None:
        return {"ok": False, "message": "用户不存在"}
    return {"ok": True, "user": user}
