import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.errors import BusinessError
from app.db.models import Feed, Notification, User
from app.db.session import Database
from app.services.feed import accept, expire_due


async def _prepare(database: Database) -> None:
    async with database.engine.begin() as connection:
        await connection.run_sync(User.__table__.create, checkfirst=True)
        await connection.run_sync(Feed.__table__.create, checkfirst=True)
        await connection.run_sync(Notification.__table__.create, checkfirst=True)


def _feed(feed_id: int, status: int, expires: datetime) -> Feed:
    return Feed(
        id=feed_id,
        couple_id=1,
        sender_id=feed_id + 100,
        receiver_id=feed_id + 200,
        feed_type="meal",
        status=status,
        expire_time=expires,
    )


@pytest.mark.integration
async def test_expiry_boundary_and_notification_contract(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    now = datetime(2026, 7, 26, 12)
    ids = list(range(935001, 935007))
    await database.connect()
    await _prepare(database)
    try:
        async with database.session() as session:
            session.add_all(
                [
                    _feed(ids[0], 0, now - timedelta(seconds=1)),
                    _feed(ids[1], 0, now),
                    _feed(ids[2], 0, now + timedelta(seconds=1)),
                    _feed(ids[3], 1, now - timedelta(seconds=1)),
                    _feed(ids[4], 2, now - timedelta(seconds=1)),
                    _feed(ids[5], 3, now - timedelta(seconds=1)),
                ]
            )
            await session.commit()
        factory = async_sessionmaker(database.engine, expire_on_commit=False)
        async with factory() as session:
            assert await expire_due(session, "test", now=now) == 1
        async with factory() as session:
            rows = {
                item.id: item
                for item in (await session.scalars(select(Feed).where(Feed.id.in_(ids)))).all()
            }
            notification = await session.scalar(
                select(Notification).where(
                    Notification.related_id == ids[0], Notification.related_type == "feed"
                )
            )
        assert [rows[item].status for item in ids] == [3, 0, 0, 1, 2, 3]
        assert notification is not None
        assert (
            notification.user_id,
            notification.type,
            notification.title,
            notification.content,
            notification.sender_id,
            notification.is_read,
            notification.read_time,
        ) == (
            ids[0] + 100,
            2,
            "⏰ 投喂已过期",
            "您发送的投喂已过期未被领取，下次记得提醒TA及时领取哦！",
            None,
            0,
            None,
        )
    finally:
        async with database.session() as session:
            await session.execute(
                Notification.__table__.delete().where(Notification.related_id.in_(ids))
            )
            await session.execute(Feed.__table__.delete().where(Feed.id.in_(ids)))
            await session.commit()
        await database.close()


@pytest.mark.integration
async def test_two_workers_create_one_expiry_notification(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    item_id = 935101
    await database.connect()
    await _prepare(database)
    try:
        async with database.session() as session:
            session.add(_feed(item_id, 0, datetime(2026, 1, 1)))
            await session.commit()
        factory = async_sessionmaker(database.engine, expire_on_commit=False)
        async with factory() as one, factory() as two:
            locked = asyncio.Event()
            release = asyncio.Event()
            first_task = asyncio.create_task(
                expire_due(
                    _BlockingExpirySession(one, locked, release),
                    "a",
                    now=datetime(2026, 7, 26),
                )
            )
            await locked.wait()
            second_result = await expire_due(two, "b", now=datetime(2026, 7, 26))
            await two.rollback()
            release.set()
            first_result = await first_task
        async with factory() as session:
            count = await session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.related_id == item_id
                )
            )
        assert (first_result, second_result) == (1, 0)
        assert count == 1
    finally:
        async with database.session() as session:
            await session.execute(
                Notification.__table__.delete().where(Notification.related_id == item_id)
            )
            await session.execute(Feed.__table__.delete().where(Feed.id == item_id))
            await session.commit()
        await database.close()


@pytest.mark.integration
async def test_commit_failure_rolls_back_and_retry_recovers(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    item_id = 935201
    await database.connect()
    await _prepare(database)
    try:
        async with database.session() as session:
            session.add(_feed(item_id, 0, datetime(2026, 1, 1)))
            await session.commit()
        factory = async_sessionmaker(database.engine, expire_on_commit=False)
        async with factory() as session:
            original = session.commit

            async def fail() -> None:
                raise RuntimeError("db")

            session.commit = fail  # type: ignore[method-assign]
            with pytest.raises(RuntimeError):
                await expire_due(session, "x", now=datetime(2026, 7, 26))
            session.commit = original  # type: ignore[method-assign]
        async with factory() as session:
            assert (await session.get(Feed, item_id)).status == 0
            assert (
                await session.scalar(
                    select(func.count(Notification.id)).where(
                        Notification.related_id == item_id
                    )
                )
                == 0
            )
            assert await expire_due(session, "x", now=datetime(2026, 7, 26)) == 1
    finally:
        async with database.session() as session:
            await session.execute(
                Notification.__table__.delete().where(Notification.related_id == item_id)
            )
            await session.execute(Feed.__table__.delete().where(Feed.id == item_id))
            await session.commit()
        await database.close()


class _BlockingExpirySession:
    def __init__(self, session, locked: asyncio.Event, release: asyncio.Event) -> None:  # type: ignore[no-untyped-def]
        self._session = session
        self.locked = locked
        self.release = release

    async def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = await self._session.execute(statement, *args, **kwargs)
        self.locked.set()
        await self.release.wait()
        return result

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._session, name)


class _BlockingAcceptSession:
    def __init__(
        self,
        session,
        requested: asyncio.Event,
        locked: asyncio.Event,
        release: asyncio.Event,
    ) -> None:  # type: ignore[no-untyped-def]
        self._session = session
        self.requested = requested
        self.locked = locked
        self.release = release
        self._scalar_calls = 0

    async def scalar(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        self._scalar_calls += 1
        if self._scalar_calls == 2:
            self.requested.set()
        result = await self._session.scalar(statement, *args, **kwargs)
        if self._scalar_calls == 2:
            self.locked.set()
            await self.release.wait()
        return result

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._session, name)


class _RequestingAcceptSession:
    def __init__(self, session, requested: asyncio.Event) -> None:  # type: ignore[no-untyped-def]
        self._session = session
        self.requested = requested
        self._scalar_calls = 0

    async def scalar(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        self._scalar_calls += 1
        if self._scalar_calls == 2:
            self.requested.set()
        return await self._session.scalar(statement, *args, **kwargs)

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._session, name)


def _request() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(request_id="feed-race"))


async def _seed_race_feed(
    database: Database, feed_id: int, sender_id: int, receiver_id: int
) -> None:
    async with database.session() as session:
        item = _feed(feed_id, 0, datetime(2026, 1, 1))
        item.sender_id = sender_id
        item.receiver_id = receiver_id
        session.add_all(
            [
                User(id=sender_id, openid=f"feed-race-sender-{sender_id}", couple_id=1),
                User(id=receiver_id, openid=f"feed-race-receiver-{receiver_id}", couple_id=1),
                item,
            ]
        )
        await session.commit()


async def _cleanup_race(database: Database, feed_id: int, sender_id: int, receiver_id: int) -> None:
    async with database.session() as session:
        await session.execute(
            Notification.__table__.delete().where(Notification.related_id == feed_id)
        )
        await session.execute(Feed.__table__.delete().where(Feed.id == feed_id))
        await session.execute(User.__table__.delete().where(User.id.in_([sender_id, receiver_id])))
        await session.commit()


@pytest.mark.integration
async def test_expiry_wins_accept_competition(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=3, max_overflow=0)
    feed_id, sender_id, receiver_id = 935301, 935302, 935303
    await database.connect()
    await _prepare(database)
    await _seed_race_feed(database, feed_id, sender_id, receiver_id)
    expiry_locked, expiry_release = asyncio.Event(), asyncio.Event()
    accept_requested = asyncio.Event()
    factory = async_sessionmaker(database.engine, expire_on_commit=False)
    try:
        async with factory() as expiry_session, factory() as accept_session:
            expiry_task = asyncio.create_task(
                expire_due(
                    _BlockingExpirySession(expiry_session, expiry_locked, expiry_release),
                    "expiry-first",
                    now=datetime(2026, 7, 26),
                )
            )
            await expiry_locked.wait()
            accept_task = asyncio.create_task(
                accept(
                    _request(),
                    _RequestingAcceptSession(accept_session, accept_requested),
                    receiver_id,
                    feed_id,
                )
            )
            await accept_requested.wait()
            expiry_release.set()
            assert await expiry_task == 1
            with pytest.raises(BusinessError, match="投喂已过期") as error:
                await accept_task
            assert error.value.code == 6003
        async with factory() as session:
            item = await session.get(Feed, feed_id)
            expiry_count = await session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.related_id == feed_id,
                    Notification.title == "⏰ 投喂已过期",
                )
            )
            accept_count = await session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.related_id == feed_id,
                    Notification.title == "投喂被接受",
                )
            )
        assert item is not None and item.status == 3
        assert (expiry_count, accept_count) == (1, 0)
    finally:
        await _cleanup_race(database, feed_id, sender_id, receiver_id)
        await database.close()


@pytest.mark.integration
async def test_accept_wins_competition(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=3, max_overflow=0)
    feed_id, sender_id, receiver_id = 935311, 935312, 935313
    await database.connect()
    await _prepare(database)
    async with database.session() as session:
        item = _feed(feed_id, 0, datetime(2099, 1, 1))
        item.sender_id = sender_id
        item.receiver_id = receiver_id
        session.add_all(
            [
                User(id=sender_id, openid=f"feed-race-sender-{sender_id}", couple_id=1),
                User(id=receiver_id, openid=f"feed-race-receiver-{receiver_id}", couple_id=1),
                item,
            ]
        )
        await session.commit()
    accept_requested = asyncio.Event()
    accept_locked = asyncio.Event()
    accept_release = asyncio.Event()
    factory = async_sessionmaker(database.engine, expire_on_commit=False)
    try:
        async with factory() as accept_session, factory() as expiry_session:
            accept_task = asyncio.create_task(
                accept(
                    _request(),
                    _BlockingAcceptSession(
                        accept_session, accept_requested, accept_locked, accept_release
                    ),
                    receiver_id,
                    feed_id,
                )
            )
            await accept_requested.wait()
            await accept_locked.wait()
            assert await expire_due(expiry_session, "accept-first", now=datetime(2100, 1, 1)) == 0
            await expiry_session.rollback()
            accept_release.set()
            await accept_task
        async with factory() as session:
            item = await session.get(Feed, feed_id)
            expiry_count = await session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.related_id == feed_id,
                    Notification.title == "⏰ 投喂已过期",
                )
            )
        assert item is not None and item.status == 1
        assert expiry_count == 0
    finally:
        await _cleanup_race(database, feed_id, sender_id, receiver_id)
        await database.close()
