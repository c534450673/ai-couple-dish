import re
import secrets
from datetime import UTC, datetime
from time import perf_counter

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims, create_access_token
from app.core.config import Settings
from app.core.errors import BusinessError
from app.db.models import User
from app.redis.keys import logout_blacklist_key, verify_code_key
from app.schemas.business import PhoneLoginRequest, UpdateUserRequest, WechatLoginRequest

logger = structlog.get_logger()
PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
VERIFY_CODE_TTL_SECONDS = 300
VERIFY_RATE_LIMIT_SECONDS = 60


def _operation_log_fields(
    request_id: str, operation: str, result: str, duration_ms: int, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request_id,
        "module": "user",
        "operation": operation,
        "result": result,
        "durationMs": duration_ms,
        "errorCode": error_code,
    }


async def _find_user(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    openid: str | None = None,
    phone: str | None = None,
) -> User | None:
    conditions = [User.is_deleted == 0]
    if user_id is not None:
        conditions.append(User.id == user_id)
    if openid is not None:
        conditions.append(User.openid == openid)
    if phone is not None:
        conditions.append(User.phone == phone)
    result = await session.execute(select(User).where(*conditions).limit(1))
    return result.scalar_one_or_none()


def _user_payload(user: User) -> dict[str, object | None]:
    love_start_date = user.love_start_date.isoformat() if user.love_start_date else None
    return {
        "id": user.id,
        "openid": user.openid,
        "nickName": user.nick_name,
        "avatarUrl": user.avatar_url,
        "phone": user.phone,
        "gender": user.gender,
        "coupleId": user.couple_id,
        "loveStartDate": love_start_date,
        "memberLevel": user.member_level,
        "status": user.status,
        "coupleInfo": None,
    }


def _login_payload(user: User, settings: Settings) -> dict[str, object]:
    return {
        "token": create_access_token(
            user.id,
            settings.jwt_secret.get_secret_value(),
            settings.jwt_expiration,
        ),
        "userInfo": _user_payload(user),
    }


async def _commit_new_user(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.flush()
    await session.commit()
    await session.refresh(user)
    return user


async def wechat_login(
    request: Request, session: AsyncSession, payload: WechatLoginRequest
) -> dict[str, object]:
    started = perf_counter()
    try:
        user = await _find_user(session, openid=payload.code)
        if user is None:
            user = await _commit_new_user(
                session,
                User(
                    openid=payload.code,
                    nick_name=payload.nick_name or f"用户{secrets.randbelow(10000):04d}",
                    avatar_url=payload.avatar_url or "",
                    member_level=0,
                    status=0,
                    is_deleted=0,
                ),
            )
        else:
            changed = False
            if payload.nick_name and payload.nick_name != user.nick_name:
                user.nick_name = payload.nick_name
                changed = True
            if payload.avatar_url and payload.avatar_url != user.avatar_url:
                user.avatar_url = payload.avatar_url
                changed = True
            if changed:
                await session.commit()
        await logger.ainfo(
            "business_operation_completed",
            **_operation_log_fields(
                request.state.request_id,
                "wechat_login",
                "success",
                round((perf_counter() - started) * 1000),
            ),
        )
        return _login_payload(user, request.app.state.settings)
    except BusinessError:
        raise
    except Exception:
        await session.rollback()
        await logger.aerror(
            "business_operation_failed",
            **_operation_log_fields(
                request.state.request_id,
                "wechat_login",
                "error",
                round((perf_counter() - started) * 1000),
                "USER_LOGIN_FAILED",
            ),
        )
        raise


def _validate_phone(phone: str) -> None:
    if not PHONE_PATTERN.fullmatch(phone):
        raise BusinessError(1004, "手机号格式不正确")


async def _verify_code(request: Request, phone: str, code: str | None) -> None:
    if not code:
        raise BusinessError(9003, "验证码不能为空")
    stored = await request.app.state.redis.raw.get(verify_code_key(phone))
    if stored is None:
        raise BusinessError(9004, "验证码已过期，请重新获取")
    if not secrets.compare_digest(str(stored), code):
        raise BusinessError(9003, "验证码错误")
    await request.app.state.redis.raw.delete(verify_code_key(phone))
    await request.app.state.redis.raw.delete(f"user:verify:expire:{phone}")


async def send_verify_code(request: Request, phone: str) -> None:
    started = perf_counter()
    _validate_phone(phone)
    redis = request.app.state.redis.raw
    expire_key = f"user:verify:expire:{phone}"
    if await redis.exists(expire_key):
        raise BusinessError(9005, "操作过于频繁，请稍后重试")
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    await redis.set(verify_code_key(phone), code, ex=VERIFY_CODE_TTL_SECONDS)
    await redis.set(expire_key, "1", ex=VERIFY_RATE_LIMIT_SECONDS)
    await logger.ainfo(
        "business_operation_completed",
        **_operation_log_fields(
            request.state.request_id,
            "send_verify_code",
            "success",
            round((perf_counter() - started) * 1000),
        ),
    )


async def _phone_login(
    request: Request, session: AsyncSession, payload: PhoneLoginRequest, *, register: bool
) -> dict[str, object]:
    _validate_phone(payload.phone)
    await _verify_code(request, payload.phone, payload.verify_code)
    user = await _find_user(session, phone=payload.phone)
    if register and user is not None:
        raise BusinessError(1005, "该手机号已注册，请直接登录")
    if not register and user is None:
        raise BusinessError(1006, "该手机号未注册，请先注册")
    if user is None:
        user = await _commit_new_user(
            session,
            User(
                openid=f"phone_{payload.phone}",
                phone=payload.phone,
                nick_name=f"用户{payload.phone[-4:]}",
                member_level=0,
                status=0,
                is_deleted=0,
            ),
        )
    return _login_payload(user, request.app.state.settings)


async def phone_login(
    request: Request, session: AsyncSession, payload: PhoneLoginRequest
) -> dict[str, object]:
    return await _phone_login(request, session, payload, register=False)


async def register_by_phone(
    request: Request, session: AsyncSession, payload: PhoneLoginRequest
) -> dict[str, object]:
    return await _phone_login(request, session, payload, register=True)


async def get_user_info(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None]:
    user = await _find_user(session, user_id=user_id)
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return _user_payload(user)


async def update_user_info(
    request: Request, session: AsyncSession, user_id: int, payload: UpdateUserRequest
) -> None:
    user = await _find_user(session, user_id=user_id)
    if user is None:
        raise BusinessError(1001, "用户不存在")
    changed = False
    if payload.nick_name is not None and payload.nick_name.strip():
        user.nick_name = payload.nick_name.strip()
        changed = True
    if payload.avatar_url is not None and payload.avatar_url.strip():
        user.avatar_url = payload.avatar_url.strip()
        changed = True
    if changed:
        await session.commit()


async def logout(
    request: Request, session: AsyncSession, user_id: int, claims: TokenClaims
) -> None:
    user = await _find_user(session, user_id=user_id)
    if user is None:
        raise BusinessError(1001, "用户不存在")
    remaining_ms = max(0, round((claims.expires_at - datetime.now(UTC)).total_seconds() * 1000))
    if remaining_ms:
        await request.app.state.redis.raw.set(
            logout_blacklist_key(claims.jti), str(user_id), px=remaining_ms
        )
    await logger.ainfo(
        "business_operation_completed",
        **_operation_log_fields(request.state.request_id, "logout", "success", 0),
    )
