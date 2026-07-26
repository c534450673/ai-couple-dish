import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Table, text
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
from app.db.models import Notification
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient

SECRET = "n" * 64
TOKEN_EXPIRATION_MS = 300_000
ATTACKER_ID = 901
VICTIM_ID = 902
ATTACKER_NOTIFICATION_ID = 9101
VICTIM_READ_TARGET_ID = 9201
VICTIM_DELETE_TARGET_ID = 9202
logger = logging.getLogger(__name__)


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, SECRET, expiration_ms=TOKEN_EXPIRATION_MS)
    return {"Authorization": f"Bearer {token}"}


@dataclass(frozen=True)
class NotificationContext:
    client: AsyncClient
    engine: AsyncEngine
    attacker_headers: dict[str, str]


@pytest.fixture
async def notification_context(
    mysql_url: str, redis_url: str
) -> AsyncIterator[NotificationContext]:
    engine = create_async_engine(mysql_url)
    redis = RedisClient(redis_url)
    try:
        async with engine.begin() as connection:
            notification_table = cast(Table, Notification.__table__)
            await connection.run_sync(
                lambda sync_connection: notification_table.drop(sync_connection, checkfirst=True)
            )
            await connection.run_sync(
                lambda sync_connection: notification_table.create(sync_connection, checkfirst=False)
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO t_notification (id, user_id, type, title, is_read)
                    VALUES
                        (:attacker_notification_id, :attacker_id, 1, 'attacker-own', 0),
                        (:victim_read_target_id, :victim_id, 1, 'victim-read-target', 0),
                        (:victim_delete_target_id, :victim_id, 1, 'victim-delete-target', 0)
                    """
                ),
                {
                    "attacker_notification_id": ATTACKER_NOTIFICATION_ID,
                    "attacker_id": ATTACKER_ID,
                    "victim_read_target_id": VICTIM_READ_TARGET_ID,
                    "victim_delete_target_id": VICTIM_DELETE_TARGET_ID,
                    "victim_id": VICTIM_ID,
                },
            )
        logger.info(
            "notification_isolation_seed_completed "
            "attacker_id=%s victim_id=%s notification_count=3",
            ATTACKER_ID,
            VICTIM_ID,
        )

        await redis.connect()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        app = create_app(_settings())
        app.state.redis = redis

        async def session_override() -> AsyncIterator[AsyncSession]:
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = session_override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield NotificationContext(client, engine, _headers(ATTACKER_ID))
    finally:
        await redis.close()
        await engine.dispose()


@pytest.mark.integration
async def test_notification_write_routes_isolate_other_users(
    notification_context: NotificationContext,
) -> None:
    client = notification_context.client
    headers = notification_context.attacker_headers

    responses = [
        await client.put(f"/api/notification/read/{VICTIM_READ_TARGET_ID}", headers=headers),
        await client.delete(f"/api/notification/delete/{VICTIM_DELETE_TARGET_ID}", headers=headers),
        await client.put("/api/notification/readAll", headers=headers),
    ]
    for response in responses:
        assert response.status_code == 200
        assert response.json() == {"code": 200, "message": "操作成功", "data": None}

    async with notification_context.engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT id, user_id, is_read, read_time
                    FROM t_notification
                    WHERE id IN (
                        :attacker_notification_id,
                        :victim_read_target_id,
                        :victim_delete_target_id
                    )
                    ORDER BY id
                    """
                    ),
                    {
                        "attacker_notification_id": ATTACKER_NOTIFICATION_ID,
                        "victim_read_target_id": VICTIM_READ_TARGET_ID,
                        "victim_delete_target_id": VICTIM_DELETE_TARGET_ID,
                    },
                )
            )
            .mappings()
            .all()
        )

    assert len(rows) == 3
    rows_by_id = {int(row["id"]): row for row in rows}
    attacker_notification = rows_by_id[ATTACKER_NOTIFICATION_ID]
    assert int(attacker_notification["user_id"]) == ATTACKER_ID
    assert int(attacker_notification["is_read"]) == 1
    assert attacker_notification["read_time"] is not None

    for notification_id in (VICTIM_READ_TARGET_ID, VICTIM_DELETE_TARGET_ID):
        victim_notification = rows_by_id[notification_id]
        assert int(victim_notification["user_id"]) == VICTIM_ID
        assert int(victim_notification["is_read"]) == 0
        assert victim_notification["read_time"] is None

    logger.info(
        "notification_isolation_verified attacker_id=%s victim_id=%s routes=read,delete,readAll",
        ATTACKER_ID,
        VICTIM_ID,
    )
