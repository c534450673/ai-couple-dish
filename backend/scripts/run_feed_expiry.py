"""One-shot, opt-in Feed expiry shadow worker."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.session import Database
from app.services.feed import expire_due


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="一次性执行投喂过期 shadow worker")


async def _log(
    request_id: str, operation: str, result: str, started: float, error_code: str
) -> None:
    fields = {
        "requestId": request_id,
        "module": "feed_expiry",
        "operation": operation,
        "result": result,
        "durationMs": max(0, int((time.monotonic() - started) * 1000)),
        "errorCode": error_code,
    }
    method = structlog.get_logger().ainfo if error_code == "NONE" else structlog.get_logger().aerror
    await method("feed_expiry", **fields)


async def execute(settings: Settings) -> int:
    configure_logging(settings)
    started, request_id, exit_code = time.monotonic(), uuid.uuid4().hex, 1
    if not settings.fastapi_feed_expiry_enabled:
        await _log(request_id, "opt_in", "rejected_disabled", started, "FEED_EXPIRY_DISABLED")
        return 2
    database: Database | None = None
    try:
        database = Database(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        await database.connect()
        factory = async_sessionmaker(database.engine, expire_on_commit=False)
        async with factory() as session:
            try:
                count = await expire_due(session, request_id)
            except Exception:
                await session.rollback()
                raise
        await _log(request_id, "run", f"processed_{count}", started, "NONE")
        exit_code = 0
    except Exception:
        await _log(request_id, "run", "failed", started, "DEPENDENCY")
    finally:
        if database is not None:
            try:
                await database.close()
            except Exception:
                await _log(request_id, "database.close", "failed", started, "DEPENDENCY_CLOSE")
                exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return asyncio.run(execute(Settings()))


if __name__ == "__main__":
    sys.exit(main())
