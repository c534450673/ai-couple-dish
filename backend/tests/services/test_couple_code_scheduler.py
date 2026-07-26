import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from io import StringIO

import pytest
import structlog

from app.core.config import Settings
from app.core.logging import configure_logging
from app.services.couple_code_scheduler import CoupleCodeScheduler


@dataclass
class FakeSession:
    notifications: list[object]
    fail_commit: bool = False
    commits: int = 0
    rollbacks: int = 0

    def add(self, notification: object) -> None:
        self.notifications.append(notification)

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("database unavailable")
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeRedis:
    def __init__(self, values: dict[str, tuple[int, dict[str, str]]]) -> None:
        self.values = values
        self.values["couple:code:user:99"] = (86_399, {})
        self.strings: dict[str, tuple[str, int]] = {}
        self.scan_calls: list[tuple[int, str, int]] = []
        self.deleted: list[str] = []
        self.locked = False
        self.fail_ttl_keys: set[str] = set()

    async def scan(self, cursor: int, *, match: str, count: int) -> tuple[int, list[str]]:
        self.scan_calls.append((cursor, match, count))
        keys = list(self.values)
        if cursor == 0:
            return (1 if len(keys) > 2 else 0, keys[:2])
        return 0, keys[2:]

    async def ttl(self, key: str) -> int:
        if key in self.fail_ttl_keys:
            raise RuntimeError("redis ttl failed")
        return self.values.get(key, (-2, {}))[0]

    async def hgetall(self, key: str) -> dict[str, str]:
        return self.values.get(key, (-2, {}))[1]

    async def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool | None:
        await asyncio.sleep(0)
        if key.endswith(":lock") and self.locked:
            return None
        if nx and key in self.strings:
            return None
        self.strings[key] = (value, ex)
        return True

    async def eval(self, _script: str, _keys: int, key: str, value: str) -> int:
        if self.strings.get(key, (None, 0))[0] != value:
            return 0
        self.strings.pop(key, None)
        self.deleted.append(key)
        return 1


class CapturingLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def ainfo(self, _event: str, **fields: object) -> None:
        self.events.append(fields)

    async def aerror(self, _event: str, **fields: object) -> None:
        self.events.append(fields)


def session_factory(session: FakeSession):
    @asynccontextmanager
    async def factory() -> AsyncIterator[FakeSession]:
        yield session

    return factory


def scheduler(
    redis: FakeRedis,
    session: FakeSession,
    logger: CapturingLogger | None = None,
) -> CoupleCodeScheduler:
    return CoupleCodeScheduler(
        redis=redis,
        session_factory=session_factory(session),
        jwt_secret="x" * 64,
        lock_ttl_seconds=120,
        marker_ttl_seconds=93_600,
        clock=lambda: 1_700_000_000.0,
        logger=logger or CapturingLogger(),
    )


@pytest.mark.parametrize(
    ("ttl", "expected"),
    [(-1, 0), (0, 1), (86_399, 1), (86_400, 0)],
)
async def test_scan_filters_reverse_keys_and_ttl_boundaries(ttl: int, expected: int) -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (ttl, {"userId": "7"})})
    session = FakeSession([])

    result = await scheduler(redis, session).run()

    assert result.processed == expected
    assert len(session.notifications) == expected
    assert all(call[1:] == ("couple:code:*", 100) for call in redis.scan_calls)


@pytest.mark.parametrize("user_id", [None, "", "0", "-1", "+1", "abc", "9223372036854775808"])
async def test_invalid_user_id_is_skipped(user_id: str | None) -> None:
    values = {} if user_id is None else {"userId": user_id}
    redis = FakeRedis({"couple:code:ABCD1234": (3_600, values)})
    session = FakeSession([])

    result = await scheduler(redis, session).run()

    assert result.processed == 0
    assert result.skipped >= 1
    assert session.notifications == []


async def test_marker_idempotency_and_notification_contract() -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (7_200, {"userId": "7"})})
    session = FakeSession([])
    worker = scheduler(redis, session)

    first = await worker.run()
    second = await worker.run()

    assert (first.processed, second.processed, second.duplicates) == (1, 0, 1)
    notification = session.notifications[0]
    assert notification.user_id == 7
    assert notification.type == 2
    assert notification.title == "⏰ 情侣码即将过期"
    assert notification.related_id is None
    assert notification.related_type == "couple_code"
    assert notification.sender_id is None
    assert "2 小时" in notification.content
    assert all("ABCD1234" not in key and ":7:" not in key for key in redis.strings)


async def test_lock_contention_skips_without_writing() -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (3_600, {"userId": "7"})})
    redis.locked = True
    session = FakeSession([])

    result = await scheduler(redis, session).run()

    assert result.status == "skipped_locked"
    assert session.notifications == []


async def test_commit_failure_rolls_back_and_removes_only_its_marker() -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (3_600, {"userId": "7"})})
    session = FakeSession([], fail_commit=True)

    result = await scheduler(redis, session).run()

    assert result.failed == 1
    assert session.rollbacks == 1
    assert not [key for key in redis.strings if ":marker:" in key]


async def test_delete_after_marker_reservation_skips_and_cleans_marker() -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (3_600, {"userId": "7"})})
    session = FakeSession([])
    original_ttl = redis.ttl
    calls = 0

    async def deleting_ttl(key: str) -> int:
        nonlocal calls
        calls += 1
        if calls == 2:
            redis.values.pop(key, None)
        return await original_ttl(key)

    redis.ttl = deleting_ttl  # type: ignore[method-assign]
    result = await scheduler(redis, session).run()

    assert result.processed == 0
    assert result.skipped >= 1
    assert session.notifications == []
    assert not [key for key in redis.strings if ":marker:" in key]


async def test_single_redis_key_failure_does_not_block_later_valid_key() -> None:
    broken_key = "couple:code:BROKEN"
    valid_key = "couple:code:VALID"
    redis = FakeRedis(
        {
            broken_key: (3_600, {"userId": "7"}),
            valid_key: (3_600, {"userId": "8"}),
        }
    )
    redis.fail_ttl_keys.add(broken_key)
    session = FakeSession([])

    result = await scheduler(redis, session).run()

    assert (result.failed, result.processed) == (1, 1)
    assert len(session.notifications) == 1
    assert session.notifications[0].user_id == 8


async def test_logs_are_exactly_six_redacted_fields() -> None:
    logger = CapturingLogger()
    redis = FakeRedis({"couple:code:PRIVATECODE": (3_600, {"userId": "700"})})
    session = FakeSession([])

    await scheduler(redis, session, logger).run()

    expected = {"requestId", "module", "operation", "result", "durationMs", "errorCode"}
    assert logger.events
    assert all(set(event) == expected for event in logger.events)
    serialized = json.dumps(logger.events, ensure_ascii=False)
    assert "PRIVATECODE" not in serialized
    assert "700" not in serialized


def test_configured_scheduler_logs_render_exact_six_fields() -> None:
    stream = StringIO()
    settings = Settings(  # noqa: S106
        _env_file=None,
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET="x" * 64,  # noqa: S106
    )
    configure_logging(settings, stream=stream)

    structlog.get_logger().error(
        "private-event",
        requestId="run-1",
        module="couple_code_scheduler",
        operation="item.persist",
        result="processed_1",
        durationMs=1,
        errorCode="NONE",
        code="PRIVATECODE",
        userId="700",
        content="private notification",
    )

    assert json.loads(stream.getvalue()) == {
        "requestId": "run-1",
        "module": "couple_code_scheduler",
        "operation": "item.persist",
        "result": "processed_1",
        "durationMs": 1,
        "errorCode": "NONE",
    }
    logging.getLogger().handlers.clear()


async def test_two_concurrent_workers_only_one_acquires_lock() -> None:
    redis = FakeRedis({"couple:code:ABCD1234": (3_600, {"userId": "7"})})
    session = FakeSession([])
    first = scheduler(redis, session)
    second = scheduler(redis, session)

    results = await asyncio.gather(first.run(), second.run())

    assert sum(result.processed for result in results) == 1
    assert sum(result.status == "skipped_locked" for result in results) == 1
