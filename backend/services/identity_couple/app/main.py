"""用户与情侣身份服务。

该服务直接使用共享 SQLAlchemy ``User``/``Couple`` 模型；未配置数据库依赖时
明确返回 503，而不会退化成进程内状态，以免多副本部署产生分叉数据。
"""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import date, datetime
from time import perf_counter

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.db.models import Couple, User

logger = structlog.get_logger()


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    nick_name: str | None = Field(default=None, alias="nickName", max_length=64)
    avatar_url: str | None = Field(default=None, alias="avatarUrl", max_length=512)

    model_config = {"populate_by_name": True}


class BindRequest(BaseModel):
    couple_code: str = Field(alias="coupleCode", min_length=1, max_length=32)

    model_config = {"populate_by_name": True}


SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def _secret(value: str | None) -> str:
    resolved = value or os.getenv("JWT_SECRET")
    if not resolved:
        raise RuntimeError("JWT_SECRET 未配置")
    if len(resolved) < 64:
        raise ValueError("JWT_SECRET 至少64字符")
    return resolved


def _result(data: object | None = None) -> dict[str, object | None]:
    return {"code": 200, "message": "操作成功", "data": data}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def _session(request: Request) -> AsyncIterator[AsyncSession]:
    provider: SessionProvider | None = getattr(request.app.state, "session_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503, detail={"code": 503, "message": "身份服务未就绪", "data": None}
        )
    async with provider() as session:
        yield session


_SESSION_DEPENDENCY = Depends(_session)


async def _authenticated_session(
    request: Request, authorization: str | None = Header(default=None)
) -> AsyncIterator[AsyncSession]:
    request.state.user_id = _claims_user(authorization, request.app.state.jwt_secret)
    async for session in _session(request):
        yield session


_AUTHENTICATED_SESSION_DEPENDENCY = Depends(_authenticated_session)


def _user_payload(user: User) -> dict[str, object | None]:
    return {
        "id": user.id,
        "openid": user.openid,
        "nickName": user.nick_name,
        "avatarUrl": user.avatar_url,
        "phone": user.phone,
        "gender": user.gender,
        "coupleId": user.couple_id,
        "loveStartDate": user.love_start_date.isoformat() if user.love_start_date else None,
        "memberLevel": user.member_level,
        "status": user.status,
        "coupleInfo": None,
    }


def _claims_user(authorization: str | None, secret: str) -> int:
    from packages.platform.auth import decode_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"code": 401, "message": "请先登录", "data": None}
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, secret=secret)
        return int(payload["userId"])
    except Exception as error:
        raise HTTPException(
            status_code=401, detail={"code": 401, "message": "登录信息无效", "data": None}
        ) from error


def create_app(
    *, jwt_secret: str | None = None, session_provider: SessionProvider | None = None
) -> FastAPI:
    app = FastAPI(title="Identity Couple Service")
    app.state.jwt_secret = _secret(jwt_secret)
    app.state.session_provider = session_provider

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or secrets.token_hex(16)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        detail = (
            error.detail
            if isinstance(error.detail, dict)
            else {
                "code": error.status_code,
                "message": str(error.detail),
                "data": None,
            }
        )
        return JSONResponse(status_code=error.status_code, content=detail)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "identity_couple"}

    @app.post("/api/user/login")
    async def login(
        request: Request, payload: LoginRequest, session: AsyncSession = _SESSION_DEPENDENCY
    ) -> dict[str, object]:
        started = perf_counter()
        result = await session.execute(
            select(User).where(User.openid == payload.code, User.is_deleted == 0).limit(1)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                openid=payload.code,
                nick_name=payload.nick_name or "新用户",
                avatar_url=payload.avatar_url or "",
                member_level=0,
                status=0,
                is_deleted=0,
            )
            session.add(user)
            await session.flush()
        elif payload.nick_name or payload.avatar_url:
            user.nick_name = payload.nick_name or user.nick_name
            user.avatar_url = payload.avatar_url or user.avatar_url
        await session.commit()
        token = create_access_token(user.id, app.state.jwt_secret, 604_800_000)
        await logger.ainfo(
            "identity_operation_completed",
            requestId=_request_id(request),
            module="identity",
            operation="login",
            result="success",
            durationMs=round((perf_counter() - started) * 1000),
            errorCode="NONE",
        )
        return _result({"token": token, "userInfo": _user_payload(user)})

    @app.get("/api/user/profile")
    async def profile(
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id = request.state.user_id
        result = await session.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=404, detail={"code": 1001, "message": "用户不存在", "data": None}
            )
        return _result(
            {"userId": user.id, "coupleId": user.couple_id, "userInfo": _user_payload(user)}
        )

    @app.post("/api/couple/generateCode")
    async def generate(
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id = request.state.user_id
        result = await session.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=404, detail={"code": 1001, "message": "用户不存在", "data": None}
            )
        if user.couple_id is not None:
            raise HTTPException(
                status_code=200,
                detail={"code": 2002, "message": "已经绑定过情侣关系", "data": None},
            )
        existing = await session.execute(
            select(Couple).where(Couple.user1_id == user_id, Couple.status == 0).limit(1)
        )
        couple = existing.scalar_one_or_none()
        if couple is None:
            couple = Couple(
                couple_code=secrets.token_hex(4).upper(),
                user1_id=user_id,
                user2_id=None,
                start_date=date.today(),
                love_days=0,
                status=0,
            )
            session.add(couple)
            await session.flush()
        await session.commit()
        await logger.ainfo(
            "identity_operation_completed",
            requestId=_request_id(request),
            module="identity",
            operation="generate_code",
            result="success",
            durationMs=0,
            errorCode="NONE",
        )
        return _result({"code": couple.couple_code})

    @app.post("/api/couple/bind")
    async def bind(
        request: Request,
        payload: BindRequest,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id = request.state.user_id
        user_result = await session.execute(
            select(User).where(User.id == user_id, User.is_deleted == 0)
        )
        user = user_result.scalar_one_or_none()
        code_result = await session.execute(
            select(Couple)
            .where(Couple.couple_code == payload.couple_code.strip().upper(), Couple.status == 0)
            .limit(1)
        )
        couple = code_result.scalar_one_or_none()
        if (
            user is None
            or couple is None
            or couple.user1_id == user_id
            or user.couple_id is not None
            or couple.user2_id is not None
        ):
            raise HTTPException(
                status_code=400,
                detail={"code": 2003, "message": "情侣码无效或已过期", "data": None},
            )
        couple.user2_id = user_id
        couple.status = 1
        couple.love_days = max(0, (date.today() - (couple.start_date or date.today())).days)
        couple.couple_nickname = f"情侣{couple.user1_id}&{user_id}"
        user.couple_id = couple.id
        user.love_start_date = datetime.combine(
            couple.start_date or date.today(), datetime.min.time()
        )
        owner_result = await session.execute(
            select(User).where(User.id == couple.user1_id, User.is_deleted == 0)
        )
        owner = owner_result.scalar_one_or_none()
        if owner is not None:
            owner.couple_id = couple.id
            owner.love_start_date = user.love_start_date
        await session.commit()
        return _result({"coupleId": couple.id})

    return app


try:
    app = create_app()
except (RuntimeError, ValueError):
    # 本地导入/静态检查没有密钥时保持模块可导入；实际启动应注入 JWT_SECRET。
    app = FastAPI(title="Identity Couple Service")

    @app.get("/health")
    async def health_unconfigured() -> dict[str, str]:
        return {"status": "ok", "service": "identity_couple"}
