import logging
import sys
from collections.abc import MutableMapping
from typing import Any, TextIO

import structlog

from app.core.config import Settings

ALLOWED_FIELDS = {
    "timestamp",
    "level",
    "event",
    "requestId",
    "service",
    "release",
    "module",
    "operation",
    "result",
    "durationMs",
    "method",
    "route",
    "status",
    "errorCode",
    "dependency",
}
POSTER_LOG_FIELDS = (
    "requestId",
    "module",
    "operation",
    "result",
    "durationMs",
    "errorCode",
)
SCHEDULER_LOG_FIELDS = (
    "requestId",
    "module",
    "operation",
    "result",
    "durationMs",
    "errorCode",
)


def sanitize_event(event: MutableMapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key in ALLOWED_FIELDS}


def allowlist_processor(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> dict[str, Any]:
    sanitized = sanitize_event(event_dict)
    if sanitized.get("module") == "poster":
        return {key: sanitized[key] for key in POSTER_LOG_FIELDS if key in sanitized}
    if sanitized.get("module") == "couple_code_scheduler":
        return {key: sanitized[key] for key in SCHEDULER_LOG_FIELDS if key in sanitized}
    return sanitized


def configure_logging(settings: Settings, *, stream: TextIO = sys.stdout) -> None:
    logging.basicConfig(
        stream=stream,
        level=settings.log_level.upper(),
        format="%(message)s",
        force=True,
    )

    def add_service_metadata(
        _logger: Any,
        _method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        event_dict["service"] = settings.service_name
        event_dict["release"] = settings.release_sha
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_service_metadata,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.add_log_level,
            allowlist_processor,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
