"""菜品目录微服务 HTTP 边界。"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from fastapi import Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import Database
from packages.platform.admin_auth import require_admin
from packages.platform.catalog import Dish
from packages.platform.logging import configure_logging

from .services.catalog import (
    CatalogDishPage,
    CatalogNotFoundError,
    CatalogNotPublishableError,
    CatalogStore,
    SqlAlchemyCatalogStore,
)

logger = structlog.get_logger()
SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class SourceReviewRequest(BaseModel):
    approved: bool


def _envelope(data: object) -> dict[str, object]:
    return {"code": 200, "message": "操作成功", "data": data}


def _price_payload(price: Decimal | None) -> str | None:
    return str(price) if price is not None else None


def _dish_payload(dish: Dish, *, include_sources: bool = False) -> dict[str, object]:
    data: dict[str, object] = {
        "id": dish.id,
        "dishId": dish.id,
        "slug": dish.slug,
        "name": dish.name,
        "cuisine": dish.cuisine,
        "tags": list(dish.tags),
        "spicyLevel": dish.spicy_level,
        "allergens": list(dish.allergens),
        "status": dish.status,
        "imageUrl": dish.image_url,
        "unitPrice": _price_payload(dish.unit_price),
        "price": _price_payload(dish.unit_price),
    }
    if include_sources:
        data["sources"] = list(dish.sources)
    return data


@asynccontextmanager
async def _session_scope(request: Request) -> AsyncIterator[AsyncSession]:
    provider: SessionProvider | None = getattr(request.app.state, "session_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503, detail={"code": 503, "message": "菜品目录未就绪", "data": None}
        )
    async with provider() as session:
        yield session


async def _rollback(
    session: AsyncSession, request: Request, *, operation: str, error: BaseException
) -> None:
    await session.rollback()
    await logger.aerror(
        "catalog_transaction_rolled_back",
        requestId=request.state.request_id,
        module="catalog",
        operation=operation,
        result="error",
        errorCode=type(error).__name__,
    )


def create_app(
    *,
    session_provider: SessionProvider | None = None,
    store: CatalogStore | None = None,
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
        application.state.settings = active_settings
        application.state.session_provider = database.session
        configure_logging(active_settings)
        try:
            await database.connect()
            await logger.ainfo(
                "catalog_dependencies_connected",
                module="catalog",
                operation="startup",
                result="success",
                dependencies=["database"],
            )
            yield
        finally:
            await database.close()
            await logger.ainfo(
                "catalog_dependencies_closed",
                module="catalog",
                operation="shutdown",
                result="success",
                dependencies=["database"],
            )

    app = FastAPI(title="Catalog Service", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_provider = session_provider
    app.state.store = store or SqlAlchemyCatalogStore()

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        request.state.request_id = request.headers.get("X-Request-ID") or secrets.token_hex(16)
        started = datetime.now()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        await logger.ainfo(
            "catalog_request_completed",
            requestId=request.state.request_id,
            module="catalog",
            operation=request.url.path,
            result="success" if response.status_code < 400 else "rejected",
            status=response.status_code,
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
    @app.get("/health/live")
    async def health() -> dict[str, object]:
        return _envelope({"status": "UP", "service": "catalog"})

    @app.get("/health/ready")
    @app.get("/actuator/health")
    async def readiness() -> JSONResponse:
        ready = app.state.session_provider is not None
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "code": 200 if ready else 503,
                "message": "操作成功" if ready else "服务暂不可用",
                "data": {"status": "UP" if ready else "DOWN", "service": "catalog"},
            },
        )

    @app.get("/api/catalog/cuisines")
    async def cuisines(request: Request) -> dict[str, object]:
        async with _session_scope(request) as session:
            try:
                data = await app.state.store.list_cuisines(session)
            except SQLAlchemyError as error:
                await logger.aerror(
                    "catalog_read_failed",
                    requestId=request.state.request_id,
                    module="catalog",
                    operation="list_cuisines",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
                ) from error
        return _envelope(data)

    @app.get("/api/catalog/dishes")
    async def dishes(
        request: Request,
        cuisine: str | None = Query(default=None),
        keyword: str | None = Query(default=None),
        tag: str | None = Query(default=None),
        spicy_level: int | None = Query(default=None, alias="spicyLevel", ge=0, le=5),
        allergen: str | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    ) -> dict[str, object]:
        async with _session_scope(request) as session:
            try:
                listed = await app.state.store.list_dishes(
                    session,
                    cuisine=cuisine,
                    keyword=keyword,
                    tag=tag,
                    spicy_level=spicy_level,
                    allergen=allergen,
                    page=page,
                    page_size=page_size,
                )
            except SQLAlchemyError as error:
                await logger.aerror(
                    "catalog_read_failed",
                    requestId=request.state.request_id,
                    module="catalog",
                    operation="list_dishes",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
                ) from error
        if isinstance(listed, CatalogDishPage):
            matched = listed.items
            total = listed.total
        else:
            # 兼容测试替身和迁移期实现：生产 SQL 存储始终返回有界页面。
            start = (page - 1) * page_size
            matched = listed[start : start + page_size]
            total = len(listed)
        data = [_dish_payload(dish) for dish in matched]
        await logger.ainfo(
            "catalog_dishes_listed",
            requestId=request.state.request_id,
            module="catalog",
            operation="list_dishes",
            result="success",
            matchedCount=total,
            returnedCount=len(data),
        )
        return _envelope(
            {"items": data, "page": page, "pageSize": page_size, "total": total}
        )

    @app.get("/api/catalog/dishes/{dish_reference}")
    async def dish_detail(dish_reference: str, request: Request) -> dict[str, object]:
        async with _session_scope(request) as session:
            try:
                dish = await app.state.store.get_published_dish(session, dish_reference)
            except SQLAlchemyError as error:
                await logger.aerror(
                    "catalog_read_failed",
                    requestId=request.state.request_id,
                    module="catalog",
                    operation="dish_detail",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "菜品目录暂不可用", "data": None},
                ) from error
        if dish is None:
            await logger.awarning(
                "catalog_dish_access_rejected",
                requestId=request.state.request_id,
                module="catalog",
                operation="dish_detail",
                result="not_found",
                dishReference=dish_reference,
            )
            raise HTTPException(
                status_code=404, detail={"code": 404, "message": "菜品不存在", "data": None}
            )
        return _envelope(_dish_payload(dish, include_sources=True))

    @app.post("/api/catalog/import")
    async def import_catalog(
        request: Request,
        payload: list[dict[str, object]] = Body(...),  # noqa: B008
        source_name: str | None = Header(default=None, alias="X-Catalog-Import-Source"),
    ) -> dict[str, object]:
        require_admin(request)
        safe_source_name = source_name.strip() if source_name else "catalog-api"
        if not safe_source_name or len(safe_source_name) > 128:
            raise HTTPException(
                status_code=422, detail={"code": 422, "message": "导入来源无效", "data": None}
            )
        async with _session_scope(request) as session:
            try:
                result = await app.state.store.import_catalog(
                    session, payload, source_name=safe_source_name
                )
                await session.commit()
            except SQLAlchemyError as error:
                await _rollback(session, request, operation="import", error=error)
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "菜品导入失败", "data": None},
                ) from error
        return _envelope(result)

    @app.post("/api/catalog/dishes/{dish_reference}/sources/{source_id}/review")
    async def review_source(
        dish_reference: str, source_id: int, payload: SourceReviewRequest, request: Request
    ) -> dict[str, object]:
        require_admin(request)
        async with _session_scope(request) as session:
            try:
                result = await app.state.store.review_source(
                    session,
                    dish_reference=dish_reference,
                    source_id=source_id,
                    approved=payload.approved,
                )
                await session.commit()
            except CatalogNotFoundError as error:
                await session.rollback()
                raise HTTPException(
                    status_code=404, detail={"code": 404, "message": str(error), "data": None}
                ) from error
            except SQLAlchemyError as error:
                await _rollback(session, request, operation="review_source", error=error)
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "审核保存失败", "data": None},
                ) from error
        return _envelope(result)

    @app.post("/api/catalog/dishes/{dish_reference}/publish")
    async def publish_dish(dish_reference: str, request: Request) -> dict[str, object]:
        require_admin(request)
        async with _session_scope(request) as session:
            try:
                result = await app.state.store.publish_dish(session, dish_reference=dish_reference)
                await session.commit()
            except CatalogNotFoundError as error:
                await session.rollback()
                raise HTTPException(
                    status_code=404, detail={"code": 404, "message": str(error), "data": None}
                ) from error
            except CatalogNotPublishableError as error:
                await session.rollback()
                await logger.awarning(
                    "catalog_publish_rejected",
                    requestId=request.state.request_id,
                    module="catalog",
                    operation="publish",
                    result="rejected",
                    dishReference=dish_reference,
                    errorCode="CATALOG_DISH_NOT_PUBLISHABLE",
                )
                raise HTTPException(
                    status_code=422, detail={"code": 422, "message": str(error), "data": None}
                ) from error
            except SQLAlchemyError as error:
                await _rollback(session, request, operation="publish", error=error)
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "菜品发布失败", "data": None},
                ) from error
        return _envelope(result)

    return app


app = create_app()
