import asyncio
import logging
import os
import re
from collections.abc import AsyncIterator
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

SECRET = "t" * 64
logger = logging.getLogger(__name__)


def _reset_schema(connection: Connection) -> None:
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in inspect(connection).get_table_names():
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    source = (Path(__file__).parents[2] / "src/test/resources/schema-test.sql").read_text()
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_sweet_bomb_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id, SECRET, expiration_ms=300_000)}"
    }


async def _rows(engine: AsyncEngine, statement: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), params)
        return [dict(row) for row in result.mappings().all()]


async def _seed(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, couple_id, status, is_deleted) VALUES
                (801, 'bomb-one', 81, 1, 0), (802, 'bomb-two', 81, 1, 0),
                (901, 'bomb-three', 91, 1, 0), (902, 'bomb-four', 91, 1, 0),
                (1001, 'bomb-unbound', NULL, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status) VALUES
                (81, 'BOMB-ONE', 801, 802, 1), (91, 'BOMB-TWO', 901, 902, 1)
                """
            )
        )


@pytest.fixture
async def sweet_bomb_context(
    mysql_sweet_bomb_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient]]:
    await _seed(mysql_sweet_bomb_engine)
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_sweet_bomb_engine, expire_on_commit=False)
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield (
                client,
                mysql_sweet_bomb_engine,
                {id_: _headers(id_) for id_ in (801, 802, 901, 902, 1001)},
                redis,
            )
    finally:
        await redis.close()


def _payload(response: Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    value = cast(dict[str, Any], response.json())
    assert set(value) == {"code", "message", "data"}
    return value


@pytest.mark.integration
async def test_sweet_bomb_scope_notifications_idempotency_and_redacted_logs(
    sweet_bomb_context: tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient],
) -> None:
    client, engine, auth, _ = sweet_bomb_context
    private_answer = "private-sweet-bomb-answer"
    with capture_logs() as logs:
        created = await client.post("/api/sweetBomb/generate", headers=auth[801])
        created_data = _payload(created)["data"]
        assert created_data["id"]
        bomb_id = int(created_data["id"])
        assert set(created_data) == {
            "id",
            "bombType",
            "bombTypeName",
            "content",
            "sentTime",
            "isRead",
            "isAnswered",
            "answerContent",
            "answerTime",
            "createTime",
        }
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE t_sweet_bomb SET bomb_type = 'question', content = :content "
                    "WHERE id = :id"
                ),
                {"content": '{"question":"test"}', "id": bomb_id},
            )
        assert (await client.get("/api/sweetBomb/unread", headers=auth[802])).json()["data"][0][
            "id"
        ] == bomb_id
        assert (await client.get(f"/api/sweetBomb/detail/{bomb_id}", headers=auth[901])).json()[
            "code"
        ] == 3002
        reads = await asyncio.gather(
            *[client.post(f"/api/sweetBomb/read/{bomb_id}", headers=auth[802]) for _ in range(4)]
        )
        assert all(_payload(response)["code"] == 200 for response in reads)
        answers = await asyncio.gather(
            *[
                client.post(
                    f"/api/sweetBomb/answer/{bomb_id}",
                    headers=auth[802],
                    params={"answerContent": private_answer},
                )
                for _ in range(4)
            ]
        )
        assert all(_payload(response)["code"] == 200 for response in answers)
        assert _payload(await client.get("/api/sweetBomb/history?limit=0", headers=auth[802]))[
            "data"
        ]
        assert (
            _payload(await client.get("/api/sweetBomb/unread/count", headers=auth[1001]))["data"]
            == 0
        )

    rows = await _rows(
        engine,
        "SELECT is_read, is_answered, answer_content FROM t_sweet_bomb WHERE id = :id",
        id=bomb_id,
    )
    assert rows[0]["is_read"] == 1
    assert rows[0]["is_answered"] == 1
    assert rows[0]["answer_content"] == private_answer
    notification_rows = await _rows(
        engine,
        (
            "SELECT id FROM t_notification WHERE user_id = 802 "
            "AND related_id = :id AND related_type = 'sweet_bomb'"
        ),
        id=bomb_id,
    )
    assert len(notification_rows) == 1
    assert private_answer not in str(logs)
    assert "bomb-one" not in str(logs)
    assert "requestId" in str(logs) and "durationMs" in str(logs)


@pytest.mark.integration
async def test_sweet_bomb_write_rolls_back_if_notification_insert_fails(
    sweet_bomb_context: tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient],
) -> None:
    client, engine, auth, _ = sweet_bomb_context
    async with engine.begin() as connection:
        await connection.execute(text("ALTER TABLE t_notification DROP COLUMN title"))
    client._transport = ASGITransport(app=client._transport.app, raise_app_exceptions=False)
    response = await client.post("/api/sweetBomb/generate", headers=auth[801])
    assert response.status_code == 500
    assert await _rows(engine, "SELECT id FROM t_sweet_bomb") == []
