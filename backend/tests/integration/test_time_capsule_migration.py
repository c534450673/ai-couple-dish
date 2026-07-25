import asyncio
import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import date, timedelta
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
TOKEN_EXPIRATION_MS = 300_000
logger = logging.getLogger(__name__)


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
    schema_path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = schema_path.read_text()
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_time_capsule_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        logger.info("time_capsule_schema_ready tables_source=schema-test.sql")
        yield engine
    finally:
        await engine.dispose()


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, SECRET, expiration_ms=TOKEN_EXPIRATION_MS)
    return {"Authorization": f"Bearer {token}"}


class TimeCapsuleContext:
    def __init__(self, client: AsyncClient, engine: AsyncEngine, auth: dict[int, dict[str, str]]):
        self.client = client
        self.engine = engine
        self.auth = auth


async def _seed(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, nick_name, couple_id, status, is_deleted)
                VALUES
                    (301, 'capsule-user-one', '胶囊甲', 31, 1, 0),
                    (302, 'capsule-user-two', '胶囊乙', 31, 1, 0),
                    (401, 'capsule-outsider-one', '隔离丙', 41, 1, 0),
                    (402, 'capsule-outsider-two', '隔离丁', 41, 1, 0),
                    (501, 'capsule-unbound', '未绑定戊', NULL, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status)
                VALUES
                    (31, 'CAPSULE-COUPLE-ONE', 301, 302, 1),
                    (41, 'CAPSULE-COUPLE-TWO', 401, 402, 1)
                """
            )
        )
    logger.info(
        "time_capsule_seed_completed couples=%s users=%s", [31, 41], [301, 302, 401, 402, 501]
    )


@pytest.fixture
async def time_capsule_context(
    mysql_time_capsule_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[TimeCapsuleContext]:
    await _seed(mysql_time_capsule_engine)
    redis = RedisClient(redis_url)
    await redis.connect()
    assert await redis.raw.ping() is True
    session_factory = async_sessionmaker(mysql_time_capsule_engine, expire_on_commit=False)
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield TimeCapsuleContext(
                client,
                mysql_time_capsule_engine,
                {user_id: _headers(user_id) for user_id in (301, 302, 401, 402, 501)},
            )
    finally:
        await redis.close()


def _payload(response: Response) -> dict[str, Any]:
    payload = response.json()
    assert response.status_code in {200, 400, 500}, payload
    assert set(payload) == {"code", "message", "data"}
    return cast(dict[str, Any], payload)


def _code(response: Response) -> int:
    return int(_payload(response)["code"])


async def _rows(engine: AsyncEngine, statement: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), params)
        return [dict(row) for row in result.mappings().all()]


async def _create(
    context: TimeCapsuleContext,
    user_id: int,
    *,
    unlock_date: date,
    title: str = "给未来的信",
    content: str = "只给伴侣看的正文",
) -> int:
    request_date = max(unlock_date, date.today() + timedelta(days=1))
    response = await context.client.post(
        "/api/timeCapsule/create",
        headers=context.auth[user_id],
        json={
            "capsuleType": "text",
            "title": title,
            "content": content,
            "mediaUrls": ["https://private.example/media.jpg"],
            "unlockDate": request_date.isoformat(),
        },
    )
    assert _code(response) == 200, response.json()
    capsule_id = int(_payload(response)["data"])
    if unlock_date != request_date:
        async with context.engine.begin() as connection:
            await connection.execute(
                text("UPDATE t_time_capsule SET unlock_date = :unlock_date WHERE id = :id"),
                {"unlock_date": unlock_date, "id": capsule_id},
            )
    return capsule_id


@pytest.mark.integration
async def test_time_capsule_content_is_hidden_until_unlock_and_pending_is_scoped(
    time_capsule_context: TimeCapsuleContext,
) -> None:
    context = time_capsule_context
    capsule_id = await _create(context, 301, unlock_date=date.today() + timedelta(days=2))

    detail = await context.client.get(
        f"/api/timeCapsule/detail/{capsule_id}", headers=context.auth[302]
    )
    assert _code(detail) == 200
    detail_data = _payload(detail)["data"]
    assert detail_data["content"] != "只给伴侣看的正文"
    assert detail_data["mediaUrls"] is None
    assert detail_data["status"] == 0

    pending = await context.client.get("/api/timeCapsule/pending", headers=context.auth[302])
    assert _code(pending) == 200
    assert pending.json()["data"] == []

    due_id = await _create(context, 301, unlock_date=date.today() - timedelta(days=1))
    pending_due = await context.client.get("/api/timeCapsule/pending", headers=context.auth[302])
    assert _code(pending_due) == 200
    assert [item["id"] for item in pending_due.json()["data"]] == [due_id]

    outsider = await context.client.get(
        f"/api/timeCapsule/detail/{capsule_id}", headers=context.auth[401]
    )
    assert _code(outsider) == 9999


@pytest.mark.integration
async def test_time_capsule_unlock_is_single_transition_and_single_notification(
    time_capsule_context: TimeCapsuleContext,
) -> None:
    context = time_capsule_context
    capsule_id = await _create(context, 301, unlock_date=date.today() - timedelta(days=1))
    responses = await asyncio.gather(
        *[
            context.client.post(f"/api/timeCapsule/unlock/{capsule_id}", headers=context.auth[302])
            for _ in range(6)
        ]
    )
    codes = [_code(response) for response in responses]
    logger.info("time_capsule_concurrent_result operation=unlock codes=%s", codes)
    assert codes.count(200) == 1
    assert all(code in {200, 400, 9999} for code in codes)

    capsule_rows = await _rows(
        context.engine,
        "SELECT status, unlock_time, is_deleted FROM t_time_capsule WHERE id = :id",
        id=capsule_id,
    )
    notification_rows = await _rows(
        context.engine,
        """
        SELECT id, user_id, related_id, related_type
        FROM t_notification
        WHERE user_id = :user_id AND related_id = :capsule_id AND related_type = 'time_capsule'
        """,
        user_id=301,
        capsule_id=capsule_id,
    )
    assert capsule_rows == [
        {"status": 1, "unlock_time": capsule_rows[0]["unlock_time"], "is_deleted": 0}
    ]
    assert len(notification_rows) == 1


@pytest.mark.integration
async def test_time_capsule_create_failure_rolls_back_and_unbind_rejects_business_operations(
    time_capsule_context: TimeCapsuleContext,
) -> None:
    context = time_capsule_context
    invalid = await context.client.post(
        "/api/timeCapsule/create",
        headers=context.auth[301],
        json={
            "capsuleType": "text",
            "title": "非法日期",
            "content": "不应落库",
            "unlockDate": date.today().isoformat(),
        },
    )
    assert _code(invalid) in {400, 9001}
    assert (
        await _rows(
            context.engine,
            "SELECT id FROM t_time_capsule WHERE title = '非法日期'",
        )
        == []
    )

    capsule_id = await _create(context, 301, unlock_date=date.today() - timedelta(days=1))
    async with context.engine.begin() as connection:
        await connection.execute(text("UPDATE t_couple SET status = 2 WHERE id = 31"))

    blocked_list = await context.client.get("/api/timeCapsule/list", headers=context.auth[301])
    blocked_detail = await context.client.get(
        f"/api/timeCapsule/detail/{capsule_id}", headers=context.auth[302]
    )
    blocked_unlock = await context.client.post(
        f"/api/timeCapsule/unlock/{capsule_id}", headers=context.auth[302]
    )
    blocked_create = await context.client.post(
        "/api/timeCapsule/create",
        headers=context.auth[301],
        json={
            "capsuleType": "text",
            "title": "解绑期间不应创建",
            "content": "不应落库",
            "unlockDate": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    assert all(
        _code(response) == 2006
        for response in (blocked_list, blocked_detail, blocked_unlock, blocked_create)
    )
    assert (
        await _rows(
            context.engine,
            "SELECT id FROM t_time_capsule WHERE title = '解绑期间不应创建'",
        )
        == []
    )


@pytest.mark.integration
async def test_time_capsule_delete_is_creator_only_and_soft_deletes_from_lists(
    time_capsule_context: TimeCapsuleContext,
) -> None:
    context = time_capsule_context
    capsule_id = await _create(context, 301, unlock_date=date.today() + timedelta(days=1))

    partner_delete = await context.client.delete(
        f"/api/timeCapsule/delete/{capsule_id}", headers=context.auth[302]
    )
    assert _code(partner_delete) == 3002

    creator_delete = await context.client.delete(
        f"/api/timeCapsule/delete/{capsule_id}", headers=context.auth[301]
    )
    assert _code(creator_delete) == 200
    rows = await _rows(
        context.engine,
        "SELECT is_deleted FROM t_time_capsule WHERE id = :id",
        id=capsule_id,
    )
    assert rows == [{"is_deleted": 1}]
    listed = await context.client.get("/api/timeCapsule/list", headers=context.auth[302])
    assert _code(listed) == 200
    assert listed.json()["data"] == []


@pytest.mark.integration
async def test_time_capsule_logs_are_redacted_and_unlock_updates_visible_payload(
    time_capsule_context: TimeCapsuleContext,
) -> None:
    context = time_capsule_context
    private_content = "capsule-secret-body"
    private_media = "https://private.example/secret.mp4"
    capsule_id = await _create(
        context,
        301,
        unlock_date=date.today() + timedelta(days=2),
        title="capsule-private-title",
        content=private_content,
    )
    async with context.engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE t_time_capsule SET media_urls = :media, unlock_date = :unlock_date "
                "WHERE id = :id"
            ),
            {
                "media": '["https://private.example/secret.mp4"]',
                "unlock_date": date.today() - timedelta(days=1),
                "id": capsule_id,
            },
        )
    with capture_logs() as logs:
        response = await context.client.post(
            f"/api/timeCapsule/unlock/{capsule_id}", headers=context.auth[302]
        )
    assert _code(response) == 200
    visible = _payload(response)["data"]
    assert visible["content"] == private_content
    assert visible["mediaUrls"] == [private_media]
    assert private_content not in str(logs)
    assert private_media not in str(logs)
    assert "capsule-private-title" not in str(logs)
    assert "capsule-user-one" not in str(logs)
    assert "requestId" in str(logs)
    assert "durationMs" in str(logs)
