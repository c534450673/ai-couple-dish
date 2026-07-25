import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import date
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
from app.services import sweet_bomb

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
                INSERT INTO t_user
                (id, openid, nick_name, avatar_url, couple_id, status, is_deleted) VALUES
                (801, 'bomb-openid-sentinel', 'bomb-nickname-sentinel',
                 'https://avatar.invalid/bomb-sentinel', 81, 1, 0),
                (802, 'bomb-two', 'bomb-partner', NULL, 81, 1, 0),
                (901, 'bomb-three', NULL, NULL, 91, 1, 0),
                (902, 'bomb-four', NULL, NULL, 91, 1, 0),
                (1001, 'bomb-unbound', NULL, NULL, NULL, 1, 0),
                (1101, 'bomb-orphan', NULL, NULL, 71, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status) VALUES
                (81, 'BOMB-ONE', 801, 802, 1), (91, 'BOMB-TWO', 901, 902, 1),
                (71, 'BOMB-ORPHAN', 1101, NULL, 1)
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
                {id_: _headers(id_) for id_ in (801, 802, 901, 902, 1001, 1101)},
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, auth, _ = sweet_bomb_context
    first_answer = "first-answer-sentinel"
    later_answers = ["later-answer-one", "later-answer-two", "later-answer-three"]
    auth_token = auth[801]["Authorization"]
    generated_content = "generated-content-sentinel"

    def choose(values: object) -> object:
        sequence = list(cast(list[object], values))
        return "question" if tuple(sequence) == sweet_bomb._BOMB_TYPES else sequence[0]

    monkeypatch.setattr(sweet_bomb, "_QUESTIONS", (generated_content,))
    monkeypatch.setattr(sweet_bomb.secrets, "choice", choose)
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
            result = await connection.execute(
                text(
                    """
                    INSERT INTO t_sweet_bomb
                    (couple_id, bomb_type, content, sent_time, is_read, is_answered)
                    VALUES (91, 'question', '{}', NOW(), 0, 0)
                    """
                )
            )
            foreign_bomb_id = int(result.lastrowid)
        unread = _payload(await client.get("/api/sweetBomb/unread", headers=auth[802]))["data"]
        history = _payload(await client.get("/api/sweetBomb/history", headers=auth[802]))["data"]
        assert [item["id"] for item in unread] == [bomb_id]
        assert [item["id"] for item in history] == [bomb_id]
        assert foreign_bomb_id not in [item["id"] for item in unread]
        assert (
            _payload(await client.get("/api/sweetBomb/unread/count", headers=auth[802]))["data"]
            == 1
        )
        assert (await client.get(f"/api/sweetBomb/detail/{bomb_id}", headers=auth[901])).json()[
            "code"
        ] == 3002
        cross_read = await client.post(f"/api/sweetBomb/read/{bomb_id}", headers=auth[901])
        cross_answer = await client.post(
            f"/api/sweetBomb/answer/{bomb_id}",
            headers=auth[901],
            params={"answerContent": "cross-couple-answer"},
        )
        assert _payload(cross_read)["code"] == 3002
        assert _payload(cross_answer)["code"] == 3002
        reads = await asyncio.gather(
            *[client.post(f"/api/sweetBomb/read/{bomb_id}", headers=auth[802]) for _ in range(4)]
        )
        assert all(_payload(response)["code"] == 200 for response in reads)
        first = await client.post(
            f"/api/sweetBomb/answer/{bomb_id}",
            headers=auth[802],
            params={"answerContent": first_answer},
        )
        assert _payload(first)["code"] == 200
        answers = await asyncio.gather(
            *[
                client.post(
                    f"/api/sweetBomb/answer/{bomb_id}",
                    headers=auth[802],
                    params={"answerContent": answer},
                )
                for answer in later_answers
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
    assert rows[0]["answer_content"] == first_answer
    notification_rows = await _rows(
        engine,
        (
            "SELECT id FROM t_notification WHERE user_id = 802 "
            "AND related_id = :id AND related_type = 'sweet_bomb'"
        ),
        id=bomb_id,
    )
    assert len(notification_rows) == 1
    log_text = str(logs)
    for sentinel in (
        generated_content,
        first_answer,
        *later_answers,
        "bomb-openid-sentinel",
        "bomb-nickname-sentinel",
        "https://avatar.invalid/bomb-sentinel",
        auth_token,
        auth_token.removeprefix("Bearer "),
        "Authorization",
    ):
        assert sentinel not in log_text
    sweet_bomb_events = [item for item in logs if item.get("module") == "sweet_bomb"]
    assert sweet_bomb_events
    allowed_keys = {
        "event",
        "log_level",
        "requestId",
        "module",
        "operation",
        "result",
        "durationMs",
        "errorCode",
    }
    assert all(set(item) <= allowed_keys for item in sweet_bomb_events)


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


@pytest.mark.integration
async def test_sweet_bomb_rejects_empty_partner_and_excludes_soft_deleted_statistics(
    sweet_bomb_context: tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, auth, _ = sweet_bomb_context
    orphan = await client.post("/api/sweetBomb/generate", headers=auth[1101])
    assert _payload(orphan)["code"] == 2006
    assert await _rows(engine, "SELECT id FROM t_sweet_bomb WHERE couple_id = 71") == []
    assert await _rows(engine, "SELECT id FROM t_notification WHERE user_id = 1101") == []

    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_couple_menu
                (couple_id, creator_id, restaurant_name, is_deleted) VALUES
                (81, 801, 'live-menu', 0), (81, 801, 'deleted-menu', 1)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_anniversary
                (couple_id, creator_id, name, anniversary_date, anniversary_type, is_deleted) VALUES
                (81, 801, 'live-anniversary', :today, 1, 0),
                (81, 801, 'deleted-anniversary', :today, 1, 1)
                """
            ),
            {"today": date.today()},
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_time_capsule
                (couple_id, creator_id, capsule_type, title, unlock_date, is_deleted) VALUES
                (81, 801, 'text', 'live-capsule', :today, 0),
                (81, 801, 'text', 'deleted-capsule', :today, 1)
                """
            ),
            {"today": date.today()},
        )

    monkeypatch.setattr(sweet_bomb.secrets, "choice", lambda values: "data")
    generated = _payload(await client.post("/api/sweetBomb/generate", headers=auth[801]))
    assert generated["code"] == 200
    assert generated["data"]["bombType"] == "data"
    assert generated["data"]["content"]["statsData"] == {
        "totalDates": 1,
        "totalAnniversaries": 1,
        "totalCapsules": 1,
    }


@pytest.mark.integration
@pytest.mark.parametrize(
    ("bomb_type", "expected_field"),
    [
        ("memory", "memoryData"),
        ("data", "statsData"),
        ("question", "question"),
        ("festival", "extraInfo"),
    ],
)
async def test_sweet_bomb_generates_each_contract_content_shape_as_json(
    sweet_bomb_context: tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient],
    monkeypatch: pytest.MonkeyPatch,
    bomb_type: str,
    expected_field: str,
) -> None:
    client, engine, auth, _ = sweet_bomb_context

    def choose(values: object) -> object:
        sequence = list(cast(list[object], values))
        return bomb_type if tuple(sequence) == sweet_bomb._BOMB_TYPES else sequence[0]

    monkeypatch.setattr(sweet_bomb.secrets, "choice", choose)
    response = _payload(await client.post("/api/sweetBomb/generate", headers=auth[801]))
    data = cast(dict[str, object], response["data"])
    assert data["bombType"] == bomb_type
    assert isinstance(data["content"], dict)
    content = cast(dict[str, object], data["content"])
    assert expected_field in content
    rows = await _rows(engine, "SELECT content FROM t_sweet_bomb WHERE id = :id", id=data["id"])
    assert isinstance(json.loads(cast(str, rows[0]["content"])), dict)


@pytest.mark.integration
async def test_non_question_answer_rejects_without_changing_record(
    sweet_bomb_context: tuple[AsyncClient, AsyncEngine, dict[int, dict[str, str]], RedisClient],
) -> None:
    client, engine, auth, _ = sweet_bomb_context
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                INSERT INTO t_sweet_bomb
                (couple_id, bomb_type, content, sent_time, is_read, is_answered)
                VALUES (81, 'festival', '{}', NOW(), 0, 0)
                """
            )
        )
        bomb_id = int(result.lastrowid)
    rejected = await client.post(
        f"/api/sweetBomb/answer/{bomb_id}",
        headers=auth[802],
        params={"answerContent": "must-not-write"},
    )
    assert _payload(rejected)["code"] == 400
    rows = await _rows(
        engine,
        "SELECT is_answered, answer_content, answer_time FROM t_sweet_bomb WHERE id = :id",
        id=bomb_id,
    )
    assert rows == [{"is_answered": 0, "answer_content": None, "answer_time": None}]
