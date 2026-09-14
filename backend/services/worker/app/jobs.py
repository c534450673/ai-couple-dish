"""独立 worker 作业入口；不会在 FastAPI lifespan 中自动启动。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

logger = structlog.get_logger()

JOB_NAMES = ("couple_code_reminder", "feed_expiry", "report_aggregation", "image_cleanup")
JobHandler = Callable[[], Awaitable[dict[str, Any]]]


async def run_job(name: str, handler: JobHandler) -> dict[str, Any]:
    if name not in JOB_NAMES:
        raise ValueError(f"unknown worker job: {name}")
    result = await handler()
    logger.info("worker_job_completed", module="worker", operation=name, result="success")
    return result
