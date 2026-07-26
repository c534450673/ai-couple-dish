import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
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

from app.core.auth import create_access_token, decode_access_token
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient
from app.redis.keys import logout_blacklist_key
from app.services import challenge as challenge_service

SECRET = "c" * 64


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
async def challenge_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url, pool_size=12, max_overflow=4)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
            await connection.execute(
                text(
                    """INSERT INTO t_user
                    (id,openid,nick_name,avatar_url,couple_id,status,is_deleted)
                    VALUES (101,'u101','甲','avatar-a',11,1,0),(102,'u102','乙',NULL,11,1,0),
                           (201,'u201','丙',NULL,22,1,0),(202,'u202','丁',NULL,22,1,0),
                           (301,'u301','未绑定',NULL,NULL,1,0)"""
                )
            )
            await connection.execute(
                text(
                    """INSERT INTO t_couple (id,couple_code,user_1_id,user_2_id,status)
                    VALUES (11,'C11',101,102,1),(22,'C22',201,202,1)"""
                )
            )
        yield engine
    finally:
        await engine.dispose()


class Context:
    def __init__(self, client: AsyncClient, engine: AsyncEngine, redis: RedisClient) -> None:
        self.client = client
        self.engine = engine
        self.redis = redis
        self.auth = {user_id: _headers(user_id) for user_id in (101, 102, 201, 202, 301)}


@pytest.fixture
async def context(challenge_engine: AsyncEngine, redis_url: str) -> AsyncIterator[Context]:
    redis = RedisClient(redis_url)
    await redis.connect()
    app = create_app(_settings())
    app.state.redis = redis
    factory = async_sessionmaker(challenge_engine, expire_on_commit=False)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                await challenge_service.logger.awarning(
                    "database_session_rolled_back",
                    module="database",
                    operation="rollback",
                    result="completed",
                    dependency="database",
                )
                raise

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield Context(client, challenge_engine, redis)
    finally:
        await redis.close()


async def _scalar(engine: AsyncEngine, sql: str, **params: Any) -> Any:
    async with engine.connect() as connection:
        return await connection.scalar(text(sql), params)


async def _rows(engine: AsyncEngine, sql: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]


async def _execute(engine: AsyncEngine, sql: str, **params: Any) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), params)


async def _snapshot(context: Context, challenge_id: int) -> tuple[list[dict[str, Any]], int]:
    challenge = await _rows(
        context.engine,
        "SELECT current_days,status,end_date,is_deleted FROM t_challenge WHERE id=:id",
        id=challenge_id,
    )
    records = int(
        await _scalar(
            context.engine,
            "SELECT COUNT(*) FROM t_checkin_record WHERE challenge_id=:id",
            id=challenge_id,
        )
    )
    return challenge, records


async def _create(context: Context, *, target_days: int = 3, user_id: int = 101) -> int:
    response = await context.client.post(
        "/api/challenge/create",
        headers=context.auth[user_id],
        json={
            "challengeType": " sport ",
            "title": " 私密标题 ",
            "description": "私密描述",
            "targetDays": target_days,
            "reward": "私密奖励",
        },
    )
    assert response.json()["code"] == 200
    return int(response.json()["data"])


@pytest.mark.integration
async def test_challenge_happy_path_dto_scope_and_accepted_pending_compatibility(
    context: Context,
) -> None:
    challenge_id = await _create(context)
    accepted = await context.client.post(
        f"/api/challenge/accept/{challenge_id}", headers=context.auth[102]
    )
    assert accepted.json() == {"code": 200, "message": "接受成功", "data": None}
    pending = await context.client.get("/api/challenge/pending", headers=context.auth[102])
    assert [item["id"] for item in pending.json()["data"]] == [challenge_id]
    assert (
        await _scalar(
            context.engine, "SELECT status FROM t_challenge WHERE id=:id", id=challenge_id
        )
        == 0
    )

    checkin = await context.client.post(
        "/api/challenge/checkin",
        headers=context.auth[101],
        json={"challengeId": challenge_id, "content": "正文", "imageUrl": "image"},
    )
    assert checkin.json()["code"] == 200
    record = checkin.json()["data"]
    assert set(record) == {
        "id",
        "challengeId",
        "userId",
        "userName",
        "userAvatar",
        "checkinDate",
        "content",
        "imageUrl",
        "createTime",
    }
    detail = await context.client.get(
        f"/api/challenge/detail/{challenge_id}", headers=context.auth[102]
    )
    data = detail.json()["data"]
    assert set(data) == {
        "id",
        "challengeType",
        "title",
        "description",
        "targetDays",
        "currentDays",
        "status",
        "statusDesc",
        "startDate",
        "endDate",
        "reward",
        "creatorId",
        "partnerId",
        "creatorName",
        "partnerName",
        "createTime",
        "checkinRecords",
        "todayChecked",
        "progressPercent",
    }
    assert data["challengeType"] == "sport"
    assert data["title"] == "私密标题"
    assert data["todayChecked"] is False
    assert data["currentDays"] == 1
    records = await context.client.get(
        f"/api/challenge/checkin-records/{challenge_id}?pageNum=1&pageSize=10",
        headers=context.auth[102],
    )
    assert records.json()["data"]["total"] == 1
    outsider = await context.client.get(
        f"/api/challenge/detail/{challenge_id}", headers=context.auth[201]
    )
    assert outsider.json() == {"code": 9999, "message": "无权访问该挑战", "data": None}


@pytest.mark.integration
async def test_same_user_eight_concurrent_checkins_are_idempotent(context: Context) -> None:
    challenge_id = await _create(context, target_days=3)
    responses = await asyncio.gather(
        *[
            context.client.post(
                "/api/challenge/checkin",
                headers=context.auth[101],
                json={"challengeId": challenge_id, "content": "same"},
            )
            for _ in range(8)
        ]
    )
    payloads = [response.json() for response in responses]
    assert all(payload["code"] == 200 for payload in payloads)
    assert len({payload["data"]["id"] for payload in payloads}) == 1
    assert (
        await _scalar(
            context.engine,
            "SELECT COUNT(*) FROM t_checkin_record WHERE challenge_id=:id AND user_id=101",
            id=challenge_id,
        )
        == 1
    )
    assert (
        await _scalar(
            context.engine, "SELECT current_days FROM t_challenge WHERE id=:id", id=challenge_id
        )
        == 1
    )


@pytest.mark.integration
async def test_two_users_same_day_contribute_one_progress_day_without_lost_insert(
    context: Context,
) -> None:
    challenge_id = await _create(context, target_days=3)
    async with context.engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO t_checkin_record (challenge_id,user_id,checkin_date,content) "
                "VALUES (:id,101,:day,'old')"
            ),
            {"id": challenge_id, "day": date.today() - timedelta(days=1)},
        )
    responses = await asyncio.gather(
        *[
            context.client.post(
                "/api/challenge/checkin",
                headers=context.auth[user_id],
                json={"challengeId": challenge_id},
            )
            for user_id in (101, 102)
        ]
    )
    assert all(response.json()["code"] == 200 for response in responses)
    assert (
        await _scalar(
            context.engine,
            "SELECT COUNT(*) FROM t_checkin_record WHERE challenge_id=:id",
            id=challenge_id,
        )
        == 3
    )
    assert (
        await _scalar(
            context.engine, "SELECT current_days FROM t_challenge WHERE id=:id", id=challenge_id
        )
        == 2
    )


@pytest.mark.integration
@pytest.mark.parametrize("status", [1, 2, 3])
async def test_terminal_states_reject_all_writes_without_mutation(
    context: Context, status: int
) -> None:
    challenge_id = await _create(context)
    async with context.engine.begin() as connection:
        await connection.execute(
            text("UPDATE t_challenge SET status=:status WHERE id=:id"),
            {"status": status, "id": challenge_id},
        )
    responses = [
        await context.client.post(
            f"/api/challenge/accept/{challenge_id}", headers=context.auth[102]
        ),
        await context.client.post(
            f"/api/challenge/reject/{challenge_id}", headers=context.auth[102]
        ),
        await context.client.post(
            f"/api/challenge/cancel/{challenge_id}", headers=context.auth[101]
        ),
        await context.client.post(
            "/api/challenge/checkin", headers=context.auth[101], json={"challengeId": challenge_id}
        ),
    ]
    assert all(response.json()["code"] == 9999 for response in responses)
    assert (
        await _scalar(
            context.engine, "SELECT status FROM t_challenge WHERE id=:id", id=challenge_id
        )
        == status
    )
    assert (
        await _scalar(
            context.engine,
            "SELECT COUNT(*) FROM t_checkin_record WHERE challenge_id=:id",
            id=challenge_id,
        )
        == 0
    )


@pytest.mark.integration
async def test_future_start_rejected_and_unbound_user_cannot_create(context: Context) -> None:
    response = await context.client.post(
        "/api/challenge/create",
        headers=context.auth[101],
        json={
            "challengeType": "future",
            "title": "future",
            "targetDays": 2,
            "startDate": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    challenge_id = response.json()["data"]
    rejected = await context.client.post(
        "/api/challenge/checkin", headers=context.auth[101], json={"challengeId": challenge_id}
    )
    assert rejected.json() == {"code": 9999, "message": "挑战尚未开始", "data": None}
    unbound = await context.client.post(
        "/api/challenge/create",
        headers=context.auth[301],
        json={"challengeType": "x", "title": "x", "targetDays": 1},
    )
    assert unbound.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}


@pytest.mark.integration
async def test_completion_threshold_is_linearized_for_two_concurrent_users(
    context: Context,
) -> None:
    challenge_id = await _create(context, target_days=2)
    await _execute(
        context.engine,
        "INSERT INTO t_checkin_record (challenge_id,user_id,checkin_date,content) "
        "VALUES (:id,101,:day,'old')",
        id=challenge_id,
        day=date.today() - timedelta(days=1),
    )
    responses = await asyncio.gather(
        *[
            context.client.post(
                "/api/challenge/checkin",
                headers=context.auth[user_id],
                json={"challengeId": challenge_id},
            )
            for user_id in (101, 102)
        ]
    )
    payloads = [response.json() for response in responses]
    assert sorted(payload["code"] for payload in payloads) == [200, 9999]
    rejected = next(payload for payload in payloads if payload["code"] == 9999)
    assert rejected["message"] == "挑战状态不允许操作"
    assert await _rows(
        context.engine,
        "SELECT current_days,status,end_date FROM t_challenge WHERE id=:id",
        id=challenge_id,
    ) == [{"current_days": 2, "status": 1, "end_date": date.today()}]
    assert (
        await _scalar(
            context.engine,
            "SELECT COUNT(*) FROM t_checkin_record WHERE challenge_id=:id",
            id=challenge_id,
        )
        == 2
    )


@pytest.mark.integration
async def test_checkin_failure_after_flush_rolls_back_and_logs_safely(
    context: Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    challenge_id = await _create(context)
    before = await _snapshot(context, challenge_id)

    async def fail_count(_session: AsyncSession, _challenge_id: int) -> int:
        raise RuntimeError("private-database-failure-marker")

    with monkeypatch.context() as patch, capture_logs() as logs:
        patch.setattr(challenge_service, "_count_progress", fail_count)
        response = await context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[101],
            json={
                "challengeId": challenge_id,
                "content": "private-rollback-content-marker",
                "imageUrl": "https://private.invalid/rollback-image-marker",
            },
        )
    assert response.status_code == 500
    assert response.json() == {
        "code": 500,
        "message": "服务器内部错误，请稍后重试",
        "data": None,
    }
    assert await _snapshot(context, challenge_id) == before
    assert any(entry.get("event") == "database_session_rolled_back" for entry in logs)
    challenge_logs = [entry for entry in logs if entry.get("module") == "challenge"]
    assert len(challenge_logs) == 1
    assert challenge_logs[0]["event"] == "business_operation_failed"
    assert challenge_logs[0]["errorCode"] == "INTERNAL_ERROR"
    serialized = str(logs)
    assert "private-database-failure-marker" not in serialized
    assert "private-rollback-content-marker" not in serialized
    assert "rollback-image-marker" not in serialized
    assert "mysql+asyncmy" not in serialized


@pytest.mark.integration
async def test_after_unbind_all_nine_routes_reject_without_mutation(context: Context) -> None:
    challenge_id = await _create(context)
    before = await _snapshot(context, challenge_id)
    await _execute(context.engine, "UPDATE t_user SET couple_id=NULL WHERE id IN (101,102)")
    await _execute(context.engine, "UPDATE t_couple SET status=0 WHERE id=11")

    requests = [
        context.client.post(
            "/api/challenge/create",
            headers=context.auth[101],
            json={"challengeType": "x", "title": "x", "targetDays": 1},
        ),
        context.client.post(f"/api/challenge/accept/{challenge_id}", headers=context.auth[102]),
        context.client.post(f"/api/challenge/reject/{challenge_id}", headers=context.auth[102]),
        context.client.post(f"/api/challenge/cancel/{challenge_id}", headers=context.auth[101]),
        context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[101],
            json={"challengeId": challenge_id},
        ),
        context.client.get(f"/api/challenge/detail/{challenge_id}", headers=context.auth[101]),
        context.client.get("/api/challenge/list", headers=context.auth[101]),
        context.client.get(
            f"/api/challenge/checkin-records/{challenge_id}", headers=context.auth[101]
        ),
        context.client.get("/api/challenge/pending", headers=context.auth[102]),
    ]
    responses = await asyncio.gather(*requests)
    assert all(
        response.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}
        for response in responses
    )
    assert await _snapshot(context, challenge_id) == before


@pytest.mark.integration
async def test_unbind_and_checkin_race_has_only_complete_linearized_outcomes(
    context: Context,
) -> None:
    challenge_id = await _create(context)

    async def unbind() -> None:
        async with context.engine.begin() as connection:
            await connection.execute(text("SELECT id FROM t_couple WHERE id=11 FOR UPDATE"))
            await connection.execute(text("UPDATE t_user SET couple_id=NULL WHERE id IN (101,102)"))
            await connection.execute(text("UPDATE t_couple SET status=0 WHERE id=11"))

    checkin_response, _ = await asyncio.gather(
        context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[101],
            json={"challengeId": challenge_id},
        ),
        unbind(),
    )
    assert checkin_response.json()["code"] in {200, 2006}
    snapshot = await _snapshot(context, challenge_id)
    if checkin_response.json()["code"] == 200:
        assert snapshot == (
            [{"current_days": 1, "status": 0, "end_date": None, "is_deleted": 0}],
            1,
        )
    else:
        assert snapshot == (
            [{"current_days": 0, "status": 0, "end_date": None, "is_deleted": 0}],
            0,
        )
    assert await _rows(
        context.engine,
        "SELECT couple_id FROM t_user WHERE id IN (101,102) ORDER BY id",
    ) == [{"couple_id": None}, {"couple_id": None}]
    assert await _scalar(context.engine, "SELECT status FROM t_couple WHERE id=11") == 0


@pytest.mark.integration
async def test_role_matrix_and_cross_couple_scope_preserve_rows(context: Context) -> None:
    first_id = await _create(context, user_id=101)
    foreign_id = await _create(context, user_id=201)
    assert [
        item["id"]
        for item in (
            await context.client.get("/api/challenge/list", headers=context.auth[101])
        ).json()["data"]
    ] == [first_id]
    assert [
        item["id"]
        for item in (
            await context.client.get("/api/challenge/list", headers=context.auth[201])
        ).json()["data"]
    ] == [foreign_id]
    assert [
        item["id"]
        for item in (
            await context.client.get("/api/challenge/pending", headers=context.auth[102])
        ).json()["data"]
    ] == [first_id]

    before = await _snapshot(context, first_id)
    outsider_requests = [
        context.client.get(f"/api/challenge/detail/{first_id}", headers=context.auth[201]),
        context.client.get(f"/api/challenge/checkin-records/{first_id}", headers=context.auth[201]),
        context.client.post(f"/api/challenge/accept/{first_id}", headers=context.auth[201]),
        context.client.post(f"/api/challenge/reject/{first_id}", headers=context.auth[201]),
        context.client.post(f"/api/challenge/cancel/{first_id}", headers=context.auth[201]),
        context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[201],
            json={"challengeId": first_id},
        ),
    ]
    outsider_responses = await asyncio.gather(*outsider_requests)
    assert all(
        response.json() == {"code": 9999, "message": "无权访问该挑战", "data": None}
        for response in outsider_responses
    )
    reverse_responses = [
        await context.client.post(f"/api/challenge/accept/{first_id}", headers=context.auth[101]),
        await context.client.post(f"/api/challenge/reject/{first_id}", headers=context.auth[101]),
        await context.client.post(f"/api/challenge/cancel/{first_id}", headers=context.auth[102]),
    ]
    assert [
        (response.json()["code"], response.json()["message"]) for response in reverse_responses
    ] == [
        (9999, "您不是该挑战的伙伴"),
        (9999, "您不是该挑战的伙伴"),
        (9999, "只有创建者可以取消挑战"),
    ]
    assert await _snapshot(context, first_id) == before


@pytest.mark.integration
async def test_competing_transitions_never_overwrite_terminal_state(context: Context) -> None:
    transition_id = await _create(context)
    reject_response, cancel_response = await asyncio.gather(
        context.client.post(f"/api/challenge/reject/{transition_id}", headers=context.auth[102]),
        context.client.post(f"/api/challenge/cancel/{transition_id}", headers=context.auth[101]),
    )
    assert sorted([reject_response.json()["code"], cancel_response.json()["code"]]) == [200, 9999]
    assert (
        await _scalar(
            context.engine, "SELECT status FROM t_challenge WHERE id=:id", id=transition_id
        )
        == 3
    )

    checkin_id = await _create(context, target_days=3)
    checkin_response, competing_cancel = await asyncio.gather(
        context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[101],
            json={"challengeId": checkin_id},
        ),
        context.client.post(f"/api/challenge/cancel/{checkin_id}", headers=context.auth[101]),
    )
    codes = sorted([checkin_response.json()["code"], competing_cancel.json()["code"]])
    assert codes in ([200, 200], [200, 9999])
    challenge_rows, record_count = await _snapshot(context, checkin_id)
    assert challenge_rows[0]["status"] == 3
    assert record_count in {0, 1}
    assert challenge_rows[0]["current_days"] == record_count


@pytest.mark.integration
async def test_real_redis_blacklist_rejects_read_and_write_without_mutation(
    context: Context,
) -> None:
    token = create_access_token(101, SECRET, expiration_ms=300_000)
    claims = decode_access_token(token, SECRET)
    await context.redis.raw.setex(logout_blacklist_key(claims.jti), 300, "1")
    headers = {"Authorization": f"Bearer {token}"}
    before_count = await _scalar(context.engine, "SELECT COUNT(*) FROM t_challenge")
    read_response, write_response = await asyncio.gather(
        context.client.get("/api/challenge/list", headers=headers),
        context.client.post(
            "/api/challenge/create",
            headers=headers,
            json={"challengeType": "x", "title": "x", "targetDays": 1},
        ),
    )
    assert read_response.status_code == write_response.status_code == 401
    assert read_response.json()["code"] == write_response.json()["code"] == 401
    assert await _scalar(context.engine, "SELECT COUNT(*) FROM t_challenge") == before_count


@pytest.mark.integration
async def test_full_dto_paging_sorting_and_challenge_logs_are_private(context: Context) -> None:
    await _execute(
        context.engine,
        "UPDATE t_user SET nick_name='private-nickname-marker', "
        "avatar_url='https://private.invalid/avatar-marker' WHERE id=101",
    )
    private_values = (
        "private-title-marker",
        "private-description-marker",
        "private-reward-marker",
        "private-content-marker",
        "https://private.invalid/image-marker",
        "private-nickname-marker",
        "https://private.invalid/avatar-marker",
        context.auth[101]["Authorization"],
    )
    with capture_logs() as logs:
        created = await context.client.post(
            "/api/challenge/create",
            headers=context.auth[101],
            json={
                "challengeType": " private-type-marker ",
                "title": " private-title-marker ",
                "description": "private-description-marker",
                "targetDays": 3,
                "reward": "private-reward-marker",
            },
        )
        challenge_id = int(created.json()["data"])
        checked = await context.client.post(
            "/api/challenge/checkin",
            headers=context.auth[101],
            json={
                "challengeId": challenge_id,
                "content": "private-content-marker",
                "imageUrl": "https://private.invalid/image-marker",
            },
        )
        async with context.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO t_checkin_record "
                    "(challenge_id,user_id,checkin_date,content) "
                    "VALUES (:challenge_id,102,:checkin_date,:content)"
                ),
                [
                    {
                        "challenge_id": challenge_id,
                        "checkin_date": date.today(),
                        "content": f"partner-record-{index}",
                    }
                    for index in range(21)
                ],
            )
        rejected = await context.client.post(
            f"/api/challenge/accept/{challenge_id}", headers=context.auth[101]
        )
        detail = await context.client.get(
            f"/api/challenge/detail/{challenge_id}", headers=context.auth[101]
        )
        listed = await context.client.get("/api/challenge/list?status=0", headers=context.auth[101])
        pending = await context.client.get("/api/challenge/pending", headers=context.auth[102])
        records = await context.client.get(
            f"/api/challenge/checkin-records/{challenge_id}?pageNum=1&pageSize=1",
            headers=context.auth[101],
        )

    assert created.json() == {"code": 200, "message": "操作成功", "data": challenge_id}
    assert checked.json()["code"] == 200
    assert rejected.json() == {"code": 9999, "message": "您不是该挑战的伙伴", "data": None}
    detail_data = detail.json()["data"]
    list_data = listed.json()["data"]
    pending_data = pending.json()["data"]
    page = records.json()["data"]
    expected_challenge_keys = {
        "id",
        "challengeType",
        "title",
        "description",
        "targetDays",
        "currentDays",
        "status",
        "statusDesc",
        "startDate",
        "endDate",
        "reward",
        "creatorId",
        "partnerId",
        "creatorName",
        "partnerName",
        "createTime",
        "checkinRecords",
        "todayChecked",
        "progressPercent",
    }
    assert set(detail_data) == expected_challenge_keys
    assert set(list_data[0]) == set(pending_data[0]) == expected_challenge_keys
    assert list_data[0]["checkinRecords"] is list_data[0]["todayChecked"] is None
    assert pending_data[0]["checkinRecords"] is pending_data[0]["todayChecked"] is None
    assert detail_data["challengeType"] == "private-type-marker"
    assert detail_data["title"] == "private-title-marker"
    assert detail_data["startDate"] == date.today().isoformat()
    assert detail_data["todayChecked"] is True
    assert len(detail_data["checkinRecords"]) == 20
    assert checked.json()["data"]["id"] not in {
        item["id"] for item in detail_data["checkinRecords"]
    }
    assert set(page) == {"records", "total", "size", "current", "pages"}
    assert (page["total"], page["size"], page["current"], page["pages"]) == (22, 1, 1, 22)

    challenge_logs = [entry for entry in logs if entry.get("module") == "challenge"]
    assert challenge_logs
    allowed = {"requestId", "module", "operation", "result", "durationMs", "errorCode"}
    for entry in challenge_logs:
        assert set(entry) - {"event", "log_level"} == allowed
        assert entry["event"] in {"business_operation_completed", "business_operation_failed"}
    serialized_logs = str(challenge_logs)
    for private_value in private_values:
        assert private_value not in serialized_logs

    whitespace_type = await context.client.post(
        "/api/challenge/create",
        headers=context.auth[101],
        json={"challengeType": "   ", "title": "valid", "targetDays": 1},
    )
    whitespace_title = await context.client.post(
        "/api/challenge/create",
        headers=context.auth[101],
        json={"challengeType": "valid", "title": "   ", "targetDays": 1},
    )
    assert (whitespace_type.json()["code"], whitespace_type.json()["message"]) == (
        400,
        "挑战类型不能为空",
    )
    assert (whitespace_title.json()["code"], whitespace_title.json()["message"]) == (
        400,
        "挑战标题不能为空",
    )
