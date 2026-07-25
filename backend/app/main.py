import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.couple import router as couple_router
from app.api.health import ready
from app.api.health import router as health_router
from app.api.notification import router as notification_router
from app.api.user import router as user_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import Database
from app.redis.client import RedisClient

logger = structlog.get_logger()


async def default_readiness() -> dict[str, bool]:
    """在外部依赖初始化前提供应用级就绪状态。"""
    return {"application": True}


async def _log_dependency_result(
    dependency: str,
    operation: str,
    result: str,
    error: BaseException | None = None,
) -> None:
    fields: dict[str, Any] = {
        "module": "application",
        "dependency": dependency,
        "operation": operation,
        "result": result,
    }
    if error is not None:
        fields["errorCode"] = type(error).__name__
        await logger.aerror("dependency_operation_failed", **fields)
        return
    await logger.ainfo("dependency_operation_completed", **fields)


async def _close_dependency(dependency: str, resource: Database | RedisClient) -> None:
    try:
        await resource.close()
    except Exception as error:
        await _log_dependency_result(dependency, "close", "failed", error)
    else:
        await _log_dependency_result(dependency, "close", "completed")


def create_app(settings: Settings | None = None) -> FastAPI:
    """根据传入配置创建 FastAPI 应用。"""
    active_settings = settings or get_settings()
    configure_logging(active_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = active_settings
        try:
            async with AsyncExitStack() as resources:
                database = Database(
                    active_settings.database_url,
                    pool_size=active_settings.database_pool_size,
                    max_overflow=active_settings.database_max_overflow,
                )
                resources.push_async_callback(_close_dependency, "database", database)
                redis_client = RedisClient(active_settings.redis_url)
                resources.push_async_callback(_close_dependency, "redis", redis_client)
                app.state.db = database
                app.state.redis = redis_client

                async def readiness() -> dict[str, bool]:
                    results = await asyncio.gather(
                        database.ping(),
                        redis_client.ping(),
                        return_exceptions=True,
                    )
                    return {
                        "database": not isinstance(results[0], BaseException) and bool(results[0]),
                        "redis": not isinstance(results[1], BaseException) and bool(results[1]),
                    }

                app.state.readiness = readiness
                try:
                    await database.connect()
                except Exception as error:
                    await _log_dependency_result("database", "connect", "failed", error)
                    raise
                await _log_dependency_result("database", "connect", "completed")

                try:
                    await redis_client.connect()
                except Exception as error:
                    await _log_dependency_result("redis", "connect", "failed", error)
                    raise
                await _log_dependency_result("redis", "connect", "completed")
                await logger.ainfo(
                    "application_started",
                    module="application",
                    operation="lifespan",
                    result="started",
                )
                yield
        finally:
            await logger.ainfo(
                "application_stopped",
                module="application",
                operation="lifespan",
                result="stopped",
            )

    app = FastAPI(
        title="AI Couple Dish API",
        docs_url=None if active_settings.app_env == "prod" else "/api/docs",
        openapi_url=None if active_settings.app_env == "prod" else "/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.readiness = default_readiness
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["Authorization", "Content-Disposition", "X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    install_exception_handlers(app)
    app.include_router(health_router, prefix=active_settings.api_prefix)
    app.include_router(user_router, prefix=active_settings.api_prefix)
    app.include_router(couple_router, prefix=active_settings.api_prefix)
    app.include_router(notification_router, prefix=active_settings.api_prefix)
    app.add_api_route(
        f"{active_settings.api_prefix}/actuator/health",
        ready,
        methods=["GET"],
        tags=["health"],
    )
    return app


app = create_app()
