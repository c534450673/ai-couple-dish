"""Administrator API with isolated JWT issuer/audience and an audit trail."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt
import structlog
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from packages.platform.service import create_service_app

logger = structlog.get_logger()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class ReviewRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    approved: bool
    reason: str | None = Field(default=None, max_length=512)


class ImportRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    source: str = Field(default="admin", min_length=1, max_length=128)


class FlagRequest(BaseModel):
    flagged: bool = True
    reason: str | None = Field(default=None, max_length=512)


# Backwards-compatible names used by early contract tests.
Login = LoginRequest
Review = ReviewRequest


def _envelope(data: Any = None, message: str = "操作成功", code: int = 200) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def _secret(value: str | None) -> str | None:
    resolved = value or os.getenv("ADMIN_JWT_SECRET")
    if resolved and len(resolved) < 64:
        raise ValueError("ADMIN_JWT_SECRET 至少64字符")
    return resolved


def _masked_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    if len(phone) <= 7:
        return "*" * len(phone)
    return f"{phone[:3]}****{phone[-4:]}"


def create_app(*, secret: str | None = None) -> FastAPI:
    signing_secret = _secret(secret)
    app = create_service_app("admin")
    audits: list[dict[str, Any]] = []
    reviews: dict[str, dict[str, Any]] = {}
    imports: list[dict[str, Any]] = []
    orders: dict[str, dict[str, Any]] = {}
    users: dict[int, dict[str, Any]] = {}

    def fail(status: int, code: int, message: str) -> HTTPException:
        return HTTPException(status_code=status, detail=_envelope(code=code, message=message))

    def claims(authorization: str | None) -> dict[str, Any]:
        if not signing_secret:
            raise fail(503, 503, "管理员密钥未配置")
        if not authorization or not authorization.startswith("Bearer "):
            raise fail(401, 401, "请先登录")
        try:
            payload = jwt.decode(
                authorization.removeprefix("Bearer ").strip(),
                signing_secret,
                algorithms=["HS512"],
                audience="admin-web",
                issuer="admin-service",
                options={"require": ["sub", "role", "iss", "aud", "jti", "iat", "exp"]},
            )
        except jwt.PyJWTError as error:
            logger.info(
                "admin_auth_denied",
                module="admin",
                operation="authenticate",
                result="denied",
                errorCode=type(error).__name__,
            )
            raise fail(403, 403, "无管理员权限") from error
        if payload.get("role") != "admin":
            raise fail(403, 403, "无管理员权限")
        return payload

    def audit(
        actor: str,
        operation: str,
        *,
        target: str | None = None,
        result: str = "success",
        **extra: Any,
    ) -> None:
        record = {
            "id": uuid4().hex,
            "actor": actor,
            "operation": operation,
            "target": target,
            "result": result,
            "createdAt": datetime.now(UTC).isoformat(),
            **extra,
        }
        audits.append(record)
        logger.info(
            "admin_audit", module="admin", operation=operation, result=result, target=target or "-"
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        detail = (
            error.detail
            if isinstance(error.detail, dict)
            else _envelope(code=error.status_code, message=str(error.detail))
        )
        return JSONResponse(status_code=error.status_code, content=detail)

    @app.post("/api/admin/login")
    async def login(payload: LoginRequest) -> dict[str, Any]:
        if not signing_secret:
            raise fail(503, 503, "管理员密钥未配置")
        configured_user = os.getenv("ADMIN_USERNAME")
        password_hash = os.getenv("ADMIN_PASSWORD_HASH")
        if not configured_user or not password_hash:
            raise fail(503, 503, "管理员凭据未配置")
        if payload.username != configured_user:
            raise fail(401, 401, "用户名或密码错误")
        try:
            valid = bcrypt.checkpw(payload.password.encode(), password_hash.encode())
        except ValueError:
            valid = False
        if not valid:
            raise fail(401, 401, "用户名或密码错误")
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": payload.username,
                "role": "admin",
                "iss": "admin-service",
                "aud": "admin-web",
                "jti": uuid4().hex,
                "iat": now,
                "exp": now + timedelta(hours=8),
            },
            signing_secret,
            algorithm="HS512",
        )
        audit(payload.username, "admin.login")
        return _envelope({"token": token, "expiresIn": 8 * 3600})

    @app.post("/api/admin/catalog/review")
    async def review(
        payload: ReviewRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = claims(authorization)
        status = "approved" if payload.approved else "rejected"
        reviews[payload.slug] = {
            "slug": payload.slug,
            "reviewStatus": status,
            "reason": payload.reason,
            "updatedAt": datetime.now(UTC).isoformat(),
        }
        audit(str(actor["sub"]), "catalog.review", target=payload.slug, reviewStatus=status)
        return _envelope(reviews[payload.slug])

    @app.post("/api/admin/catalog/{slug}/publish")
    async def publish(
        slug: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = claims(authorization)
        review = reviews.get(slug)
        if not review or review.get("reviewStatus") != "approved":
            raise fail(422, 422, "菜品来源未审核")
        review["published"] = True
        audit(str(actor["sub"]), "catalog.publish", target=slug)
        return _envelope({"slug": slug, "status": "published"})

    @app.post("/api/admin/catalog/import")
    async def import_catalog(
        payload: ImportRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = claims(authorization)
        failures = [
            {"row": i, "reason": "slug required"}
            for i, row in enumerate(payload.rows)
            if not row.get("slug")
        ]
        result = {
            "source": payload.source,
            "imported": len(payload.rows) - len(failures),
            "failed": len(failures),
            "failures": failures,
        }
        imports.append(result)
        audit(
            str(actor["sub"]),
            "catalog.import",
            target=payload.source,
            imported=result["imported"],
            failed=result["failed"],
        )
        return _envelope(result)

    @app.get("/api/admin/catalog/export")
    async def export_catalog(authorization: str | None = Header(default=None)) -> StreamingResponse:
        actor = claims(authorization)
        audit(str(actor["sub"]), "catalog.export")
        payload = json.dumps(list(reviews.values()), ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            iter([payload]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=catalog.json"},
        )

    @app.get("/api/admin/orders")
    async def list_orders(
        status: str | None = Query(default=None), authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        claims(authorization)
        values = [
            item for item in orders.values() if status is None or item.get("status") == status
        ]
        return _envelope({"items": values, "total": len(values)})

    @app.post("/api/admin/orders/{order_id}/flag")
    async def flag_order(
        order_id: str, payload: FlagRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = claims(authorization)
        order = orders.setdefault(order_id, {"orderId": order_id, "status": "unknown"})
        order.update({"flagged": payload.flagged, "flagReason": payload.reason})
        audit(str(actor["sub"]), "order.flag", target=order_id, flagged=payload.flagged)
        return _envelope(order)

    @app.get("/api/admin/users/{user_id}")
    async def user(
        user_id: int, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        claims(authorization)
        value = users.get(user_id)
        if value is None:
            raise fail(404, 404, "用户不存在")
        data = {**value, "phone": _masked_phone(value.get("phone"))}
        data.pop("openid", None)
        return _envelope(data)

    @app.get("/api/admin/audit")
    async def get_audit(
        authorization: str | None = Header(default=None), operation: str | None = None
    ) -> dict[str, Any]:
        claims(authorization)
        items = [item for item in audits if operation is None or item["operation"] == operation]
        return _envelope({"items": items, "total": len(items)})

    return app


app = create_app()
