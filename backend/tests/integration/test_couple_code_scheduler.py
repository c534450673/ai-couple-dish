import asyncio
import uuid

import pytest
from sqlalchemy import delete, select

from app.db.models import Notification
from app.db.session import Database
from app.redis.client import RedisClient
from app.services.couple_code_scheduler import CoupleCodeScheduler


async def _notification_count(database: Database, user_id: int) -> int:
    async with database.session() as session:
        rows = await session.scalars(select(Notification).where(Notification.user_id == user_id))
        return len(rows.all())


class BlockingRedis:
    """Pause the first scan so a second real Redis worker observes its distributed lock."""

    def __init__(self, raw, entered: asyncio.Event, release: asyncio.Event) -> None:  # type: ignore[no-untyped-def]
        self.raw = raw
        self.entered = entered
        self.release = release
        self._blocked = False

    async def scan(self, cursor: int, *, match: str, count: int):  # type: ignore[no-untyped-def]
        if not self._blocked:
            self._blocked = True
            self.entered.set()
            await self.release.wait()
        return await self.raw.scan(cursor, match=match, count=count)

    async def ttl(self, key: str) -> int:
        return await self.raw.ttl(key)

    async def hgetall(self, key: str):  # type: ignore[no-untyped-def]
        return await self.raw.hgetall(key)

    async def set(self, key: str, value: str, *, nx: bool, ex: int):  # type: ignore[no-untyped-def]
        return await self.raw.set(key, value, nx=nx, ex=ex)

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> int:
        return await self.raw.eval(script, numkeys, *keys_and_args)


class DeleteBeforeHashRedis:
    """Simulate Spring bind deleting the hash after SCAN's candidate TTL check."""

    def __init__(self, raw, target_key: str) -> None:  # type: ignore[no-untyped-def]
        self.raw = raw
        self.target_key = target_key
        self._target_ttl_calls = 0

    async def scan(self, cursor: int, *, match: str, count: int):  # type: ignore[no-untyped-def]
        return await self.raw.scan(cursor, match=match, count=count)

    async def ttl(self, key: str) -> int:
        if key == self.target_key:
            self._target_ttl_calls += 1
            if self._target_ttl_calls == 2:
                await self.raw.delete(key)
        return await self.raw.ttl(key)

    async def hgetall(self, key: str):  # type: ignore[no-untyped-def]
        return await self.raw.hgetall(key)

    async def set(self, key: str, value: str, *, nx: bool, ex: int):  # type: ignore[no-untyped-def]
        return await self.raw.set(key, value, nx=nx, ex=ex)

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> int:
        return await self.raw.eval(script, numkeys, *keys_and_args)


@pytest.mark.integration
async def test_real_mysql_redis_worker_is_idempotent_and_preserves_notification_fields(
    mysql_url: str, redis_url: str
) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    redis = RedisClient(redis_url)
    user_id = 9_000_001
    key = f"couple:code:{uuid.uuid4().hex.upper()}"
    bad_key = f"couple:code:{uuid.uuid4().hex.upper()}"
    await database.connect()
    await redis.connect()
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Notification.__table__.create, checkfirst=True)
        async with database.session() as session:
            await session.execute(delete(Notification).where(Notification.user_id == user_id))
            await session.commit()
        await redis.raw.hset(key, mapping={"userId": str(user_id)})
        await redis.raw.expire(key, 86_399)
        await redis.raw.hset(bad_key, mapping={"unexpected": "value"})
        await redis.raw.expire(bad_key, 86_399)
        worker = CoupleCodeScheduler(
            redis=redis.raw,
            session_factory=database.session,
            jwt_secret="x" * 64,
            lock_ttl_seconds=60,
            marker_ttl_seconds=93_600,
        )

        first = await worker.run()
        second = await worker.run()

        assert (first.processed, second.duplicates) == (1, 1)
        assert first.skipped >= 1
        assert await _notification_count(database, user_id) == 1
        async with database.session() as session:
            notification = await session.scalar(
                select(Notification).where(Notification.user_id == user_id)
            )
        assert notification is not None
        assert (
            notification.type,
            notification.title,
            notification.related_id,
            notification.related_type,
            notification.sender_id,
        ) == (2, "⏰ 情侣码即将过期", None, "couple_code", None)
    finally:
        await redis.raw.delete(key, bad_key)
        async with database.session() as session:
            await session.execute(delete(Notification).where(Notification.user_id == user_id))
            await session.commit()
        await redis.close()
        await database.close()


@pytest.mark.integration
async def test_real_redis_lock_and_bind_delete_race_do_not_write_stale_notification(
    mysql_url: str, redis_url: str
) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    redis = RedisClient(redis_url)
    user_id = 9_000_002
    key = f"couple:code:{uuid.uuid4().hex.upper()}"
    race_user_id = 9_000_003
    race_key = f"couple:code:{uuid.uuid4().hex.upper()}"
    await database.connect()
    await redis.connect()
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Notification.__table__.create, checkfirst=True)
        async with database.session() as session:
            await session.execute(delete(Notification).where(Notification.user_id == user_id))
            await session.commit()
        await redis.raw.hset(key, mapping={"userId": str(user_id)})
        await redis.raw.expire(key, 86_399)
        entered = asyncio.Event()
        release = asyncio.Event()
        first = CoupleCodeScheduler(
            redis=BlockingRedis(redis.raw, entered, release),
            session_factory=database.session,
            jwt_secret="x" * 64,
            lock_ttl_seconds=60,
            marker_ttl_seconds=93_600,
        )
        second = CoupleCodeScheduler(
            redis=redis.raw,
            session_factory=database.session,
            jwt_secret="x" * 64,
            lock_ttl_seconds=60,
            marker_ttl_seconds=93_600,
        )
        first_task = asyncio.create_task(first.run())
        await entered.wait()
        locked = await second.run()
        release.set()
        completed = await first_task

        assert locked.status == "skipped_locked"
        assert completed.processed == 1

        await redis.raw.hset(race_key, mapping={"userId": str(race_user_id)})
        await redis.raw.expire(race_key, 86_399)
        stale = CoupleCodeScheduler(
            redis=DeleteBeforeHashRedis(redis.raw, race_key),
            session_factory=database.session,
            jwt_secret="x" * 64,
            lock_ttl_seconds=60,
            marker_ttl_seconds=93_600,
        )
        stale_result = await stale.run()
        assert stale_result.processed == 0
        assert await _notification_count(database, user_id) == 1
        assert await _notification_count(database, race_user_id) == 0
    finally:
        await redis.raw.delete(key, race_key)
        async with database.session() as session:
            await session.execute(
                delete(Notification).where(Notification.user_id.in_([user_id, race_user_id]))
            )
            await session.commit()
        await redis.close()
        await database.close()
