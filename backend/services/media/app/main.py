from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import Database
from packages.platform.logging import configure_logging
from packages.platform.service import create_service_app

from .api.upload import router as upload_router
from .services.storage import Storage

logger = structlog.get_logger()
SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def create_app(
    *,
    session_provider: SessionProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """创建媒体服务，并为上传事务接入共享数据库会话。"""

    active_settings = settings
    if active_settings is None:
        try:
            active_settings = get_settings()
        except Exception:
            # import/OpenAPI 工具和单元测试可在未注入生产密钥时加载模块；
            # 真正的上传请求会明确返回 503，而不会回退到进程内元数据。
            active_settings = None

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
        configure_logging(active_settings)
        try:
            await database.connect()
            await logger.ainfo(
                "media_dependencies_connected",
                module="media",
                operation="startup",
                result="success",
                dependencies=["database"],
            )
            yield
        finally:
            await database.close()
            await logger.ainfo(
                "media_dependencies_closed",
                module="media",
                operation="shutdown",
                result="success",
                dependencies=["database"],
            )

    app = create_service_app("media", settings=active_settings)
    app.router.lifespan_context = lifespan
    app.state.settings = active_settings
    app.state.session_provider = session_provider
    app.state.storage = Storage()
    app.include_router(upload_router)
    return app


app = create_app()
