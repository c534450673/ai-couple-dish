import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import Request
from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.core.errors import BusinessError
from app.db.models import Couple, CoupleUnbindRecord, Notification, User
from app.redis.client import RedisClient
from app.schemas.business import (
    BindCoupleRequest,
    GenerateCodeRequest,
    UnbindRequest,
    WechatLoginRequest,
)
from app.services import couple as couple_service
from app.services import user as user_service

SECRET = "c" * 64


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
async def mysql_couple_gate_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


def _request_context(redis: RedisClient) -> Request:
    settings = Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106
    return cast(
        Request,
        SimpleNamespace(
            state=SimpleNamespace(request_id="couple-cutover-gate-request"),
            app=SimpleNamespace(state=SimpleNamespace(redis=redis, settings=settings)),
        ),
    )


async def _create_users(
    request: Request,
    session: AsyncSession,
    identities: tuple[tuple[str, str], ...],
) -> list[int]:
    users = [
        await user_service.wechat_login(
            request,
            session,
            WechatLoginRequest(code=openid, nick_name=nickname),
        )
        for openid, nickname in identities
    ]
    user_ids: list[int] = []
    for user in users:
        user_info = cast(dict[str, object], user["userInfo"])
        user_id = user_info["id"]
        assert isinstance(user_id, int)
        user_ids.append(user_id)
    return user_ids


async def _bind_pair(
    request: Request,
    session: AsyncSession,
    creator_id: int,
    partner_id: int,
) -> tuple[int, str]:
    code = await couple_service.generate_code(
        request,
        session,
        creator_id,
        GenerateCodeRequest(love_start_date=date.today()),
    )
    relation = await couple_service.bind(
        request,
        session,
        partner_id,
        BindCoupleRequest(couple_code=code),
    )
    relation_id = relation["id"]
    assert isinstance(relation_id, int)
    return relation_id, code


async def _assert_bind_failure_left_no_database_writes(
    session_factory: async_sessionmaker[AsyncSession], user_ids: list[int]
) -> None:
    async with session_factory() as verification_session:
        assert await verification_session.scalar(select(func.count(Couple.id))) == 0
        assert await verification_session.scalar(select(func.count(Notification.id))) == 0
        users = list(await verification_session.scalars(select(User).where(User.id.in_(user_ids))))
        assert len(users) == len(user_ids)
        assert all(user.couple_id is None for user in users)
        assert all(user.love_start_date is None for user in users)


@pytest.mark.integration
async def test_bind_notification_failure_rolls_back_couple_users_and_preserves_code(
    mysql_couple_gate_engine: AsyncEngine,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_couple_gate_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request = _request_context(redis)
            creator_id, partner_id = await _create_users(
                request,
                session,
                (("bind-notification-creator", "通知甲"), ("bind-notification-partner", "通知乙")),
            )
            code = await couple_service.generate_code(
                request,
                session,
                creator_id,
                GenerateCodeRequest(love_start_date=date.today()),
            )
            original_add = AsyncSession.add

            def fail_notification_add(
                target_session: AsyncSession, instance: object, *, _warn: bool = True
            ) -> None:
                if isinstance(instance, Notification):
                    raise RuntimeError("injected notification persistence failure")
                original_add(target_session, instance, _warn=_warn)

            with monkeypatch.context() as patch:
                patch.setattr(AsyncSession, "add", fail_notification_add)
                with pytest.raises(RuntimeError, match="notification persistence failure"):
                    await couple_service.bind(
                        request,
                        session,
                        partner_id,
                        BindCoupleRequest(couple_code=code),
                    )

        await _assert_bind_failure_left_no_database_writes(
            session_factory, [creator_id, partner_id]
        )
        assert await redis.raw.exists(f"couple:code:{code}") == 1
        assert await redis.raw.get(f"couple:code:user:{creator_id}") == code
        assert await redis.raw.exists(f"lock:bind:couple:{code}") == 0

        async with session_factory() as retry_session:
            retried = await couple_service.bind(
                _request_context(redis),
                retry_session,
                partner_id,
                BindCoupleRequest(couple_code=code),
            )
            assert retried["status"] == 1
    finally:
        await redis.close()


@pytest.mark.integration
async def test_bind_commit_failure_rolls_back_couple_notification_users_and_preserves_code(
    mysql_couple_gate_engine: AsyncEngine,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_couple_gate_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request = _request_context(redis)
            creator_id, partner_id = await _create_users(
                request,
                session,
                (("bind-commit-creator", "提交甲"), ("bind-commit-partner", "提交乙")),
            )
            code = await couple_service.generate_code(
                request,
                session,
                creator_id,
                GenerateCodeRequest(love_start_date=date.today()),
            )

            async def fail_commit(_session: AsyncSession) -> None:
                raise RuntimeError("injected commit failure")

            with monkeypatch.context() as patch:
                patch.setattr(AsyncSession, "commit", fail_commit)
                with pytest.raises(RuntimeError, match="injected commit failure"):
                    await couple_service.bind(
                        request,
                        session,
                        partner_id,
                        BindCoupleRequest(couple_code=code),
                    )

        await _assert_bind_failure_left_no_database_writes(
            session_factory, [creator_id, partner_id]
        )
        assert await redis.raw.exists(f"couple:code:{code}") == 1
        assert await redis.raw.get(f"couple:code:user:{creator_id}") == code
        assert await redis.raw.exists(f"lock:bind:couple:{code}") == 0
    finally:
        await redis.close()


@pytest.mark.integration
async def test_recover_rejects_outsider_and_concurrent_partners_restore_once(
    mysql_couple_gate_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_couple_gate_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request = _request_context(redis)
            first_id, second_id, outsider_id = await _create_users(
                request,
                session,
                (
                    ("recover-first", "恢复甲"),
                    ("recover-second", "恢复乙"),
                    ("recover-outsider", "恢复外部用户"),
                ),
            )
            old_couple_id, _ = await _bind_pair(request, session, first_id, second_id)
            await couple_service.apply_unbind(request, session, first_id, UnbindRequest())
            await couple_service.confirm_unbind(request, session, second_id, old_couple_id)
            record = await session.scalar(
                select(CoupleUnbindRecord).where(CoupleUnbindRecord.couple_id == old_couple_id)
            )
            assert record is not None
            record_id = record.id

            with pytest.raises(BusinessError) as outsider_error:
                await couple_service.recover(request, session, outsider_id, record_id)
            assert outsider_error.value.code == 2001
            await session.rollback()
            unchanged_record = await session.get(CoupleUnbindRecord, record_id)
            unchanged_couple = await session.get(Couple, old_couple_id)
            unchanged_users = list(
                await session.scalars(
                    select(User).where(User.id.in_([first_id, second_id, outsider_id]))
                )
            )
            assert unchanged_record is not None
            assert unchanged_record.status == 0
            assert unchanged_couple is not None
            assert unchanged_couple.status == 2
            assert all(user.couple_id is None for user in unchanged_users)

        async def recover_with_new_session(user_id: int) -> str:
            async with session_factory() as isolated_session:
                try:
                    await couple_service.recover(
                        _request_context(redis), isolated_session, user_id, record_id
                    )
                except BusinessError as error:
                    await isolated_session.rollback()
                    return f"error:{error.code}"
                return "success"

        outcomes = await asyncio.gather(
            recover_with_new_session(first_id), recover_with_new_session(second_id)
        )
        assert outcomes.count("success") == 1
        assert sum(outcome in {"error:2001", "error:2002"} for outcome in outcomes) == 1

        async with session_factory() as session:
            record = await session.get(CoupleUnbindRecord, record_id)
            assert record is not None
            assert record.status == 1
            users = {
                user.id: user
                for user in await session.scalars(
                    select(User).where(User.id.in_([first_id, second_id, outsider_id]))
                )
            }
            assert users[first_id].couple_id is not None
            assert users[first_id].couple_id == users[second_id].couple_id
            assert users[outsider_id].couple_id is None
            active_couples = list(await session.scalars(select(Couple).where(Couple.status == 1)))
            assert len(active_couples) == 1
            assert active_couples[0].id == users[first_id].couple_id
            assert {active_couples[0].user1_id, active_couples[0].user2_id} == {
                first_id,
                second_id,
            }
    finally:
        await redis.close()


@pytest.mark.integration
async def test_confirm_and_reject_race_has_one_terminal_transition_and_idempotent_retries(
    mysql_couple_gate_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_couple_gate_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request = _request_context(redis)
            first_id, second_id = await _create_users(
                request,
                session,
                (("unbind-race-first", "竞态甲"), ("unbind-race-second", "竞态乙")),
            )
            couple_id, _ = await _bind_pair(request, session, first_id, second_id)
            await couple_service.apply_unbind(request, session, first_id, UnbindRequest())

        async def transition_with_new_session(operation: str) -> str:
            async with session_factory() as isolated_session:
                try:
                    if operation == "confirm":
                        await couple_service.confirm_unbind(
                            _request_context(redis), isolated_session, second_id, couple_id
                        )
                    else:
                        await couple_service.reject_unbind(
                            _request_context(redis), isolated_session, second_id, couple_id
                        )
                except BusinessError as error:
                    await isolated_session.rollback()
                    return f"error:{error.code}"
                return f"success:{operation}"

        outcomes = await asyncio.gather(
            transition_with_new_session("confirm"), transition_with_new_session("reject")
        )
        assert sum(outcome.startswith("success:") for outcome in outcomes) == 1
        assert outcomes.count("error:2006") == 1

        async with session_factory() as session:
            couple = await session.get(Couple, couple_id)
            assert couple is not None
            users = list(
                await session.scalars(select(User).where(User.id.in_([first_id, second_id])))
            )
            records = list(
                await session.scalars(
                    select(CoupleUnbindRecord).where(CoupleUnbindRecord.couple_id == couple_id)
                )
            )
            titles = list(
                await session.scalars(
                    select(Notification.title).where(Notification.related_id == couple_id)
                )
            )
            if "success:confirm" in outcomes:
                assert couple.status == 2
                assert all(user.couple_id is None for user in users)
                assert len(records) == 1
                assert titles.count("💔 已解绑") == 2
                assert titles.count("💕 解绑被拒绝") == 0
            else:
                assert couple.status == 1
                assert all(user.couple_id == couple_id for user in users)
                assert records == []
                assert titles.count("💔 已解绑") == 0
                assert titles.count("💕 解绑被拒绝") == 1

        retry_outcomes = await asyncio.gather(
            transition_with_new_session("confirm"), transition_with_new_session("reject")
        )
        assert list(retry_outcomes) == ["error:2006", "error:2006"]

        async with session_factory() as session:
            assert await session.scalar(
                select(func.count(CoupleUnbindRecord.id)).where(
                    CoupleUnbindRecord.couple_id == couple_id
                )
            ) == (1 if "success:confirm" in outcomes else 0)
            titles = list(
                await session.scalars(
                    select(Notification.title).where(Notification.related_id == couple_id)
                )
            )
            assert titles.count("💔 已解绑") == (2 if "success:confirm" in outcomes else 0)
            assert titles.count("💕 解绑被拒绝") == (0 if "success:confirm" in outcomes else 1)
    finally:
        await redis.close()
