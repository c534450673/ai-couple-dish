import asyncio
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
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import create_access_token
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient

SECRET = "w" * 64
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
async def mysql_relationship_weather_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


class WeatherContext:
    def __init__(self, client: AsyncClient, engine: AsyncEngine) -> None:
        self.client = client
        self.engine = engine
        self.auth = {user_id: _headers(user_id) for user_id in (801, 802, 901, 902, 1001)}


@pytest.fixture
async def weather_context(
    mysql_relationship_weather_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[WeatherContext]:
    today = datetime.now().date()
    now = datetime.combine(today, datetime.min.time()) + timedelta(hours=12)
    async with mysql_relationship_weather_engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, nick_name, couple_id, status, is_deleted)
                VALUES (801, 'weather-one', '气象甲', 81, 1, 0),
                       (802, 'weather-two', '气象乙', 81, 1, 0),
                       (901, 'weather-out-one', '隔离丙', 91, 1, 0),
                       (902, 'weather-out-two', '隔离丁', 91, 1, 0),
                       (1001, 'weather-unbound', '未绑定戊', NULL, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status)
                VALUES (81, 'WEATHER-ONE', 801, 802, 1),
                       (91, 'WEATHER-TWO', 901, 902, 1)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_daily_greeting
                    (id, couple_id, user_id, greeting_type, greeting_date,
                     is_deleted, create_time)
                VALUES (8101, 81, 801, 1, :today, 0, :now),
                       (8102, 81, 802, 2, :yesterday, 0, :yesterday_time),
                       (8103, 81, 801, 1, :two_days, 0, :two_days_time),
                       (8104, 81, 801, 1, :today, 1, :now),
                       (8105, 81, 801, 1, :old_day, 0, :old_time)
                """
            ),
            {
                "today": today,
                "yesterday": today - timedelta(days=1),
                "two_days": today - timedelta(days=2),
                "old_day": today - timedelta(days=10),
                "now": now,
                "yesterday_time": now - timedelta(days=1),
                "two_days_time": now - timedelta(days=2),
                "old_time": now - timedelta(days=10),
            },
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple_menu
                    (id, couple_id, creator_id, restaurant_name, eaten_date,
                     is_deleted, create_time)
                VALUES (8201, 81, 801, 'private-weather-restaurant-a', :today, 0, :menu_one),
                       (8202, 81, 802, 'private-weather-restaurant-b', :yesterday, 0, :menu_two),
                       (8203, 81, 801, 'deleted-private-restaurant', :today, 1, :menu_three)
                """
            ),
            {
                "today": today,
                "yesterday": today - timedelta(days=1),
                "menu_one": now - timedelta(hours=1),
                "menu_two": now - timedelta(days=1, hours=1),
                "menu_three": now - timedelta(hours=2),
            },
        )
    redis = RedisClient(redis_url)
    await redis.connect()
    app = create_app(_settings())
    app.state.redis = redis
    factory = async_sessionmaker(mysql_relationship_weather_engine, expire_on_commit=False)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield WeatherContext(client, mysql_relationship_weather_engine)
    finally:
        await redis.close()


def _payload(response: Response) -> dict[str, Any]:
    assert response.status_code in {200, 400, 500}
    return cast(dict[str, Any], response.json())


async def _rows(engine: AsyncEngine, statement: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), params)
        return [dict(item) for item in result.mappings().all()]


@pytest.mark.integration
async def test_weather_initialization_is_single_and_current_uses_soft_deleted_sources(
    weather_context: WeatherContext,
) -> None:
    context = weather_context
    responses = await asyncio.gather(
        *[
            context.client.get("/api/relationshipWeather/current", headers=context.auth[801])
            for _ in range(6)
        ]
    )
    assert all(_payload(response)["code"] == 200 for response in responses)
    assert all(_payload(response)["data"]["interactionScore"] == 59 for response in responses)
    assert all(_payload(response)["data"]["weatherLevel"] == "rainy" for response in responses)
    rows = await _rows(
        context.engine,
        "SELECT couple_id, interaction_score, weather_level FROM t_relationship_weather",
    )
    assert rows == [{"couple_id": 81, "interaction_score": 59, "weather_level": "rainy"}]


@pytest.mark.integration
async def test_weather_interactions_suggestions_forecast_and_logs_follow_spring_contract(
    weather_context: WeatherContext,
) -> None:
    context = weather_context
    await context.client.get("/api/relationshipWeather/current", headers=context.auth[801])
    with capture_logs() as logs:
        interactions = await context.client.get(
            "/api/relationshipWeather/interactions?limit=1", headers=context.auth[802]
        )
    records = _payload(interactions)["data"]
    assert len(records) == 3
    assert sum(item["type"] == "greeting" for item in records) == 1
    assert sum(item["type"] == "date" for item in records) == 2
    assert "deleted-private-restaurant" not in str(records)
    assert "private-weather-restaurant-a" not in str(logs)
    assert "requestId" in str(logs)
    assert "durationMs" in str(logs)

    zero_limit = await context.client.get(
        "/api/relationshipWeather/interactions?limit=0", headers=context.auth[802]
    )
    assert all(item["type"] == "date" for item in _payload(zero_limit)["data"])

    suggestions = await context.client.get(
        "/api/relationshipWeather/suggestions", headers=context.auth[801]
    )
    assert _payload(suggestions)["data"] == [
        {
            "type": "interaction",
            "title": "增加互动",
            "description": "多和TA互动，提升关系温度",
            "action": "发送一个早安或晚安问候吧",
        }
    ]
    forecast = await context.client.get(
        "/api/relationshipWeather/forecast", headers=context.auth[801]
    )
    forecast_data = _payload(forecast)["data"]
    assert len(forecast_data) == 7
    assert forecast_data[0]["predictedScore"] == 59
    assert forecast_data[0]["weatherLevel"] == "rainy"
    assert forecast_data[1]["weatherLevel"] == "cloudy"


@pytest.mark.integration
async def test_weather_couple_isolation_unbound_and_unbinding_are_rejected(
    weather_context: WeatherContext,
) -> None:
    context = weather_context
    outsider = await context.client.get(
        "/api/relationshipWeather/forecast", headers=context.auth[901]
    )
    assert _payload(outsider)["code"] == 200
    rows = await _rows(
        context.engine,
        "SELECT couple_id, interaction_score FROM t_relationship_weather ORDER BY couple_id",
    )
    assert rows == [{"couple_id": 91, "interaction_score": 60}]

    unbound = await context.client.get(
        "/api/relationshipWeather/current", headers=context.auth[1001]
    )
    assert _payload(unbound)["code"] == 2006
    async with context.engine.begin() as connection:
        await connection.execute(text("UPDATE t_couple SET status = 2 WHERE id = 81"))
    blocked_responses = [
        await context.client.get(path, headers=context.auth[801])
        for path in (
            "/api/relationshipWeather/current",
            "/api/relationshipWeather/interactions",
            "/api/relationshipWeather/suggestions",
            "/api/relationshipWeather/forecast",
        )
    ]
    assert all(_payload(response)["code"] == 2006 for response in blocked_responses)
