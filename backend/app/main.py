import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.ai import router as ai_router
from app.api.anniversary import router as anniversary_router
from app.api.cart import router as cart_router
from app.api.challenge import router as challenge_router
from app.api.couple import router as couple_router
from app.api.couple_rank import router as couple_rank_router
from app.api.couple_tree import router as couple_tree_router
from app.api.daily_greeting import router as daily_greeting_router
from app.api.daily_task import router as daily_task_router
from app.api.deep_qa import router as deep_qa_router
from app.api.feed import router as feed_router
from app.api.health import ready
from app.api.health import router as health_router
from app.api.heart_moment import router as heart_moment_router
from app.api.invite import router as invite_router
from app.api.love_calendar import router as love_calendar_router
from app.api.menu import router as menu_router
from app.api.mood import router as mood_router
from app.api.note import router as note_router
from app.api.notification import router as notification_router
from app.api.order import router as order_router
from app.api.recipe import router as recipe_router
from app.api.relationship_weather import router as relationship_weather_router
from app.api.sweet_bomb import router as sweet_bomb_router
from app.api.time_capsule import router as time_capsule_router
from app.api.upload import router as upload_router
from app.api.user import router as user_router
from app.api.wish import router as wish_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import Database
from app.redis.client import RedisClient
from app.services import feed as feed_service

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


async def _cancel_task(task: asyncio.Task[None]) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _feed_expiry_loop(database: Database) -> None:
    while True:
        await asyncio.sleep(600)
        try:
            async with database.session() as session:
                await feed_service.expire_due(session)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await _log_dependency_result("database", "expire_feeds", "failed", error)


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
                expiry_task = asyncio.create_task(_feed_expiry_loop(database))
                resources.push_async_callback(_cancel_task, expiry_task)
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
    app.mount(
        f"{active_settings.api_prefix}/uploads",
        StaticFiles(directory=active_settings.file_upload_path, check_dir=False),
        name="uploads",
    )
    app.include_router(health_router, prefix=active_settings.api_prefix)
    app.include_router(user_router, prefix=active_settings.api_prefix)
    app.include_router(couple_router, prefix=active_settings.api_prefix)
    app.include_router(couple_rank_router, prefix=active_settings.api_prefix)
    app.include_router(couple_tree_router, prefix=active_settings.api_prefix)
    app.include_router(daily_greeting_router, prefix=active_settings.api_prefix)
    app.include_router(daily_task_router, prefix=active_settings.api_prefix)
    app.include_router(deep_qa_router, prefix=active_settings.api_prefix)
    app.include_router(feed_router, prefix=active_settings.api_prefix)
    app.include_router(heart_moment_router, prefix=active_settings.api_prefix)
    app.include_router(invite_router, prefix=active_settings.api_prefix)
    app.include_router(mood_router, prefix=active_settings.api_prefix)
    app.include_router(anniversary_router, prefix=active_settings.api_prefix)
    app.include_router(cart_router, prefix=active_settings.api_prefix)
    app.include_router(challenge_router, prefix=active_settings.api_prefix)
    app.include_router(order_router, prefix=active_settings.api_prefix)
    app.include_router(love_calendar_router, prefix=active_settings.api_prefix)
    app.include_router(ai_router, prefix=active_settings.api_prefix)
    app.include_router(notification_router, prefix=active_settings.api_prefix)
    app.include_router(menu_router, prefix=active_settings.api_prefix)
    app.include_router(note_router, prefix=active_settings.api_prefix)
    app.include_router(recipe_router, prefix=active_settings.api_prefix)
    app.include_router(relationship_weather_router, prefix=active_settings.api_prefix)
    app.include_router(sweet_bomb_router, prefix=active_settings.api_prefix)
    app.include_router(time_capsule_router, prefix=active_settings.api_prefix)
    app.include_router(upload_router, prefix=active_settings.api_prefix)
    app.include_router(wish_router, prefix=active_settings.api_prefix)
    app.add_api_route(
        f"{active_settings.api_prefix}/actuator/health",
        ready,
        methods=["GET"],
        tags=["health"],
    )
    return app


app = create_app()
