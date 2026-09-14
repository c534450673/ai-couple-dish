"""Opt-in task worker with one lock per job."""

from __future__ import annotations

import os
import secrets
from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import uuid4

import structlog
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from packages.platform.service import create_service_app

logger = structlog.get_logger()


class Job(BaseModel):
    job: str = Field(min_length=1, max_length=128)


class LockBackend(Protocol):
    async def acquire(self, key: str, token: str, ttl_seconds: int) -> bool: ...
    async def release(self, key: str, token: str) -> bool: ...


class RedisClient(Protocol):
    async def set(self, key: str, value: str, *, nx: bool, ex: int) -> object: ...

    async def eval(self, script: str, numkeys: int, key: str, token: str) -> object: ...


class InMemoryLease:
    """Deterministic fallback used only when REDIS_HOST is absent (unit tests)."""

    def __init__(self) -> None:
        self._locks: dict[str, str] = {}

    async def acquire(self, key: str, token: str, ttl_seconds: int) -> bool:
        del ttl_seconds
        if key in self._locks:
            return False
        self._locks[key] = token
        return True

    async def release(self, key: str, token: str) -> bool:
        if self._locks.get(key) != token:
            return False
        del self._locks[key]
        return True


class RedisLease:
    def __init__(self, client: RedisClient) -> None:
        self.client = client

    async def acquire(self, key: str, token: str, ttl_seconds: int) -> bool:
        return bool(await self.client.set(key, token, nx=True, ex=ttl_seconds))

    async def release(self, key: str, token: str) -> bool:
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        return bool(await self.client.eval(script, 1, key, token))


def _lock_backend() -> LockBackend:
    host = os.getenv("REDIS_HOST")
    if not host:
        return InMemoryLease()
    try:
        import redis.asyncio as redis

        return RedisLease(
            redis.Redis(host=host, port=int(os.getenv("REDIS_PORT", "6379")), decode_responses=True)
        )
    except Exception as error:
        logger.error(
            "worker_redis_init_failed",
            module="worker",
            operation="lock_init",
            result="error",
            errorCode=type(error).__name__,
        )
        raise RuntimeError("Redis lock backend unavailable") from error


JobHandler = Callable[[], Awaitable[object]]


def create_app(
    *,
    enabled: bool | None = None,
    lock_backend: LockBackend | None = None,
    handlers: dict[str, JobHandler] | None = None,
) -> FastAPI:
    app = create_service_app("worker")
    is_enabled = (
        enabled if enabled is not None else os.getenv("WORKER_ENABLED", "false").lower() == "true"
    )
    backend = lock_backend or _lock_backend()
    app.state.lock_backend = backend

    @app.post("/api/worker/run")
    async def run(
        payload: Job, x_worker_token: str | None = Header(default=None)
    ) -> dict[str, object]:
        if not is_enabled:
            logger.info("worker_disabled", module="worker", operation=payload.job, result="skipped")
            raise HTTPException(
                status_code=503, detail={"code": 503, "message": "Worker未启用", "data": None}
            )
        trigger_token = os.getenv("WORKER_TRIGGER_TOKEN")
        if (
            not trigger_token
            or not x_worker_token
            or not secrets.compare_digest(trigger_token, x_worker_token)
        ):
            raise HTTPException(
                status_code=403, detail={"code": 403, "message": "无任务权限", "data": None}
            )
        handler = (handlers or {}).get(payload.job)
        if handler is None:
            raise HTTPException(
                status_code=503, detail={"code": 503, "message": "任务未配置", "data": None}
            )
        key = f"ai-couple-dish:worker:{payload.job}"
        token = uuid4().hex
        try:
            acquired = await backend.acquire(key, token, int(os.getenv("WORKER_LOCK_TTL", "300")))
        except Exception as error:
            logger.error(
                "worker_lock_failed",
                module="worker",
                operation=payload.job,
                result="error",
                errorCode=type(error).__name__,
            )
            raise HTTPException(
                status_code=503, detail={"code": 503, "message": "任务锁不可用", "data": None}
            ) from error
        if not acquired:
            logger.info("worker_lock_busy", module="worker", operation=payload.job, result="busy")
            raise HTTPException(
                status_code=409, detail={"code": 409, "message": "任务已在运行", "data": None}
            )
        logger.info(
            "worker_lock_acquired", module="worker", operation=payload.job, result="started"
        )
        try:
            await handler()
            logger.info(
                "worker_job_completed", module="worker", operation=payload.job, result="success"
            )
            return {
                "code": 200,
                "message": "操作成功",
                "data": {"job": payload.job, "completed": True},
            }
        finally:
            released = await backend.release(key, token)
            logger.info(
                "worker_lock_released",
                module="worker",
                operation=payload.job,
                result="success" if released else "stale",
            )

    return app


app = create_app()
