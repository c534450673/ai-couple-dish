import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import create_access_token
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient

SECRET = "l" * 64
logger = logging.getLogger(__name__)


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, SECRET, expiration_ms=300_000)
    return {"Authorization": f"Bearer {token}"}


def _reset_schema(connection: Connection) -> None:
    table_names = inspect(connection).get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in table_names:
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = path.read_text()
    source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_love_calendar_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


class CalendarContext:
    def __init__(self, client: AsyncClient, engine: AsyncEngine) -> None:
        self.client = client
        self.engine = engine
        self.auth = {user_id: _headers(user_id) for user_id in (601, 602, 701)}


@pytest.fixture
async def love_calendar_context(
    mysql_love_calendar_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[CalendarContext]:
    today = datetime.now().date()
    async with mysql_love_calendar_engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, nick_name, couple_id, status, is_deleted)
                VALUES (601, 'calendar-one', '日历甲', 61, 1, 0),
                       (602, 'calendar-two', '日历乙', 61, 1, 0),
                       (701, 'calendar-outsider', '隔离丙', 71, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, start_date, status)
                VALUES (61, 'CALENDAR-ONE', 601, 602, :start_date, 1),
                       (71, 'CALENDAR-TWO', 701, 701, :start_date, 1)
                """
            ),
            {"start_date": today - timedelta(days=10)},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_anniversary
                    (id, couple_id, creator_id, name, anniversary_date,
                     anniversary_type, is_deleted)
                VALUES (6101, 61, 601, '在一起', :today, 2, 0),
                       (6102, 61, 601, '已删除', :today, 2, 1)
                """
            ),
            {"today": today},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_time_capsule
                    (id, couple_id, creator_id, capsule_type, title, unlock_date,
                     status, is_deleted)
                VALUES (6201, 61, 601, 'text', '未来胶囊', :tomorrow, 0, 0)
                """
            ),
            {"tomorrow": today + timedelta(days=1)},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_heart_moment
                    (id, couple_id, creator_id, moment_type, content, create_time, is_deleted)
                VALUES (6301, 61, 601, 'text', '心动内容', :now, 0)
                """
            ),
            {"now": datetime.combine(today, datetime.min.time()) + timedelta(hours=8)},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple_menu
                    (id, couple_id, creator_id, restaurant_name, dish_name, eaten_date, is_deleted)
                VALUES (6401, 61, 601, '约会餐厅', '双人套餐', :today, 0)
                """
            ),
            {"today": today},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_food_note
                    (id, couple_id, author_id, title, content, create_time, is_deleted)
                VALUES (6501, 61, 601, '美食笔记', '记录', :now, 0)
                """
            ),
            {"now": datetime.combine(today, datetime.min.time()) + timedelta(hours=9)},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_wish
                    (id, couple_id, creator_id, wish_type, title, status, achieved_date, is_deleted)
                VALUES (6601, 61, 601, 'dish', '已实现心愿', 1, :today, 0)
                """
            ),
            {"today": today},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_love_calendar
                    (id, couple_id, calendar_date, event_type, event_title)
                VALUES (6701, 61, :today, 'custom', '不应聚合')
                """
            ),
            {"today": today},
        )
    redis = RedisClient(redis_url)
    await redis.connect()
    app = create_app(_settings())
    app.state.redis = redis
    factory = async_sessionmaker(mysql_love_calendar_engine, expire_on_commit=False)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield CalendarContext(client, mysql_love_calendar_engine)
    finally:
        await redis.close()


def _payload(response: Response) -> dict[str, Any]:
    assert response.status_code in {200, 400, 500}
    return cast(dict[str, Any], response.json())


@pytest.mark.integration
async def test_love_calendar_aggregates_spring_sources_and_enforces_scope(
    love_calendar_context: CalendarContext,
) -> None:
    context = love_calendar_context
    today = datetime.now().date().isoformat()
    response = await context.client.get(
        f"/api/loveCalendar/events/date?date={today}", headers=context.auth[601]
    )
    body = _payload(response)
    assert body["code"] == 200
    events = body["data"]
    assert {item["eventType"] for item in events} == {
        "anniversary",
        "heartMoment",
        "menu",
        "note",
        "wish",
    }
    assert all(item["id"] != 6701 for item in events)
    assert all("private" not in str(item) for item in events)

    month = await context.client.get(
        f"/api/loveCalendar/month?year={today[:4]}&month={int(today[5:7])}",
        headers=context.auth[602],
    )
    assert _payload(month)["data"]["monthStats"]["totalEvents"] == 6

    outsider = await context.client.get(
        f"/api/loveCalendar/events/date?date={today}", headers=context.auth[701]
    )
    assert _payload(outsider)["code"] == 200
    assert _payload(outsider)["data"] == []

    async with context.engine.begin() as connection:
        await connection.execute(text("UPDATE t_couple SET status = 2 WHERE id = 61"))
    blocked = await context.client.get(
        f"/api/loveCalendar/events/date?date={today}", headers=context.auth[601]
    )
    assert _payload(blocked)["code"] == 2006
