"""情侣共享点菜、个人购物车和订单状态机 API。"""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
from app.core.config import Settings, get_settings
from app.core.errors import BusinessError
from app.db.models import User
from app.db.session import Database
from app.redis.client import RedisClient
from app.redis.keys import logout_blacklist_key
from services.dining.app.models import DiningOrder, DiningOrderItem
from services.dining.app.services import cart, order
from services.dining.app.services.catalog import CatalogReader, HttpCatalogReader
from services.dining.app.services.idempotency import get_record, run_once

logger = structlog.get_logger()
SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class CartItemRequest(BaseModel):
    dish_id: int = Field(alias="dishId", ge=1)
    quantity: int = Field(default=1, ge=1, le=999)
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


class QuantityRequest(BaseModel):
    quantity: int = Field(ge=1, le=999)


class OrderRequest(BaseModel):
    cart_id: int | None = Field(default=None, alias="cartId", ge=1)
    item_ids: list[int] | None = Field(default=None, alias="itemIds", max_length=100)
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


class TransitionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)


def _secret(value: str | None) -> str:
    resolved = value or os.getenv("JWT_SECRET")
    if not resolved:
        raise RuntimeError("JWT_SECRET 未配置")
    if len(resolved) < 64:
        raise ValueError("JWT_SECRET 至少64字符")
    return resolved


def _result(data: object | None = None, message: str = "操作成功") -> dict[str, object | None]:
    return {"code": 200, "message": message, "data": data}


def _error(code: int, message: str) -> HTTPException:
    return HTTPException(status_code=200, detail={"code": code, "message": message, "data": None})


async def _session(request: Request) -> AsyncIterator[AsyncSession]:
    provider: SessionProvider | None = getattr(request.app.state, "session_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503, detail={"code": 503, "message": "点菜服务未就绪", "data": None}
        )
    async with provider() as session:
        yield session


async def _user_id(request: Request) -> int:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"code": 401, "message": "请先登录", "data": None}
        )
    try:
        claims = decode_access_token(
            authorization.removeprefix("Bearer ").strip(), request.app.state.jwt_secret
        )
    except BusinessError as error:
        raise HTTPException(
            status_code=401, detail={"code": 401, "message": "登录信息无效", "data": None}
        ) from error
    redis = getattr(request.app.state, "redis", None)
    if redis is None and request.app.state.requires_redis:
        raise HTTPException(
            status_code=503, detail={"code": 503, "message": "点菜服务未就绪", "data": None}
        )
    if redis is not None:
        try:
            revoked = await redis.raw.exists(logout_blacklist_key(claims.jti))
        except Exception as error:
            await logger.aerror(
                "dining_dependency_failed",
                requestId=request.state.request_id,
                module="dining",
                operation="check_token_revocation",
                result="error",
                errorCode=type(error).__name__,
            )
            raise HTTPException(
                status_code=503, detail={"code": 503, "message": "点菜服务暂不可用", "data": None}
            ) from error
        if revoked:
            await logger.awarning(
                "dining_token_rejected",
                requestId=request.state.request_id,
                module="dining",
                operation="check_token_revocation",
                result="rejected",
                errorCode="TOKEN_REVOKED",
            )
            raise HTTPException(
                status_code=401,
                detail={"code": 401, "message": "登录已过期，请重新登录", "data": None},
            )
    return claims.user_id


async def _authenticated_session(request: Request) -> AsyncIterator[AsyncSession]:
    request.state.user_id = await _user_id(request)
    async for session in _session(request):
        yield session


_AUTHENTICATED_SESSION_DEPENDENCY = Depends(_authenticated_session)


async def _identity(session: AsyncSession, user_id: int) -> tuple[int, int | None]:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise _error(1001, "用户不存在")
    return user_id, user.couple_id


def create_app(
    *,
    jwt_secret: str | None = None,
    session_provider: SessionProvider | None = None,
    catalog_reader: CatalogReader | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if session_provider is not None:
            yield
            return
        active_settings = settings or get_settings()
        database = Database(
            active_settings.database_url,
            pool_size=active_settings.database_pool_size,
            max_overflow=active_settings.database_max_overflow,
        )
        redis = RedisClient(active_settings.redis_url)
        application.state.session_provider = database.session
        application.state.redis = redis
        try:
            await database.connect()
            await redis.connect()
            await logger.ainfo(
                "dining_dependencies_connected",
                module="dining",
                operation="startup",
                result="success",
                dependencies=["database", "redis"],
            )
            yield
        finally:
            await redis.close()
            await database.close()
            await logger.ainfo(
                "dining_dependencies_closed",
                module="dining",
                operation="shutdown",
                result="success",
                dependencies=["database", "redis"],
            )

    app = FastAPI(title="Dining Service", lifespan=lifespan)
    app.state.jwt_secret = _secret(jwt_secret)
    app.state.session_provider = session_provider
    app.state.redis = None
    app.state.requires_redis = session_provider is None
    app.state.catalog_reader = catalog_reader or HttpCatalogReader(
        os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8102")
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        request.state.request_id = request.headers.get("X-Request-ID") or secrets.token_hex(16)
        started = datetime.now()
        try:
            response = await call_next(request)
        except Exception:
            raise
        response.headers["X-Request-ID"] = request.state.request_id
        await logger.ainfo(
            "dining_request_completed",
            requestId=request.state.request_id,
            module="dining",
            operation=request.url.path,
            result="success",
            durationMs=round((datetime.now() - started).total_seconds() * 1000),
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        detail = (
            error.detail
            if isinstance(error.detail, dict)
            else {"code": error.status_code, "message": str(error.detail), "data": None}
        )
        return JSONResponse(status_code=error.status_code, content=detail)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "dining"}

    async def context(request: Request, session: AsyncSession) -> tuple[int, int | None]:
        return await _identity(session, request.state.user_id)

    @app.get("/api/dining/cuisines")
    async def cuisines(request: Request) -> dict[str, object | None]:
        await _user_id(request)
        try:
            data = await app.state.catalog_reader.list_cuisines(request.state.request_id)
        except httpx.HTTPError as error:
            await logger.aerror(
                "dining_catalog_request_failed",
                requestId=request.state.request_id,
                module="dining",
                operation="catalog_cuisines",
                result="error",
                errorCode=type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
            ) from error
        return _result(data)

    @app.get("/api/dining/dishes")
    async def dishes(request: Request) -> dict[str, object | None]:
        await _user_id(request)
        query = list(request.query_params.multi_items())
        try:
            data = await app.state.catalog_reader.list_dishes(query, request.state.request_id)
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
            ) from error
        return _result(data)

    @app.get("/api/dining/cart")
    @app.get("/api/dining/cart/list")
    async def cart_list(
        request: Request, session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY
    ) -> dict[str, object]:
        user_id, couple_id = await context(request, session)
        return _result(await cart.list_items(session, user_id=user_id, couple_id=couple_id))

    @app.post("/api/dining/cart/items")
    @app.post("/api/dining/cart/add")
    async def cart_add(
        payload: CartItemRequest,
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id, couple_id = await context(request, session)
        try:
            dish = await app.state.catalog_reader.get_dish(
                payload.dish_id, request.state.request_id
            )
            if dish is None:
                raise ValueError("菜品不存在或未上架")
            item = await cart.add_item(
                session,
                user_id=user_id,
                couple_id=couple_id,
                dish=dish,
                quantity=payload.quantity,
                remark=payload.remark,
            )
            await session.commit()
            return _result(item, "加入购物车成功")
        except ValueError as error:
            await session.rollback()
            raise _error(3001, str(error)) from error
        except httpx.HTTPError as error:
            await session.rollback()
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
            ) from error

    @app.patch("/api/dining/cart/items/{item_id}")
    async def cart_update(
        item_id: int,
        payload: QuantityRequest,
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id, couple_id = await context(request, session)
        try:
            item = await cart.update_item(
                session,
                user_id=user_id,
                couple_id=couple_id,
                item_id=item_id,
                quantity=payload.quantity,
            )
            await session.commit()
            return _result(item, "更新购物车成功")
        except ValueError as error:
            await session.rollback()
            raise _error(4001, str(error)) from error

    @app.delete("/api/dining/cart/items/{item_id}")
    async def cart_remove(
        item_id: int,
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object | None]:
        user_id, couple_id = await context(request, session)
        try:
            await cart.remove_item(session, user_id=user_id, couple_id=couple_id, item_id=item_id)
            await session.commit()
            return _result(None, "移除购物车成功")
        except ValueError as error:
            await session.rollback()
            raise _error(4001, str(error)) from error

    @app.delete("/api/dining/cart")
    @app.delete("/api/dining/cart/clear")
    async def cart_clear(
        request: Request, session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY
    ) -> dict[str, object | None]:
        user_id, couple_id = await context(request, session)
        await cart.clear(session, user_id=user_id, couple_id=couple_id)
        await session.commit()
        return _result(None, "清空购物车成功")

    @app.post("/api/dining/orders")
    @app.post("/api/dining/order/create")
    async def order_create(
        payload: OrderRequest,
        request: Request,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        normalized_idempotency_key = (
            idempotency_key.strip() if idempotency_key is not None else None
        )
        if normalized_idempotency_key is not None and len(normalized_idempotency_key) > 128:
            await logger.awarning(
                "dining_order_rejected",
                requestId=request.state.request_id,
                module="dining",
                operation="order_create",
                result="rejected",
                errorCode="IDEMPOTENCY_KEY_TOO_LONG",
                keyLength=len(normalized_idempotency_key),
            )
            raise _error(4002, "Idempotency-Key长度不能超过128")
        user_id, couple_id = await context(request, session)
        if normalized_idempotency_key is None or not normalized_idempotency_key:
            await logger.awarning(
                "dining_order_rejected",
                requestId=request.state.request_id,
                module="dining",
                operation="order_create",
                result="rejected",
                errorCode="IDEMPOTENCY_KEY_REQUIRED",
                userId=user_id,
            )
            raise _error(4002, "Idempotency-Key不能为空")
        idempotency_key = normalized_idempotency_key
        cart_row = await cart.cart_scope(session, user_id=user_id, couple_id=couple_id)

        async def action() -> dict[str, object]:
            created = await order.create_from_cart(
                session,
                user_id=user_id,
                couple_id=couple_id,
                cart_id=payload.cart_id or cart_row.id,
                item_ids=payload.item_ids,
                remark=payload.remark,
            )
            await session.flush()
            return _result(order.payload(created), "创建订单成功")

        try:
            result = await run_once(session, user_id, idempotency_key, action)
            await session.commit()
            return result
        except IntegrityError as error:
            await session.rollback()
            if idempotency_key:
                existing = await get_record(session, user_id, idempotency_key)
                if existing is not None:
                    return existing
            raise _error(409, "请求正在处理，请勿重复提交") from error
        except (ValueError, PermissionError) as error:
            await session.rollback()
            raise _error(4002, str(error)) from error

    async def transition_endpoint(
        order_id: int,
        target: str,
        request: Request,
        payload: TransitionRequest | None,
        session: AsyncSession,
    ) -> dict[str, object]:
        user_id = request.state.user_id
        try:
            changed = await order.transition(
                session,
                order_id=order_id,
                user_id=user_id,
                target=target,
                reason=payload.reason if payload else None,
            )
            await session.commit()
            return _result(order.payload(changed), "订单状态更新成功")
        except PermissionError as error:
            await session.rollback()
            raise _error(403, str(error)) from error
        except ValueError as error:
            await session.rollback()
            raise _error(4003, str(error)) from error

    @app.post("/api/dining/orders/{order_id}/confirm")
    async def confirm(
        order_id: int,
        request: Request,
        payload: TransitionRequest | None = None,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        return await transition_endpoint(order_id, "confirmed", request, payload, session)

    @app.post("/api/dining/orders/{order_id}/cancel")
    async def cancel(
        order_id: int,
        request: Request,
        payload: TransitionRequest | None = None,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        return await transition_endpoint(order_id, "cancelled", request, payload, session)

    @app.post("/api/dining/orders/{order_id}/cooking")
    @app.post("/api/dining/orders/{order_id}/start")
    async def cooking(
        order_id: int,
        request: Request,
        payload: TransitionRequest | None = None,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        return await transition_endpoint(order_id, "cooking", request, payload, session)

    @app.post("/api/dining/orders/{order_id}/complete")
    @app.post("/api/dining/orders/{order_id}/finish")
    async def complete(
        order_id: int,
        request: Request,
        payload: TransitionRequest | None = None,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        return await transition_endpoint(order_id, "completed", request, payload, session)

    @app.get("/api/dining/orders/{order_id}")
    async def order_detail(
        order_id: int,
        request: Request,
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id, couple_id = await context(request, session)
        row = await session.scalar(select(DiningOrder).where(DiningOrder.id == order_id))
        if row is None or (
            row.user_id != user_id and (couple_id is None or row.couple_id != couple_id)
        ):
            raise _error(4041, "订单不存在")
        items = list(
            (
                await session.scalars(
                    select(DiningOrderItem).where(DiningOrderItem.order_id == order_id)
                )
            ).all()
        )
        return _result(order.payload(row, items))

    @app.get("/api/dining/orders")
    async def order_list(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
        session: AsyncSession = _AUTHENTICATED_SESSION_DEPENDENCY,
    ) -> dict[str, object]:
        user_id, couple_id = await context(request, session)
        filters = (
            (DiningOrder.couple_id == couple_id)
            if couple_id is not None
            else (DiningOrder.user_id == user_id)
        )
        total = int(
            await session.scalar(select(func.count(DiningOrder.id)).where(filters)) or 0
        )
        rows = list(
            (
                await session.scalars(
                    select(DiningOrder)
                    .where(filters)
                    .order_by(DiningOrder.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        await logger.ainfo(
            "dining_orders_listed",
            requestId=request.state.request_id,
            module="dining",
            operation="order_list",
            result="success",
            userId=user_id,
            page=page,
            pageSize=page_size,
            total=total,
            returnedCount=len(rows),
        )
        return _result({"records": [order.payload(row) for row in rows], "total": total})

    return app


try:
    app = create_app()
except (RuntimeError, ValueError):
    app = FastAPI(title="Dining Service")

    @app.get("/health")
    async def health_unconfigured() -> dict[str, str]:
        return {"status": "ok", "service": "dining"}
