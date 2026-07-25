from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from uuid import uuid4

import jwt
import structlog
from fastapi import Request
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.errors import BusinessError
from app.redis.keys import logout_blacklist_key

logger = structlog.get_logger()


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    jti: str
    expires_at: datetime


def create_access_token(user_id: int, secret: str, expiration_ms: int) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "userId": user_id,
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(milliseconds=expiration_ms),
    }
    token = jwt.encode(claims, secret, algorithm="HS512")
    logger.info(
        "access_token_created",
        module="auth",
        operation="create_access_token",
        result="completed",
        algorithm="HS512",
    )
    return token


def decode_access_token(token: str, secret: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS512"],
            options={"require": ["sub", "userId", "jti", "iat", "exp"]},
        )
        subject_user_id = int(payload["sub"])
        if type(payload["userId"]) is not int:
            raise TypeError("invalid user id type")
        claim_user_id = payload["userId"]
        if subject_user_id != claim_user_id:
            raise ValueError("inconsistent user id claims")
        jti = payload["jti"]
        if not isinstance(jti, str):
            raise TypeError("invalid jti type")
        logout_blacklist_key(jti)
        numeric_dates: dict[str, datetime] = {}
        for claim_name in ("iat", "exp"):
            claim_value = payload[claim_name]
            if (
                isinstance(claim_value, bool)
                or not isinstance(claim_value, (int, float))
                or not isfinite(claim_value)
            ):
                raise TypeError("invalid NumericDate claim")
            numeric_dates[claim_name] = datetime.fromtimestamp(claim_value, tz=UTC)
        expires_at = numeric_dates["exp"]
    except (InvalidTokenError, KeyError, TypeError, ValueError, OverflowError, OSError) as error:
        logger.warning(
            "access_token_rejected",
            module="auth",
            operation="decode_access_token",
            result="rejected",
            reason=type(error).__name__,
        )
        raise BusinessError(401, "登录已过期，请重新登录", http_status=401) from error
    logger.info(
        "access_token_decoded",
        module="auth",
        operation="decode_access_token",
        result="completed",
        algorithm="HS512",
    )
    return TokenClaims(user_id=subject_user_id, jti=jti, expires_at=expires_at)


async def current_user_id(
    request: Request,
) -> int:
    route = request.url.path
    authorization_values = request.headers.getlist("authorization")
    if len(authorization_values) != 1:
        await logger.awarning(
            "authorization_rejected",
            module="auth",
            operation="current_user_id",
            result="rejected",
            reason="invalid_header_count",
            route=route,
        )
        raise BusinessError(401, "请先登录", http_status=401)
    authorization = authorization_values[0]
    if not authorization.startswith("Bearer "):
        await logger.awarning(
            "authorization_rejected",
            module="auth",
            operation="current_user_id",
            result="rejected",
            reason="invalid_scheme",
            route=route,
        )
        raise BusinessError(401, "请先登录", http_status=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token or " " in token or "," in token:
        await logger.awarning(
            "authorization_rejected",
            module="auth",
            operation="current_user_id",
            result="rejected",
            reason="invalid_bearer_value",
            route=route,
        )
        raise BusinessError(401, "登录信息无效", http_status=401)

    settings: Settings = request.app.state.settings
    claims = decode_access_token(token, settings.jwt_secret.get_secret_value())
    if await request.app.state.redis.raw.exists(logout_blacklist_key(claims.jti)):
        await logger.awarning(
            "authorization_rejected",
            module="auth",
            operation="current_user_id",
            result="rejected",
            reason="blacklisted",
            route=route,
        )
        raise BusinessError(401, "登录已过期，请重新登录", http_status=401)
    await logger.ainfo(
        "authorization_completed",
        module="auth",
        operation="current_user_id",
        result="completed",
        route=route,
    )
    return claims.user_id
