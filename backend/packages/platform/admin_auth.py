"""Verify administrator tokens at each service's write boundary."""

from __future__ import annotations

import os

import jwt
import structlog
from fastapi import HTTPException, Request

logger = structlog.get_logger()


def require_admin(request: Request) -> None:
    secret = os.getenv("ADMIN_JWT_SECRET")
    if not secret or len(secret) < 64:
        raise HTTPException(
            status_code=503,
            detail={"code": 503, "message": "管理员认证未配置", "data": None},
        )
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"code": 401, "message": "请先登录", "data": None}
        )
    try:
        claims = jwt.decode(
            authorization.removeprefix("Bearer ").strip(),
            secret,
            algorithms=["HS512"],
            audience="admin-web",
            issuer="admin-service",
            options={"require": ["sub", "role", "iss", "aud", "jti", "iat", "exp"]},
        )
    except jwt.PyJWTError as error:
        logger.warning(
            "admin_auth_rejected",
            requestId=getattr(request.state, "request_id", "unknown"),
            module="admin_auth",
            operation=request.url.path,
            result="denied",
            errorCode=type(error).__name__,
        )
        raise HTTPException(
            status_code=403, detail={"code": 403, "message": "无管理员权限", "data": None}
        ) from error
    if claims.get("role") != "admin":
        raise HTTPException(
            status_code=403, detail={"code": 403, "message": "无管理员权限", "data": None}
        )
