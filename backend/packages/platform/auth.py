from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt


def _validate_secret(secret: str) -> None:
    if len(secret) < 64:
        raise ValueError("JWT_SECRET 至少64字符")


def issue_user_token(*, user_id: int, secret: str, expires_ms: int) -> str:
    _validate_secret(secret)
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "userId": user_id,
            "jti": uuid4().hex,
            "iat": now,
            "exp": now + timedelta(milliseconds=expires_ms),
        },
        secret,
        algorithm="HS512",
    )


def decode_token(token: str, *, secret: str) -> dict[str, Any]:
    _validate_secret(secret)
    return jwt.decode(
        token,
        secret,
        algorithms=["HS512"],
        options={"require": ["sub", "userId", "jti", "iat", "exp"]},
    )
