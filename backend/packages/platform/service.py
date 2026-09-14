"""Shared application wiring for the Python microservices.

The service entry points intentionally stay thin.  This module owns the small
amount of cross-service HTTP behaviour that must remain identical: settings
and structured logging setup, plus liveness/readiness/actuator envelopes.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from packages.platform.config import Settings, get_settings
from packages.platform.logging import configure_logging

ReadinessCheck = Callable[[], Awaitable[bool | dict[str, bool]]]


def _health_envelope(*, service: str, status: str, code: int) -> dict[str, Any]:
    """Build the stable result envelope used by every service health route."""

    return {
        "code": code,
        "message": "操作成功" if code == 200 else "服务暂不可用",
        "data": {"status": status, "service": service},
    }


def _settings_for_service(service_name: str, settings: Settings | None) -> Settings | None:
    """Load shared settings without making import-only tooling require secrets.

    Production and normal runtime startup still validates all required settings.
    The narrow fallback only allows a module import (for e.g. OpenAPI tooling)
    before environment variables are injected; no synthetic secret is created.
    """

    if settings is not None:
        return settings.model_copy(update={"service_name": service_name})
    try:
        loaded = get_settings()
    except ValidationError:
        return None
    return loaded.model_copy(update={"service_name": service_name})


def create_service_app(
    service_name: str,
    *,
    settings: Settings | None = None,
    readiness: ReadinessCheck | None = None,
) -> FastAPI:
    """Create a service app with the shared configuration and health contract."""

    active_settings = _settings_for_service(service_name, settings)
    if active_settings is not None:
        configure_logging(active_settings)
    logger = structlog.get_logger()

    async def default_readiness() -> bool:
        return True

    check = readiness or default_readiness
    app = FastAPI(title=f"{service_name.title()} Service")
    app.state.settings = active_settings
    app.state.readiness = check

    async def live() -> JSONResponse:
        payload = _health_envelope(service=service_name, status="UP", code=200)
        logger.info(
            "service_health",
            module="health",
            operation="live",
            result="ok",
            status="UP",
        )
        return JSONResponse(status_code=200, content=payload)

    async def ready() -> JSONResponse:
        try:
            result = await check()
            is_ready = result if isinstance(result, bool) else all(result.values())
        except Exception as error:  # readiness must never expose dependency details
            is_ready = False
            logger.warning(
                "service_health",
                module="health",
                operation="ready",
                result="error",
                errorCode=type(error).__name__,
            )
        code = 200 if is_ready else 503
        status = "UP" if is_ready else "DOWN"
        logger.info(
            "service_health",
            module="health",
            operation="ready",
            result="ok" if is_ready else "unavailable",
            status=status,
        )
        return JSONResponse(
            status_code=code,
            content=_health_envelope(service=service_name, status=status, code=code),
        )

    app.add_api_route("/health", live, methods=["GET"], tags=["health"])
    app.add_api_route("/health/live", live, methods=["GET"], tags=["health"])
    app.add_api_route("/health/ready", ready, methods=["GET"], tags=["health"])
    app.add_api_route("/actuator/health", ready, methods=["GET"], tags=["health"])
    return app


__all__ = ["ReadinessCheck", "create_service_app"]
