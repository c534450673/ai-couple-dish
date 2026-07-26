import asyncio
import os
import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import decode_access_token
from app.core.config import Settings
from app.db.models import User
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient
from app.redis.keys import logout_blacklist_key, verify_code_key
from app.services import user as user_service

SECRET = "u" * 64
PHONE = "13900139000"
VERIFY_CODE = "648205"


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
async def user_gate_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
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


def _test_app(session_factory: async_sessionmaker[AsyncSession], redis: RedisClient) -> FastAPI:
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    return app


@pytest.mark.integration
async def test_http_logout_blacklists_old_jwt_before_next_protected_request(
    user_gate_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(user_gate_engine, expire_on_commit=False)
    app = _test_app(session_factory, redis)
    blacklist_key: str | None = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/user/login",
                json={"code": "logout-cutover-user", "nickName": "退出门禁用户"},
            )
            assert login.status_code == 200, login.text
            assert login.json()["code"] == 200, login.text
            token = login.json()["data"]["token"]
            user_id = int(login.json()["data"]["userInfo"]["id"])
            authorization = {"Authorization": f"Bearer {token}"}

            before_logout = await client.get("/api/user/info", headers=authorization)
            assert before_logout.status_code == 200, before_logout.text
            assert before_logout.json()["data"]["id"] == user_id

            claims = decode_access_token(token, SECRET)
            blacklist_key = logout_blacklist_key(claims.jti)
            with capture_logs() as logs:
                logout = await client.post("/api/user/logout", headers=authorization)
                after_logout = await client.get("/api/user/info", headers=authorization)

            assert logout.status_code == 200, logout.text
            assert logout.json() == {"code": 200, "message": "操作成功", "data": None}
            assert await redis.raw.get(blacklist_key) == str(user_id)
            assert await redis.raw.pttl(blacklist_key) > 0
            assert after_logout.status_code == 401, after_logout.text
            assert after_logout.json() == {
                "code": 401,
                "message": "登录已过期，请重新登录",
                "data": None,
            }
            assert any(
                entry.get("event") == "authorization_rejected"
                and entry.get("reason") == "blacklisted"
                and entry.get("route") == "/api/user/info"
                for entry in logs
            ), logs
    finally:
        if blacklist_key is not None:
            await redis.raw.delete(blacklist_key)
        await redis.close()


@pytest.mark.integration
async def test_same_verification_code_concurrent_http_registration_creates_one_user(
    user_gate_engine: AsyncEngine,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(user_gate_engine, expire_on_commit=False)
    app = _test_app(session_factory, redis)
    code_key = verify_code_key(PHONE)
    expire_key = f"user:verify:expire:{PHONE}"
    lock_key = f"lock:user:phone:{PHONE}"
    commit_entered = asyncio.Event()
    allow_commit = asyncio.Event()
    original_commit = user_service._commit_new_user

    async def controlled_commit(session: AsyncSession, user: User) -> User:
        commit_entered.set()
        await allow_commit.wait()
        return await original_commit(session, user)

    monkeypatch.setattr(user_service, "_commit_new_user", controlled_commit)
    await redis.raw.delete(code_key, expire_key, lock_key)
    await redis.raw.set(code_key, VERIFY_CODE, ex=60)
    await redis.raw.set(expire_key, "1", ex=60)
    first_task: asyncio.Task[Response] | None = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {"phone": PHONE, "verifyCode": VERIFY_CODE}
            first_task = asyncio.create_task(client.post("/api/user/register", json=payload))
            await asyncio.wait_for(commit_entered.wait(), timeout=5)
            try:
                concurrent_response = await client.post("/api/user/register", json=payload)
            finally:
                allow_commit.set()
            successful_response = await asyncio.wait_for(first_task, timeout=5)

        assert successful_response.status_code == concurrent_response.status_code == 200
        assert successful_response.json()["code"] == 200, successful_response.text
        assert concurrent_response.json() == {
            "code": 9005,
            "message": "操作过于频繁，请稍后重试",
            "data": None,
        }

        async with session_factory() as session:
            user_count = await session.scalar(
                select(func.count()).select_from(User).where(User.phone == PHONE)
            )
            users = list(await session.scalars(select(User).where(User.phone == PHONE)))
        assert user_count == 1
        assert len(users) == 1
        assert users[0].openid == f"phone_{PHONE}"
        assert successful_response.json()["data"]["userInfo"]["id"] == users[0].id
        assert await redis.raw.get(code_key) is None
        assert await redis.raw.get(expire_key) is None
        assert await redis.raw.get(lock_key) is None
    finally:
        allow_commit.set()
        if first_task is not None and not first_task.done():
            await first_task
        await redis.raw.delete(code_key, expire_key, lock_key)
        await redis.close()
