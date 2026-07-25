import asyncio
import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

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

logger = logging.getLogger(__name__)
SECRET = "i" * 64


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
async def invite_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
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
    token = create_access_token(user_id, SECRET, expiration_ms=300_000)
    return {"Authorization": f"Bearer {token}"}


class InviteContext:
    def __init__(self, client: AsyncClient, engine: AsyncEngine, redis: RedisClient) -> None:
        self.client = client
        self.engine = engine
        self.redis = redis
        self.auth = {user_id: _headers(user_id) for user_id in (601, 602, 603)}


async def _seed(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, nick_name, avatar_url, status, is_deleted)
                VALUES
                    (601, 'invite-a', '邀请甲', 'https://avatar.invalid/a', 1, 0),
                    (602, 'invite-b', '邀请乙', 'https://avatar.invalid/b', 1, 0),
                    (603, 'invite-c', '邀请丙', 'https://avatar.invalid/c', 1, 0)
                """
            )
        )


@pytest.fixture
async def invite_context(
    invite_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[InviteContext]:
    await _seed(invite_engine)
    redis = RedisClient(redis_url)
    await redis.connect()
    factory = async_sessionmaker(invite_engine, expire_on_commit=False)
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield InviteContext(client, invite_engine, redis)
    finally:
        await redis.close()


def _payload(response: Response) -> dict[str, Any]:
    body = response.json()
    assert set(body) == {"code", "message", "data"}, body
    return body


def _code(response: Response) -> int:
    return int(_payload(response)["code"])


async def _rows(engine: AsyncEngine, statement: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), params)
        return [dict(row) for row in result.mappings().all()]


@pytest.mark.integration
async def test_invite_code_creation_is_idempotent_under_concurrency(
    invite_context: InviteContext,
) -> None:
    context = invite_context
    responses = await asyncio.gather(
        *[context.client.get("/api/invite/code", headers=context.auth[601]) for _ in range(8)]
    )
    assert all(_code(response) == 200 for response in responses)
    codes = {_payload(response)["data"]["inviteCode"] for response in responses}
    assert len(codes) == 1
    assert await _rows(context.engine, "SELECT COUNT(*) AS count FROM t_user_invite_code") == [
        {"count": 1}
    ]


@pytest.mark.integration
async def test_invite_use_locks_invitee_and_increments_once(
    invite_context: InviteContext,
) -> None:
    context = invite_context
    code_response = await context.client.get("/api/invite/code", headers=context.auth[601])
    invite_code = _payload(code_response)["data"]["inviteCode"]
    responses = await asyncio.gather(
        *[
            context.client.post(
                "/api/invite/use",
                params={"inviteCode": invite_code},
                headers=context.auth[602],
            )
            for _ in range(6)
        ]
    )
    assert [_code(response) for response in responses] == [200] * 6
    assert await _rows(
        context.engine,
        "SELECT invite_count FROM t_user_invite_code WHERE user_id = 601",
    ) == [{"invite_count": 1}]
    assert await _rows(
        context.engine,
        "SELECT inviter_id, invitee_id, reward_amount FROM t_user_referral",
    ) == [{"inviter_id": 601, "invitee_id": 602, "reward_amount": Decimal("5.00")}]
    referrals = await context.client.get("/api/invite/referrals", headers=context.auth[601])
    assert _payload(referrals)["data"][0]["rewardAmount"] == 5.0


@pytest.mark.integration
async def test_invite_stats_rank_validate_info_and_isolation(
    invite_context: InviteContext,
) -> None:
    context = invite_context
    first = _payload(await context.client.get("/api/invite/code", headers=context.auth[601]))[
        "data"
    ]["inviteCode"]
    second = _payload(await context.client.get("/api/invite/code", headers=context.auth[603]))[
        "data"
    ]["inviteCode"]
    await context.client.post(
        "/api/invite/use", params={"inviteCode": first}, headers=context.auth[602]
    )
    await context.client.post(
        "/api/invite/use", params={"inviteCode": second}, headers=context.auth[601]
    )

    async with context.engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE t_user_referral SET bind_couple_time = :bound, reward_amount = :amount "
                "WHERE inviter_id = 601"
            ),
            {"bound": datetime(2026, 7, 26, 12), "amount": Decimal("15.00")},
        )

    stats = await context.client.get("/api/invite/stats", headers=context.auth[601])
    stats_data = _payload(stats)["data"]
    assert stats_data["totalInvites"] == 1
    assert stats_data["boundCoupleCount"] == 1
    assert stats_data["pendingBindCount"] == 0
    assert stats_data["totalRewardAmount"] == 15.0
    assert stats_data["pendingRewardAmount"] == 15.0

    referrals = await context.client.get("/api/invite/referrals", headers=context.auth[601])
    assert _payload(referrals)["data"][0]["inviteeId"] == 602
    isolated = await context.client.get("/api/invite/referrals", headers=context.auth[602])
    assert _payload(isolated)["data"] == []

    rank = await context.client.get("/api/invite/rank", headers=context.auth[601])
    assert [_item["userId"] for _item in _payload(rank)["data"][:2]] == [601, 603]
    assert (
        _payload(
            await context.client.get(
                "/api/invite/validate", params={"inviteCode": first}, headers=context.auth[602]
            )
        )["data"]
        is True
    )
    assert (
        _payload(
            await context.client.get(
                "/api/invite/validate",
                params={"inviteCode": "NOT-FOUND"},
                headers=context.auth[602],
            )
        )["data"]
        is False
    )
    info = await context.client.get(f"/api/invite/info/{first}", headers=context.auth[602])
    assert _payload(info)["data"]["inviteCode"] == first
    missing = await context.client.get("/api/invite/info/NOT-FOUND", headers=context.auth[602])
    assert _code(missing) == 404


@pytest.mark.integration
async def test_invite_use_invalid_inputs_are_noop_and_logs_redact_data(
    invite_context: InviteContext,
) -> None:
    context = invite_context
    response = await context.client.get("/api/invite/code", headers=context.auth[601])
    invite_code = _payload(response)["data"]["inviteCode"]
    with capture_logs() as logs:
        blank = await context.client.post(
            "/api/invite/use", params={"inviteCode": "   "}, headers=context.auth[602]
        )
        self_use = await context.client.post(
            "/api/invite/use", params={"inviteCode": invite_code}, headers=context.auth[601]
        )
    assert _code(blank) == 200
    assert _code(self_use) == 200
    text_logs = str(logs)
    assert invite_code not in text_logs
    assert "邀请甲" not in text_logs
    assert "avatar.invalid" not in text_logs


@pytest.mark.integration
async def test_invite_use_failure_rolls_back_referral_and_counter(
    invite_context: InviteContext,
) -> None:
    context = invite_context
    invite_code = _payload(await context.client.get("/api/invite/code", headers=context.auth[601]))[
        "data"
    ]["inviteCode"]
    async with context.engine.begin() as connection:
        await connection.exec_driver_sql(
            "ALTER TABLE t_user_invite_code "
            "ADD CONSTRAINT reject_invite_count CHECK (invite_count <= 0)"
        )
    response = await context.client.post(
        "/api/invite/use", params={"inviteCode": invite_code}, headers=context.auth[602]
    )
    assert response.status_code == 500
    assert await _rows(
        context.engine,
        "SELECT invite_count FROM t_user_invite_code WHERE user_id = 601",
    ) == [{"invite_count": 0}]
    assert await _rows(context.engine, "SELECT COUNT(*) AS count FROM t_user_referral") == [
        {"count": 0}
    ]
