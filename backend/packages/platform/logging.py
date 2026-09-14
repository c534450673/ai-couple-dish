import logging
import sys
from collections.abc import MutableMapping
from typing import Any, TextIO

import structlog

_ALLOWED = {
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
    "errorCode",
    "route",
    "status",
    "method",
    "dependency",
}


def configure_logging(settings: Any, *, stream: TextIO = sys.stdout) -> None:
    logging.basicConfig(
        stream=stream,
        level=getattr(logging, str(settings.log_level).upper(), logging.INFO),
        format="%(message)s",
        force=True,
    )

    def metadata(
        _logger: Any, _method: str, event: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event["service"] = settings.service_name
        event["release"] = settings.release_sha
        return event

    def allowlist(_logger: Any, _method: str, event: MutableMapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in event.items() if k in _ALLOWED}

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            metadata,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.add_log_level,
            allowlist,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
