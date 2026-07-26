"""One-shot shadow worker for Spring's CoupleCodeTask expiration reminder."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification, User

COUPLE_CODE_PREFIX = "couple:code:"
REVERSE_KEY_PREFIX = "couple:code:user:"
REMINDER_WINDOW_SECONDS = 86_400
MAX_USER_ID = 9_223_372_036_854_775_807
LOCK_KEY = "scheduler:couple-code-expiration-reminder:lock"
MARKER_KEY_PREFIX = "scheduler:couple-code-expiration-reminder:marker:"
COMPARE_AND_DELETE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""
COMPARE_AND_EXPIRE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""


class RedisSchedulerClient(Protocol):
    async def scan(
        self, cursor: int, *, match: str, count: int
    ) -> tuple[int, list[str] | list[bytes]]: ...

    async def ttl(self, key: str) -> int: ...

    async def hgetall(self, key: str) -> dict[str, str] | dict[bytes, bytes]: ...

    async def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool | None: ...

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> int: ...


class SchedulerLogger(Protocol):
    async def ainfo(self, event: str, **fields: object) -> None: ...

    async def aerror(self, event: str, **fields: object) -> None: ...


SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class CoupleCodeRunResult:
    status: str
    processed: int = 0
    skipped: int = 0
    duplicates: int = 0
    failed: int = 0


class CoupleCodeScheduler:
    """Scans expiring couple code hashes once without participating in web lifecycle."""

    def __init__(
        self,
        *,
        redis: RedisSchedulerClient,
        session_factory: SessionFactory,
        jwt_secret: str,
        lock_ttl_seconds: int,
        marker_ttl_seconds: int,
        clock: Callable[[], float] = time.time,
        logger: SchedulerLogger | None = None,
    ) -> None:
        self._redis = redis
        self._session_factory = session_factory
        self._jwt_secret = jwt_secret.encode("utf-8")
        self._lock_ttl_seconds = lock_ttl_seconds
        self._marker_ttl_seconds = marker_ttl_seconds
        self._clock = clock
        self._logger: SchedulerLogger = logger or structlog.get_logger()

    async def run(self) -> CoupleCodeRunResult:
        request_id = uuid.uuid4().hex
        started_at = self._clock()
        lock_token = uuid.uuid4().hex
        try:
            acquired = await self._redis.set(
                LOCK_KEY, lock_token, nx=True, ex=self._lock_ttl_seconds
            )
        except Exception:
            await self._log(request_id, "lock.acquire", "failed", started_at, "REDIS_LOCK")
            return CoupleCodeRunResult(status="failed", failed=1)
        if not acquired:
            await self._log(request_id, "run", "skipped_locked", started_at, "LOCKED")
            return CoupleCodeRunResult(status="skipped_locked")

        processed = skipped = duplicates = failed = 0
        try:
            cursor = 0
            while True:
                if not await self._renew_lock(lock_token):
                    return await self._lock_lost_result(
                        request_id, started_at, processed, skipped, duplicates, failed
                    )
                try:
                    cursor, keys = await self._redis.scan(
                        cursor, match=f"{COUPLE_CODE_PREFIX}*", count=100
                    )
                except Exception:
                    await self._log(request_id, "scan", "failed", started_at, "REDIS_SCAN")
                    return CoupleCodeRunResult(
                        status="failed",
                        processed=processed,
                        skipped=skipped,
                        duplicates=duplicates,
                        failed=failed + 1,
                    )
                for raw_key in keys:
                    if not await self._renew_lock(lock_token):
                        return await self._lock_lost_result(
                            request_id, started_at, processed, skipped, duplicates, failed
                        )
                    key = self._as_text(raw_key)
                    if key is None or key.startswith(REVERSE_KEY_PREFIX):
                        skipped += 1
                        continue
                    outcome = await self._process_key(key, request_id, started_at, lock_token)
                    if outcome == "processed":
                        processed += 1
                    elif outcome == "duplicate":
                        duplicates += 1
                    elif outcome == "failed":
                        failed += 1
                    else:
                        skipped += 1
                if cursor == 0:
                    break
            status = "completed" if failed == 0 else "completed_with_errors"
            result = CoupleCodeRunResult(status, processed, skipped, duplicates, failed)
            await self._log(
                request_id,
                "run",
                self._summary(result),
                started_at,
                "NONE" if failed == 0 else "ITEM_FAILURE",
            )
            return result
        finally:
            try:
                await self._compare_and_delete(LOCK_KEY, lock_token)
            except Exception:
                await self._log(request_id, "lock.release", "failed", started_at, "REDIS_LOCK")

    async def _process_key(
        self, key: str, request_id: str, started_at: float, marker_token: str
    ) -> str:
        """Re-check the hash immediately before DB work to tolerate bind/delete races."""
        marker_key: str | None = None
        marker_owned = False
        try:
            ttl = await self._redis.ttl(key)
            if ttl < 0 or ttl >= REMINDER_WINDOW_SECONDS:
                return "skipped"
            code = key.removeprefix(COUPLE_CODE_PREFIX)
            if not code:
                return "skipped"
            expiry_hour = int((self._clock() + ttl) // 3600)
            marker_key = self._marker_key(code, expiry_hour)
            marked = await self._redis.set(
                marker_key, marker_token, nx=True, ex=self._marker_ttl_seconds
            )
            if not marked:
                return "duplicate"
            marker_owned = True
            # SCAN is not a snapshot. Re-read after acquiring the marker and immediately
            # before DB work so a Spring bind/delete cannot create a stale notification.
            ttl = await self._redis.ttl(key)
            if ttl < 0 or ttl >= REMINDER_WINDOW_SECONDS:
                await self._compare_and_delete(marker_key, marker_token)
                return "skipped"
            values = await self._redis.hgetall(key)
            user_id = self._valid_user_id(self._mapping_value(values, "userId"))
            if user_id is None:
                await self._compare_and_delete(marker_key, marker_token)
                return "skipped"
        except Exception:
            if marker_owned and marker_key is not None:
                try:
                    await self._compare_and_delete(marker_key, marker_token)
                except Exception:
                    await self._log(
                        request_id, "item.marker_cleanup", "failed", started_at, "REDIS_MARKER"
                    )
            await self._log(request_id, "item.prepare", "failed", started_at, "REDIS_ITEM")
            return "failed"

        if marker_key is None:
            await self._log(request_id, "item.prepare", "failed", started_at, "MARKER_STATE")
            return "failed"
        session: AsyncSession | None = None
        try:
            async with self._session_factory() as session:
                user = await session.scalar(
                    select(User).where(User.id == user_id).with_for_update()
                )
                if user is None or user.couple_id is not None:
                    await session.rollback()
                    await self._compare_and_delete(marker_key, marker_token)
                    return "skipped"
                notification = Notification(
                    user_id=user_id,
                    type=2,
                    title="⏰ 情侣码即将过期",
                    content=f"您的情侣码 {code} 将在 {ttl // 3600} 小时后过期，请尽快分享给TA绑定",
                    related_id=None,
                    related_type="couple_code",
                    sender_id=None,
                    is_read=0,
                )
                session.add(notification)
                await session.commit()
        except Exception:
            if session is not None:
                try:
                    await session.rollback()
                except Exception:
                    await self._log(
                        request_id, "item.rollback", "failed", started_at, "DATABASE_ROLLBACK"
                    )
            try:
                await self._compare_and_delete(marker_key, marker_token)
            except Exception:
                await self._log(
                    request_id, "item.marker_cleanup", "failed", started_at, "REDIS_MARKER"
                )
            await self._log(request_id, "item.persist", "failed", started_at, "DATABASE")
            return "failed"

        await self._log(request_id, "item.persist", "processed_1", started_at, "NONE")
        return "processed"

    def _marker_key(self, code: str, expiry_hour: int) -> str:
        digest = hmac.new(self._jwt_secret, code.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{MARKER_KEY_PREFIX}{digest}:{expiry_hour}"

    async def _compare_and_delete(self, key: str, token: str) -> None:
        await self._redis.eval(COMPARE_AND_DELETE_LUA, 1, key, token)

    async def _renew_lock(self, token: str) -> bool:
        try:
            renewed = await self._redis.eval(
                COMPARE_AND_EXPIRE_LUA, 1, LOCK_KEY, token, str(self._lock_ttl_seconds)
            )
        except Exception:
            return False
        return bool(renewed)

    async def _lock_lost_result(
        self,
        request_id: str,
        started_at: float,
        processed: int,
        skipped: int,
        duplicates: int,
        failed: int,
    ) -> CoupleCodeRunResult:
        await self._log(request_id, "lock.renew", "failed_lost", started_at, "LOCK_LOST")
        return CoupleCodeRunResult(
            status="failed",
            processed=processed,
            skipped=skipped,
            duplicates=duplicates,
            failed=failed + 1,
        )

    async def _log(
        self,
        request_id: str,
        operation: str,
        result: str,
        started_at: float,
        error_code: str,
    ) -> None:
        fields = {
            "requestId": request_id,
            "module": "couple_code_scheduler",
            "operation": operation,
            "result": result,
            "durationMs": max(0, int((self._clock() - started_at) * 1000)),
            "errorCode": error_code,
        }
        if error_code == "NONE":
            await self._logger.ainfo("couple_code_scheduler", **fields)
        else:
            await self._logger.aerror("couple_code_scheduler", **fields)

    @staticmethod
    def _as_text(value: str | bytes) -> str | None:
        if isinstance(value, str):
            return value
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @classmethod
    def _mapping_value(cls, values: dict[str, str] | dict[bytes, bytes], name: str) -> str | None:
        for raw_key, raw_value in values.items():
            if cls._as_text(raw_key) == name:
                return cls._as_text(raw_value)
        return None

    @staticmethod
    def _valid_user_id(value: str | None) -> int | None:
        if value is None or not value.isascii() or not value.isdigit():
            return None
        parsed = int(value)
        if parsed <= 0 or parsed > MAX_USER_ID:
            return None
        return parsed

    @staticmethod
    def _summary(result: CoupleCodeRunResult) -> str:
        return (
            f"processed_{result.processed}_skipped_{result.skipped}_"
            f"duplicate_{result.duplicates}_failed_{result.failed}"
        )
