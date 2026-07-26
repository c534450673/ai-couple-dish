import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import create_access_token
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app
from app.redis.client import RedisClient
from app.services import daily_greeting as daily_greeting_service

SECRET = "g" * 64
DTO_FIELDS = {
    "id",
    "greetingType",
    "greetingTypeName",
    "content",
    "voiceUrl",
    "voiceDuration",
    "greetingDate",
    "createTime",
    "sender",
    "streakDays",
    "maxStreakDays",
    "hasCheckedToday",
    "bothCheckStatus",
}


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, SECRET, expiration_ms=300_000)
    return {"Authorization": f"Bearer {token}"}


def _reset_schema(connection: Connection) -> None:
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in inspect(connection).get_table_names():
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", path.read_text())
    return [statement.strip() for statement in source.split(";") if statement.strip()]


@pytest.fixture
async def greeting_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url, pool_size=12, max_overflow=4)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
            await connection.execute(
                text(
                    """
                    INSERT INTO t_user
                        (id, openid, nick_name, avatar_url, couple_id, status, is_deleted)
                    VALUES
                        (101, 'g101', '甲', 'avatar-a', 11, 1, 0),
                        (102, 'g102', '乙', NULL, 11, 1, 0),
                        (201, 'g201', '脏关联', NULL, 11, 1, 0),
                        (301, 'g301', '解绑甲', NULL, 22, 1, 0),
                        (302, 'g302', '解绑乙', NULL, 22, 1, 0)
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status)
                    VALUES
                        (11, 'ACTIVE11', 101, 102, 1),
                        (22, 'INACTIVE22', 301, 302, 3)
                    """
                )
            )
        yield engine
    finally:
        await engine.dispose()


class Context:
    def __init__(
        self,
        client: AsyncClient,
        engine: AsyncEngine,
        redis: RedisClient,
    ) -> None:
        self.client = client
        self.engine = engine
        self.redis = redis
        self.auth = {user_id: _headers(user_id) for user_id in (101, 102, 201, 301)}


@pytest.fixture
async def context(
    greeting_engine: AsyncEngine, mysql_url: str, redis_url: str
) -> AsyncIterator[Context]:
    redis = RedisClient(redis_url)
    await redis.connect()
    await redis.raw.flushdb()
    database = Database(mysql_url, pool_size=12, max_overflow=4)
    await database.connect()
    app = create_app(_settings())
    app.state.redis = redis
    app.state.db = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield Context(client, greeting_engine, redis)
    finally:
        await database.close()
        await redis.close()


async def _scalar(engine: AsyncEngine, sql: str, **params: Any) -> int:
    async with engine.connect() as connection:
        value = await connection.scalar(text(sql), params)
    return int(value or 0)


@pytest.mark.integration
@pytest.mark.parametrize("user_id", [201, 301])
async def test_all_routes_require_active_couple_membership(context: Context, user_id: int) -> None:
    requests = [
        context.client.post(
            "/api/dailyGreeting/send",
            headers=context.auth[user_id],
            json={"greetingType": 1},
        ),
        context.client.get(
            "/api/dailyGreeting/today/status?greetingType=1", headers=context.auth[user_id]
        ),
        context.client.get(
            "/api/dailyGreeting/both/status?greetingType=1", headers=context.auth[user_id]
        ),
        context.client.get("/api/dailyGreeting/streak?streakType=1", headers=context.auth[user_id]),
        context.client.get("/api/dailyGreeting/history", headers=context.auth[user_id]),
        context.client.get("/api/dailyGreeting/detail/1", headers=context.auth[user_id]),
    ]
    responses = await asyncio.gather(*requests)

    assert all(response.status_code == 200 for response in responses)
    assert all(
        response.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}
        for response in responses
    )
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_daily_greeting") == 0
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_greeting_streak") == 0
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_notification") == 0


@pytest.mark.integration
async def test_json_contract_and_concurrent_partner_send_are_spring_compatible(
    context: Context,
) -> None:
    empty = (
        await context.client.get(
            "/api/dailyGreeting/today/status?greetingType=1", headers=context.auth[101]
        )
    ).json()["data"]
    assert set(empty) == DTO_FIELDS
    assert empty["hasCheckedToday"] is False
    assert empty["streakDays"] == 0
    assert empty["maxStreakDays"] == 0

    responses = await asyncio.gather(
        context.client.post(
            "/api/dailyGreeting/send",
            headers=context.auth[101],
            json={"greetingType": 1, "content": "private-a"},
        ),
        context.client.post(
            "/api/dailyGreeting/send",
            headers=context.auth[102],
            json={"greetingType": 1, "voiceDuration": 0},
        ),
    )
    assert [response.json()["code"] for response in responses] == [200, 200]
    greeting_id = int(responses[0].json()["data"])

    both = (
        await context.client.get(
            "/api/dailyGreeting/both/status?greetingType=1", headers=context.auth[101]
        )
    ).json()["data"]
    assert set(both) == DTO_FIELDS
    assert both["hasCheckedToday"] is None
    assert both["bothCheckStatus"]["myChecked"] is True
    assert both["bothCheckStatus"]["partnerChecked"] is True

    history = (
        await context.client.get(
            "/api/dailyGreeting/history?greetingType=1", headers=context.auth[101]
        )
    ).json()["data"]
    assert len(history) == 2
    assert all(set(item) == DTO_FIELDS for item in history)
    assert all(item["streakDays"] is None for item in history)
    assert all(item["maxStreakDays"] is None for item in history)
    assert all(item["hasCheckedToday"] is None for item in history)
    assert all(item["bothCheckStatus"] is None for item in history)

    detail = (
        await context.client.get(
            f"/api/dailyGreeting/detail/{greeting_id}", headers=context.auth[102]
        )
    ).json()["data"]
    assert set(detail) == DTO_FIELDS
    assert detail["sender"] == {"id": 101, "nickName": "甲", "avatarUrl": "avatar-a"}
    assert detail["streakDays"] is None
    assert detail["maxStreakDays"] is None
    assert detail["hasCheckedToday"] is None
    assert detail["bothCheckStatus"] is None

    streak = (
        await context.client.get(
            "/api/dailyGreeting/streak?streakType=1", headers=context.auth[101]
        )
    ).json()["data"]
    assert set(streak) == {
        "streakType",
        "streakTypeName",
        "streakDays",
        "maxStreakDays",
        "hasCheckedToday",
    }
    assert streak["streakDays"] == 1
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_daily_greeting") == 2
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_greeting_streak") == 1
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_notification") == 2


@pytest.mark.integration
async def test_send_recomputes_date_after_lock_and_rolls_back_failed_transaction(
    context: Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    business_date = [date(2026, 7, 26)]
    original_acquire = daily_greeting_service._acquire_send_lock
    original_update = daily_greeting_service._update_streak

    async def acquire_after_midnight(*args: Any, **kwargs: Any) -> tuple[str, str]:
        business_date[0] = date(2026, 7, 27)
        return await original_acquire(*args, **kwargs)

    async def fail_after_greeting_flush(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("injected streak failure")

    monkeypatch.setattr(daily_greeting_service, "_today", lambda: business_date[0])
    monkeypatch.setattr(daily_greeting_service, "_acquire_send_lock", acquire_after_midnight)
    monkeypatch.setattr(daily_greeting_service, "_update_streak", fail_after_greeting_flush)

    failed = await context.client.post(
        "/api/dailyGreeting/send",
        headers=context.auth[101],
        json={"greetingType": 1, "content": "must-rollback"},
    )
    assert failed.status_code == 500
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_daily_greeting") == 0
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_greeting_streak") == 0
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_notification") == 0
    assert await context.redis.raw.exists("daily_greeting:send:11:1") == 0

    monkeypatch.setattr(daily_greeting_service, "_update_streak", original_update)
    succeeded = await context.client.post(
        "/api/dailyGreeting/send",
        headers=context.auth[101],
        json={"greetingType": 1},
    )
    assert succeeded.json()["code"] == 200
    async with context.engine.connect() as connection:
        stored_date = await connection.scalar(
            text("SELECT greeting_date FROM t_daily_greeting WHERE user_id = 101")
        )
    assert stored_date == date(2026, 7, 27)
