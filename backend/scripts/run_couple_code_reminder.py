"""The only supported entry point for the opt-in couple code reminder worker."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid

import structlog

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.session import Database
from app.redis.client import RedisClient
from app.services.couple_code_scheduler import CoupleCodeScheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一次性执行情侣码过期提醒 shadow worker")
    parser.add_argument("--version", action="version", version="couple-code-reminder")
    return parser


async def execute(settings: Settings) -> int:
    """Connect dependencies, run once, and close all resources before returning an exit code."""
    configure_logging(settings)
    started_at = time.monotonic()
    request_id = uuid.uuid4().hex
    if not settings.fastapi_scheduler_enabled:
        await _log_result(
            request_id, "opt_in", "rejected_disabled", started_at, "SCHEDULER_DISABLED"
        )
        return 2
    database: Database | None = None
    redis: RedisClient | None = None
    try:
        database = Database(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        redis = RedisClient(settings.redis_url)
        await database.connect()
        await redis.connect()
        worker = CoupleCodeScheduler(
            redis=redis.raw,
            session_factory=database.session,
            jwt_secret=settings.jwt_secret.get_secret_value(),
            lock_ttl_seconds=settings.couple_code_scheduler_lock_ttl_seconds,
            marker_ttl_seconds=settings.couple_code_scheduler_marker_ttl_seconds,
        )
        result = await worker.run()
        exit_code = 0 if result.status in {"completed", "skipped_locked"} else 1
        await _log_result(
            request_id,
            "run",
            result.status,
            started_at,
            "NONE" if not exit_code else "RUN_FAILED",
        )
        return exit_code
    except Exception:
        await _log_result(request_id, "run", "failed", started_at, "DEPENDENCY")
        return 1
    finally:
        if redis is not None:
            try:
                await redis.close()
            except Exception:
                await _log_result(
                    request_id, "redis.close", "failed", started_at, "DEPENDENCY_CLOSE"
                )
        if database is not None:
            try:
                await database.close()
            except Exception:
                await _log_result(
                    request_id, "database.close", "failed", started_at, "DEPENDENCY_CLOSE"
                )


async def _log_result(
    request_id: str, operation: str, result: str, started_at: float, error_code: str
) -> None:
    logger = structlog.get_logger()
    fields = {
        "requestId": request_id,
        "module": "couple_code_scheduler",
        "operation": operation,
        "result": result,
        "durationMs": max(0, int((time.monotonic() - started_at) * 1000)),
        "errorCode": error_code,
    }
    if error_code == "NONE":
        await logger.ainfo("couple_code_scheduler", **fields)
        return
    await logger.aerror(
        "couple_code_scheduler",
        **fields,
    )


def main(argv: list[str] | None = None) -> int:
    # argparse must handle --help before Settings validates secrets or dependencies are touched.
    build_parser().parse_args(argv)
    return asyncio.run(execute(Settings()))


if __name__ == "__main__":
    sys.exit(main())
