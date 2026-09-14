"""Administrator API with isolated JWT issuer/audience and an audit trail."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt
import structlog
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import Database
from packages.platform.service import create_service_app
from services.catalog.app.services.catalog import (
    CatalogNotFoundError,
    CatalogNotPublishableError,
    CatalogStore,
    SqlAlchemyCatalogStore,
)

logger = structlog.get_logger()
SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class ReviewRequest(BaseModel):
    model_config = {"populate_by_name": True}

    slug: str = Field(min_length=1, max_length=128)
    approved: bool
    reason: str | None = Field(default=None, max_length=512)
    source_id: int | None = Field(default=None, alias="sourceId", ge=1)


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


def create_app(
    *,
    secret: str | None = None,
    session_provider: SessionProvider | None = None,
    catalog_store: CatalogStore | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    signing_secret = _secret(secret)
    active_settings = settings
    if active_settings is None:
        try:
            active_settings = get_settings()
        except ValidationError:
            # Import-time tooling and the unit-test substitute may omit runtime secrets.
            if os.getenv("APP_ENV") in {"prod", "staging"}:
                raise
    app = create_service_app("admin", settings=active_settings)
    audits: list[dict[str, Any]] = []
    reviews: dict[str, dict[str, Any]] = {}
    imports: list[dict[str, Any]] = []
    orders: dict[str, dict[str, Any]] = {}
    users: dict[int, dict[str, Any]] = {}
    # The id is resolved from ``admin_user`` at login time and copied into the
    # JWT/audit rows.  It is intentionally never a hard-coded sentinel.
    admin_user_ids: dict[str, int] = {}
    revoked_jtis: set[str] = set()
    active_catalog_store = catalog_store or SqlAlchemyCatalogStore()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if session_provider is not None:
            application.state.session_provider = session_provider
            yield
            return
        if active_settings is None:
            application.state.session_provider = None
            yield
            return
        database = Database(
            active_settings.database_url,
            pool_size=active_settings.database_pool_size,
            max_overflow=active_settings.database_max_overflow,
        )
        application.state.session_provider = database.session
        await database.connect()
        await logger.ainfo(
            "admin_dependencies_connected",
            module="admin",
            operation="startup",
            result="success",
            dependencies=["database"],
        )
        try:
            yield
        finally:
            await database.close()
            await logger.ainfo(
                "admin_dependencies_closed",
                module="admin",
                operation="shutdown",
                result="success",
                dependencies=["database"],
            )

    app.router.lifespan_context = lifespan
    app.state.session_provider = session_provider
    app.state.persistence_configured = session_provider is not None or active_settings is not None

    def fail(status: int, code: int, message: str) -> HTTPException:
        return HTTPException(status_code=status, detail=_envelope(code=code, message=message))

    async def rollback_if_supported(session: AsyncSession) -> None:
        """回滚目录事务；测试替身没有 rollback 时保持兼容。"""
        rollback = getattr(session, "rollback", None)
        if rollback is not None:
            await rollback()

    async def claims(authorization: str | None) -> dict[str, Any]:
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
        if str(payload["jti"]) in revoked_jtis:
            raise fail(403, 403, "管理员会话已失效")
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    result = await session.execute(
                        text(
                            """
                            SELECT s.revoked_at, s.expires_at, u.status, s.admin_user_id
                            FROM admin_session s
                            JOIN admin_user u ON u.id = s.admin_user_id
                            WHERE s.jti = :jti
                            LIMIT 1
                            """
                        ),
                        {"jti": payload["jti"]},
                    )
                    mapped = result.mappings()
                    try:
                        row = mapped.first()
                    except AttributeError:
                        rows = mapped.all()
                        row = rows[0] if rows else None
            except Exception as error:
                await logger.aerror(
                    "admin_session_validation_failed",
                    module="admin",
                    operation="authenticate.session",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "管理员会话暂不可用") from error
            if row is None:
                raise fail(403, 403, "管理员会话已失效")
            expires_at = row.get("expires_at")
            revoked_at = row.get("revoked_at")
            status = str(row.get("status", "active"))
            now = datetime.now(UTC).replace(tzinfo=None)
            if revoked_at is not None or status != "active":
                raise fail(403, 403, "管理员会话已失效")
            if expires_at is not None and expires_at <= now:
                raise fail(403, 403, "管理员会话已过期")
            claim_admin_id = actor_id(payload)
            if claim_admin_id is not None and int(row["admin_user_id"]) != claim_admin_id:
                raise fail(403, 403, "管理员会话已失效")
        return payload

    def actor_id(payload: dict[str, Any]) -> int | None:
        value = payload.get("adminUserId")
        try:
            resolved = int(str(value))
        except (TypeError, ValueError):
            return None
        return resolved if resolved > 0 else None

    async def ensure_admin_user(username: str, password_hash: str) -> int:
        """Resolve the persisted administrator identity used by sessions/audits.

        The environment remains the source of truth for the bcrypt credential,
        while ``admin_user`` gives each replica a stable foreign identity.  A
        missing row is provisioned once; a failed read/write is surfaced rather
        than silently falling back to an in-memory or zero id.
        """
        if username in admin_user_ids:
            return admin_user_ids[username]
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            # Unit-test and import-only mode has no persistence by design.  The
            # value is only embedded in a token and never written to a DB.
            return 1
        try:
            async with provider() as session:
                result = await session.execute(
                    text(
                        "SELECT id, status FROM admin_user "
                        "WHERE username = :username LIMIT 1"
                    ),
                    {"username": username},
                )
                rows = result.mappings().all()
                row = rows[0] if rows else None
                if row is not None:
                    if str(row.get("status", "active")) != "active":
                        raise fail(403, 403, "管理员账号已停用")
                    resolved = int(row["id"])
                else:
                    await session.execute(
                        text(
                            "INSERT INTO admin_user "
                            "(username, password_hash, roles_json, status) "
                            "VALUES (:username, :password_hash, :roles_json, 'active')"
                        ),
                        {
                            "username": username,
                            "password_hash": password_hash,
                            "roles_json": json.dumps(["admin"]),
                        },
                    )
                    await session.commit()
                    result = await session.execute(
                        text(
                            "SELECT id, status FROM admin_user "
                            "WHERE username = :username LIMIT 1"
                        ),
                        {"username": username},
                    )
                    rows = result.mappings().all()
                    if not rows:
                        raise fail(503, 503, "管理员数据暂不可用")
                    resolved = int(rows[0]["id"])
                    if str(rows[0].get("status", "active")) != "active":
                        raise fail(403, 403, "管理员账号已停用")
        except HTTPException:
            raise
        except Exception as error:
            await logger.aerror(
                "admin_user_persistence_failed",
                module="admin",
                operation="login.admin_user",
                result="error",
                errorCode=type(error).__name__,
            )
            raise fail(503, 503, "管理员数据暂不可用") from error
        admin_user_ids[username] = resolved
        await logger.ainfo(
            "admin_user_resolved",
            module="admin",
            operation="login.admin_user",
            result="success",
            adminUserId=resolved,
        )
        return resolved

    async def persist_audit(record: dict[str, Any]) -> None:
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return
        metadata = {
            key: value
            for key, value in record.items()
            if key not in {"id", "operation", "target", "result", "createdAt"}
        }
        try:
            async with provider() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO admin_audit_log
                          (admin_user_id, operation, target_type, target_id, result,
                           metadata_json, created_at)
                        VALUES (:admin_user_id, :operation, :target_type, :target_id, :result,
                                :metadata_json, :created_at)
                        """
                    ),
                    {
                        "operation": record["operation"],
                        "admin_user_id": record.get("adminUserId"),
                        "target_type": record.get("targetType"),
                        "target_id": record.get("target"),
                        "result": record["result"],
                        "metadata_json": json.dumps(metadata, ensure_ascii=False, default=str),
                        "created_at": datetime.fromisoformat(record["createdAt"])
                        .astimezone(UTC)
                        .replace(tzinfo=None),
                    },
                )
                await session.commit()
        except Exception as error:
            await logger.aerror(
                "admin_persistence_failed",
                module="admin",
                operation=record["operation"],
                result="error",
                errorCode=type(error).__name__,
            )
            raise fail(503, 503, "管理员数据暂不可用") from error

    async def load_audits(operation: str | None = None) -> list[dict[str, Any]] | None:
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return None
        try:
            async with provider() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, admin_user_id, operation, target_type, target_id, result,
                               metadata_json, created_at
                        FROM admin_audit_log
                        WHERE (:operation IS NULL OR operation = :operation)
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"operation": operation},
                )
                rows = result.mappings().all()
        except Exception as error:
            await logger.aerror(
                "admin_persistence_read_failed",
                module="admin",
                operation="audit.read",
                result="error",
                errorCode=type(error).__name__,
            )
            raise fail(503, 503, "管理员数据暂不可用") from error
        records: list[dict[str, Any]] = []
        for row in rows:
            metadata = row.get("metadata_json") or "{}"
            try:
                extra = json.loads(metadata) if isinstance(metadata, str) else {}
            except json.JSONDecodeError:
                extra = {}
            created = row.get("created_at")
            created_text = (
                str(created.isoformat())
                if created is not None and hasattr(created, "isoformat")
                else str(created)
            )
            records.append(
                {
                    "id": str(row.get("id")),
                    "adminUserId": row.get("admin_user_id"),
                    "actor": extra.pop("actor", None),
                    "operation": row.get("operation"),
                    "target": row.get("target_id"),
                    "result": row.get("result"),
                    "createdAt": created_text,
                    **extra,
                }
            )
        return records

    async def load_orders() -> list[dict[str, Any]] | None:
        """Load dining orders from the shared store and overlay admin flags."""
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return None
        try:
            async with provider() as session:
                result = await session.execute(
                    text(
                        "SELECT id, order_no, status, total_amount, user_id, couple_id, "
                        "remark, create_time FROM dining_order "
                        "ORDER BY create_time DESC, id DESC LIMIT 1000"
                    )
                )
                rows = result.mappings().all()
        except Exception as error:
            await logger.aerror(
                "admin_orders_read_failed",
                module="admin",
                operation="orders.list",
                result="error",
                errorCode=type(error).__name__,
            )
            raise fail(503, 503, "管理员数据暂不可用") from error
        flags = await load_audits("order.flag") or []
        latest_flags: dict[str, dict[str, Any]] = {}
        for item in flags:
            target = item.get("target")
            if target is not None:
                latest_flags[str(target)] = item
        values: list[dict[str, Any]] = []
        for row in rows:
            order_id = str(row["id"])
            flag = latest_flags.get(order_id, {})
            created = row.get("create_time")
            values.append(
                {
                    "orderId": order_id,
                    "orderNo": row.get("order_no"),
                    "status": row.get("status", "unknown"),
                    "totalAmount": str(row["total_amount"])
                    if row.get("total_amount") is not None
                    else None,
                    "userId": row.get("user_id"),
                    "coupleId": row.get("couple_id"),
                    "remark": row.get("remark"),
                    "createdAt": str(created.isoformat())
                    if created is not None and hasattr(created, "isoformat")
                    else created,
                    "flagged": flag.get("flagged", False),
                    "flagReason": flag.get("flagReason"),
                }
            )
        await logger.ainfo(
            "admin_orders_loaded",
            module="admin",
            operation="orders.list",
            result="success",
            returnedCount=len(values),
        )
        return values

    async def load_latest_order(order_id: str) -> dict[str, Any] | None:
        records = await load_audits("order.flag")
        if records is None:
            return orders.get(order_id)
        latest = next((item for item in reversed(records) if item.get("target") == order_id), None)
        if latest is None:
            return None
        return {
            "orderId": order_id,
            "status": latest.get("status", "unknown"),
            "flagged": latest.get("flagged", False),
            "flagReason": latest.get("flagReason"),
        }

    async def load_import_batches() -> list[dict[str, Any]] | None:
        """Read catalog import batches from the catalog-owned table.

        The audit log records who initiated an import; the catalog batch is the
        source of truth for counts and row-level failures.
        """
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return None
        try:
            async with provider() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, source_name, imported_count, failed_count,
                               failure_report_json, created_at
                        FROM catalog_import_batch
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1000
                        """
                    )
                )
                rows = result.mappings().all()
        except Exception as error:
            await logger.aerror(
                "admin_import_batches_read_failed",
                module="admin",
                operation="catalog.imports.list",
                result="error",
                errorCode=type(error).__name__,
            )
            raise fail(503, 503, "管理员数据暂不可用") from error
        values: list[dict[str, Any]] = []
        for row in rows:
            failure_report = row.get("failure_report_json") or "[]"
            try:
                failures = json.loads(failure_report) if isinstance(failure_report, str) else []
            except json.JSONDecodeError:
                failures = []
            created = row.get("created_at")
            values.append(
                {
                    "id": str(row.get("id")),
                    "target": row.get("source_name"),
                    "source": row.get("source_name"),
                    "imported": int(row.get("imported_count") or 0),
                    "failed": int(row.get("failed_count") or 0),
                    "failures": failures,
                    "createdAt": (
                        created.isoformat()
                        if created is not None and hasattr(created, "isoformat")
                        else str(created)
                    ),
                }
            )
        return values

    async def audit(
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
        # Actor is metadata only; passwords, tokens, openids and phone numbers are never included.
        record["actor"] = actor
        await persist_audit(record)
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
        admin_id = await ensure_admin_user(payload.username, password_hash)
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": payload.username,
                "role": "admin",
                "iss": "admin-service",
                "aud": "admin-web",
                "jti": uuid4().hex,
                "adminUserId": admin_id,
                "iat": now,
                "exp": now + timedelta(hours=8),
            },
            signing_secret,
            algorithm="HS512",
        )
        jti = jwt.decode(token, options={"verify_signature": False})["jti"]
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    await session.execute(
                        text(
                            "INSERT INTO admin_session (admin_user_id, jti, expires_at) "
                            "VALUES (:admin_user_id, :jti, :expires_at)"
                        ),
                        {
                            "admin_user_id": admin_id,
                            "jti": jti,
                            "expires_at": (now + timedelta(hours=8)).replace(tzinfo=None),
                        },
                    )
                    await session.execute(
                        text(
                            "UPDATE admin_user SET last_login_at = :last_login_at "
                            "WHERE id = :admin_user_id"
                        ),
                        {
                            "last_login_at": now.replace(tzinfo=None),
                            "admin_user_id": admin_id,
                        },
                    )
                    await session.commit()
            except Exception as error:
                await logger.aerror(
                    "admin_session_persistence_failed",
                    module="admin",
                    operation="login.session",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "管理员数据暂不可用") from error
        await audit(payload.username, "admin.login", adminUserId=admin_id)
        return _envelope({"token": token, "expiresIn": 8 * 3600})

    @app.post("/api/admin/logout")
    async def logout(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        actor = await claims(authorization)
        jti = str(actor["jti"])
        revoked_jtis.add(jti)
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    await session.execute(
                        text(
                            "UPDATE admin_session SET revoked_at = :revoked_at "
                            "WHERE jti = :jti AND revoked_at IS NULL"
                        ),
                        {"revoked_at": datetime.now(UTC).replace(tzinfo=None), "jti": jti},
                    )
                    await session.commit()
            except Exception as error:
                revoked_jtis.discard(jti)
                await logger.aerror(
                    "admin_session_revoke_failed",
                    module="admin",
                    operation="logout",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "管理员会话暂不可用") from error
        await audit(
            str(actor["sub"]),
            "admin.logout",
            adminUserId=actor_id(actor),
            sessionJti=jti,
            persisted=provider is not None,
        )
        await logger.ainfo(
            "admin_session_revoked",
            module="admin",
            operation="logout",
            result="success",
            adminUserId=actor_id(actor),
            persisted=provider is not None,
        )
        return _envelope({"revoked": True})

    @app.post("/api/admin/catalog/review")
    async def review(
        payload: ReviewRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = await claims(authorization)
        status = "approved" if payload.approved else "rejected"
        persisted_result: dict[str, Any] | None = None
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    source_id = payload.source_id
                    if source_id is None:
                        source_result = await session.execute(
                            text(
                                """
                                SELECT d.id AS dish_id, s.id AS source_id
                                FROM catalog_dish d
                                LEFT JOIN catalog_dish_source s ON s.dish_id = d.id
                                WHERE d.slug = :slug
                                ORDER BY CASE WHEN s.review_status = 'pending' THEN 0 ELSE 1 END,
                                         s.id
                                LIMIT 1
                                """
                            ),
                            {"slug": payload.slug},
                        )
                        source_rows = source_result.mappings().all()
                        if not source_rows:
                            raise fail(404, 404, "菜品不存在")
                        source_id = source_rows[0].get("source_id")
                    if source_id is None:
                        raise fail(422, 422, "菜品没有授权来源")
                    persisted_result = await active_catalog_store.review_source(
                        session,
                        dish_reference=payload.slug,
                        source_id=source_id,
                        approved=payload.approved,
                    )
                    await session.commit()
            except HTTPException:
                raise
            except CatalogNotFoundError as error:
                await rollback_if_supported(session)
                raise fail(404, 404, str(error)) from error
            except SQLAlchemyError as error:
                await rollback_if_supported(session)
                await logger.aerror(
                    "admin_catalog_review_persistence_failed",
                    module="admin",
                    operation="catalog.review",
                    result="error",
                    slug=payload.slug,
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "菜品审核保存失败") from error
        review_record = {
            "slug": payload.slug,
            "reviewStatus": status,
            "reason": payload.reason,
            "updatedAt": datetime.now(UTC).isoformat(),
            **(persisted_result or {}),
        }
        reviews[payload.slug] = review_record
        await audit(
            str(actor["sub"]),
            "catalog.review",
            target=payload.slug,
            targetType="catalog",
            adminUserId=actor_id(actor),
            reviewStatus=status,
            reason=payload.reason,
        )
        await logger.ainfo(
            "admin_catalog_review_persisted",
            module="admin",
            operation="catalog.review",
            result="success",
            slug=payload.slug,
            reviewStatus=status,
            persisted=provider is not None,
        )
        return _envelope(review_record)

    @app.post("/api/admin/catalog/{slug}/publish")
    async def publish(
        slug: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = await claims(authorization)
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    result = await active_catalog_store.publish_dish(
                        session, dish_reference=slug
                    )
                    await session.commit()
            except CatalogNotFoundError as error:
                await rollback_if_supported(session)
                raise fail(404, 404, str(error)) from error
            except CatalogNotPublishableError as error:
                await rollback_if_supported(session)
                raise fail(422, 422, str(error)) from error
            except SQLAlchemyError as error:
                await rollback_if_supported(session)
                await logger.aerror(
                    "admin_catalog_publish_persistence_failed",
                    module="admin",
                    operation="catalog.publish",
                    result="error",
                    slug=slug,
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "菜品发布失败") from error
            await audit(
                str(actor["sub"]),
                "catalog.publish",
                target=slug,
                targetType="catalog",
                adminUserId=actor_id(actor),
                published=True,
                persisted=True,
            )
            return _envelope({"slug": slug, **result})
        review = reviews.get(slug)
        if review is None:
            persisted = await load_audits("catalog.review")
            if persisted is not None:
                review = next(
                    (item for item in reversed(persisted) if item.get("target") == slug), None
                )
        if not review or review.get("reviewStatus") != "approved":
            raise fail(422, 422, "菜品来源未审核")
        review["published"] = True
        await audit(
            str(actor["sub"]),
            "catalog.publish",
            target=slug,
            targetType="catalog",
            adminUserId=actor_id(actor),
            published=True,
        )
        return _envelope({"slug": slug, "status": "published"})

    @app.post("/api/admin/catalog/import")
    async def import_catalog(
        payload: ImportRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = await claims(authorization)
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    result = await active_catalog_store.import_catalog(
                        session, payload.rows, source_name=payload.source
                    )
                    await session.commit()
            except (TypeError, ValueError) as error:
                await rollback_if_supported(session)
                raise fail(422, 422, str(error)) from error
            except SQLAlchemyError as error:
                await rollback_if_supported(session)
                await logger.aerror(
                    "admin_catalog_import_persistence_failed",
                    module="admin",
                    operation="catalog.import",
                    result="error",
                    source=payload.source,
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "菜品导入失败") from error
        else:
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
        await audit(
            str(actor["sub"]),
            "catalog.import",
            target=payload.source,
            targetType="catalog_import",
            adminUserId=actor_id(actor),
            imported=result["imported"],
            failed=result["failed"],
            failures=result.get("failures", []),
            persisted=provider is not None,
        )
        return _envelope(result)

    @app.get("/api/admin/catalog/export")
    async def export_catalog(authorization: str | None = Header(default=None)) -> StreamingResponse:
        actor = await claims(authorization)
        await audit(
            str(actor["sub"]),
            "catalog.export",
            adminUserId=actor_id(actor),
        )
        persisted = await load_audits("catalog.review")
        if persisted is not None:
            recovered: dict[str, dict[str, Any]] = {}
            for item in persisted:
                target = item.get("target")
                if target:
                    recovered[str(target)] = {
                        "slug": str(target),
                        "reviewStatus": item.get("reviewStatus"),
                        "reason": item.get("reason"),
                        "updatedAt": item.get("createdAt"),
                    }
            export_rows = list(recovered.values())
        else:
            export_rows = list(reviews.values())
        payload = json.dumps(export_rows, ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            iter([payload]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=catalog.json"},
        )

    @app.get("/api/admin/orders")
    async def list_orders(
        status: str | None = Query(default=None), authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        await claims(authorization)
        persisted = await load_orders()
        if persisted is not None:
            values = persisted
        else:
            values = list(orders.values())
        values = [item for item in values if status is None or item.get("status") == status]
        return _envelope({"items": values, "total": len(values)})

    @app.post("/api/admin/orders/{order_id}/flag")
    async def flag_order(
        order_id: str, payload: FlagRequest, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        actor = await claims(authorization)
        order = await load_latest_order(order_id) or orders.setdefault(
            order_id, {"orderId": order_id, "status": "unknown"}
        )
        order.update({"flagged": payload.flagged, "flagReason": payload.reason})
        await audit(
            str(actor["sub"]),
            "order.flag",
            target=order_id,
            targetType="dining_order",
            adminUserId=actor_id(actor),
            status=order.get("status", "unknown"),
            flagged=payload.flagged,
            flagReason=payload.reason,
        )
        return _envelope(order)

    @app.get("/api/admin/users/{user_id}")
    async def user(
        user_id: int, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        await claims(authorization)
        value = users.get(user_id)
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if value is None and provider is not None:
            try:
                async with provider() as session:
                    result = await session.execute(
                        text(
                            "SELECT id, nick_name, avatar_url, phone, gender, couple_id, "
                            "member_level, status FROM t_user "
                            "WHERE id = :user_id AND is_deleted = 0 LIMIT 1"
                        ),
                        {"user_id": user_id},
                    )
                    row = result.mappings().first()
                    if row is not None:
                        value = {
                            "id": int(row["id"]),
                            "nickName": row.get("nick_name"),
                            "avatarUrl": row.get("avatar_url"),
                            "phone": row.get("phone"),
                            "gender": row.get("gender"),
                            "coupleId": row.get("couple_id"),
                            "memberLevel": row.get("member_level"),
                            "status": row.get("status"),
                        }
            except Exception as error:
                await logger.aerror(
                    "admin_user_read_failed",
                    module="admin",
                    operation="users.get",
                    result="error",
                    userId=user_id,
                    errorCode=type(error).__name__,
                )
                raise fail(503, 503, "管理员数据暂不可用") from error
        if value is None:
            raise fail(404, 404, "用户不存在")
        data = {**value, "phone": _masked_phone(value.get("phone"))}
        data.pop("openid", None)
        return _envelope(data)

    @app.get("/api/admin/audit")
    async def get_audit(
        authorization: str | None = Header(default=None), operation: str | None = None
    ) -> dict[str, Any]:
        await claims(authorization)
        persisted = await load_audits(operation)
        items = persisted if persisted is not None else [
            item for item in audits if operation is None or item["operation"] == operation
        ]
        return _envelope({"items": items, "total": len(items)})

    @app.get("/api/admin/catalog/imports")
    async def get_imports(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        await claims(authorization)
        persisted = await load_import_batches()
        if persisted == []:
            # Keep visibility for historical imports created before the batch
            # table was introduced or during a partial migration.
            persisted = await load_audits("catalog.import")
        items = persisted if persisted is not None else [
            item for item in audits if item["operation"] == "catalog.import"
        ]
        return _envelope({"items": items, "total": len(items)})

    return app


app = create_app()
