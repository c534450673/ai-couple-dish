import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import text
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.db.session import Database
from app.redis.client import RedisClient


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.integration
async def test_mysql_uses_real_mysql_dialect(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    await database.connect()
    try:
        async with database.session() as session:
            version = (await session.execute(text("SELECT VERSION()"))).scalar_one()
            assert version.startswith("8.")
    finally:
        await database.close()


@pytest.mark.integration
async def test_redis_round_trip_is_namespaced(redis_url: str) -> None:
    client = RedisClient(redis_url)
    await client.connect()
    try:
        await client.raw.set("test:foundation:ping", "ok", ex=5)
        assert await client.raw.get("test:foundation:ping") == "ok"
    finally:
        await client.close()


async def test_database_session_rolls_back_on_exception() -> None:
    events: list[str] = []

    class FakeSession:
        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *_args: object) -> None:
            events.append("session.close")

        async def rollback(self) -> None:
            events.append("session.rollback")

    database = Database.__new__(Database)
    database._factory = FakeSession  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="transaction failed"):
        async with database.session():
            raise RuntimeError("transaction failed")

    assert events == ["session.rollback", "session.close"]


async def test_lifespan_connects_and_closes_dependencies_in_reverse_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    events: list[str] = []

    class FakeDatabase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("database.connect")

        async def close(self) -> None:
            events.append("database.close")

        async def ping(self) -> bool:
            return True

    class FakeRedisClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("redis.connect")

        async def close(self) -> None:
            events.append("redis.close")

        async def ping(self) -> bool:
            return True

    monkeypatch.setattr(main, "Database", FakeDatabase)
    monkeypatch.setattr(main, "RedisClient", FakeRedisClient)
    app = main.create_app(settings())

    async with app.router.lifespan_context(app):
        assert events == ["database.connect", "redis.connect"]

    assert events == [
        "database.connect",
        "redis.connect",
        "redis.close",
        "database.close",
    ]


async def test_lifespan_closes_database_when_redis_connect_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    events: list[str] = []

    class FakeDatabase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("database.connect")

        async def close(self) -> None:
            events.append("database.close")

        async def ping(self) -> bool:
            return True

    class FailingRedisClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("redis.connect")
            raise RuntimeError("redis://user:secret@private-host")

        async def close(self) -> None:
            events.append("redis.close")

        async def ping(self) -> bool:
            return True

    monkeypatch.setattr(main, "Database", FakeDatabase)
    monkeypatch.setattr(main, "RedisClient", FailingRedisClient)
    app = main.create_app(settings())

    with capture_logs() as logs:
        with pytest.raises(RuntimeError, match="private-host"):
            async with app.router.lifespan_context(app):
                pass

    assert events == [
        "database.connect",
        "redis.connect",
        "redis.close",
        "database.close",
    ]
    failure_log = next(log for log in logs if log["result"] == "failed")
    assert failure_log["dependency"] == "redis"
    assert failure_log["operation"] == "connect"
    assert failure_log["errorCode"] == "RuntimeError"
    assert "private-host" not in str(failure_log)
    assert "secret" not in str(failure_log)


async def test_lifespan_closes_created_resources_when_database_connect_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    events: list[str] = []

    class FailingDatabase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("database.connect")
            raise RuntimeError("database startup failed")

        async def close(self) -> None:
            events.append("database.close")

        async def ping(self) -> bool:
            return True

    class FakeRedisClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("redis.connect")

        async def close(self) -> None:
            events.append("redis.close")

        async def ping(self) -> bool:
            return True

    monkeypatch.setattr(main, "Database", FailingDatabase)
    monkeypatch.setattr(main, "RedisClient", FakeRedisClient)
    app = main.create_app(settings())

    with pytest.raises(RuntimeError, match="database startup failed"):
        async with app.router.lifespan_context(app):
            pass

    assert events == ["database.connect", "redis.close", "database.close"]


async def test_cleanup_failure_does_not_replace_startup_error_or_skip_database_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    class StartupFailure(RuntimeError):
        pass

    events: list[str] = []

    class FakeDatabase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("database.connect")

        async def close(self) -> None:
            events.append("database.close")

        async def ping(self) -> bool:
            return True

    class FailingRedisClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            events.append("redis.connect")
            raise StartupFailure("original startup error")

        async def close(self) -> None:
            events.append("redis.close")
            raise RuntimeError("cleanup failed")

        async def ping(self) -> bool:
            return True

    monkeypatch.setattr(main, "Database", FakeDatabase)
    monkeypatch.setattr(main, "RedisClient", FailingRedisClient)
    app = main.create_app(settings())

    with pytest.raises(StartupFailure, match="original startup error"):
        async with app.router.lifespan_context(app):
            pass

    assert events == [
        "database.connect",
        "redis.connect",
        "redis.close",
        "database.close",
    ]


def test_container_cleanup_preserves_start_error_when_stop_fails() -> None:
    from tests.integration.conftest import _running_container

    class StartupFailure(RuntimeError):
        pass

    events: list[str] = []

    class FailingContainer:
        def start(self) -> None:
            events.append("start")
            raise StartupFailure("readiness failed")

        def stop(self) -> None:
            events.append("stop")
            raise RuntimeError("stop failed")

    with pytest.raises(StartupFailure, match="readiness failed"):
        with _running_container(FailingContainer()):
            pass

    assert events == ["start", "stop"]


async def test_readiness_converts_dependency_exceptions_to_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    class FakeDatabase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def ping(self) -> bool:
            raise RuntimeError("database secret")

    class FakeRedisClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def ping(self) -> bool:
            return True

    monkeypatch.setattr(main, "Database", FakeDatabase)
    monkeypatch.setattr(main, "RedisClient", FakeRedisClient)
    app = main.create_app(settings())

    async with app.router.lifespan_context(app):
        states = await app.state.readiness()

    assert states == {"database": False, "redis": True}


async def test_get_session_provides_one_session_per_dependency_call() -> None:
    from app.db.session import get_session

    sessions = [object(), object()]
    calls = 0

    class FakeDatabase:
        @asynccontextmanager
        async def session(self) -> AsyncIterator[object]:
            nonlocal calls
            current = sessions[calls]
            calls += 1
            yield current

    request = type(
        "FakeRequest",
        (),
        {"app": type("FakeApp", (), {"state": type("State", (), {"db": FakeDatabase()})()})()},
    )()

    first = [item async for item in get_session(request)]  # type: ignore[arg-type]
    second = [item async for item in get_session(request)]  # type: ignore[arg-type]

    assert first == [sessions[0]]
    assert second == [sessions[1]]
    assert calls == 2


def test_get_redis_returns_decoded_raw_client() -> None:
    from app.redis.client import get_redis

    raw = object()
    request: Any = type(
        "FakeRequest",
        (),
        {
            "app": type(
                "FakeApp",
                (),
                {"state": type("State", (), {"redis": type("R", (), {"raw": raw})()})()},
            )
        },
    )()

    assert get_redis(request) is raw
