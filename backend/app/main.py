from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import ready
from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware

logger = structlog.get_logger()


async def default_readiness() -> dict[str, bool]:
    """在外部依赖初始化前提供应用级就绪状态。"""
    return {"application": True}


def create_app(settings: Settings | None = None) -> FastAPI:
    """根据传入配置创建 FastAPI 应用。"""
    active_settings = settings or get_settings()
    configure_logging(active_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = active_settings
        await logger.ainfo(
            "application_started",
            module="application",
            operation="lifespan",
            result="started",
        )
        try:
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
    app.add_api_route(
        f"{active_settings.api_prefix}/actuator/health",
        ready,
        methods=["GET"],
        tags=["health"],
    )
    return app


app = create_app()
