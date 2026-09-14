from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest

from packages.platform.auth import issue_user_token
from services.dining.app import main as dining
from services.identity_couple.app import main as identity

SECRET = "identity-runtime-test-" + "x" * 64


class Result:
    def scalar_one_or_none(self):
        return SimpleNamespace(
            id=7,
            couple_id=None,
            love_start_date=None,
            openid="openid",
            nick_name="tester",
            avatar_url="",
            phone=None,
            gender=None,
            member_level=0,
            status=0,
        )


class Session:
    async def execute(self, query):
        return Result()


@asynccontextmanager
async def provide_session():
    yield Session()


class RedisRaw:
    def __init__(self):
        self.keys = set()
        self.fail = False

    async def exists(self, key):
        if self.fail:
            raise ConnectionError("redis offline")
        return key in self.keys

    async def set(self, key, value, *, px):
        self.keys.add(key)


@pytest.mark.asyncio
async def test_logout_revokes_token_for_profile() -> None:
    app = identity.create_app(jwt_secret=SECRET, session_provider=provide_session)
    app.state.redis = SimpleNamespace(raw=RedisRaw())
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://identity"
    ) as client:
        assert (await client.get("/api/user/profile", headers=headers)).status_code == 200
        assert (await client.post("/api/user/logout", headers=headers)).status_code == 200
        rejected = await client.get("/api/user/profile", headers=headers)

    assert rejected.status_code == 401
    assert rejected.json()["message"] == "登录已过期，请重新登录"
    assert len(app.state.redis.raw.keys) == 1


@pytest.mark.asyncio
async def test_redis_error_does_not_accept_authenticated_request() -> None:
    app = identity.create_app(jwt_secret=SECRET, session_provider=provide_session)
    app.state.redis = SimpleNamespace(raw=RedisRaw())
    app.state.redis.raw.fail = True
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://identity"
    ) as client:
        response = await client.get(
            "/api/user/profile", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_runtime_connects_and_closes_dependencies(monkeypatch) -> None:
    events = []

    class Database:
        def __init__(self, url, *, pool_size, max_overflow):
            self.session = provide_session

        async def connect(self):
            events.append("database_connected")

        async def close(self):
            events.append("database_closed")

    class Redis:
        def __init__(self, url):
            self.raw = RedisRaw()

        async def connect(self):
            events.append("redis_connected")

        async def close(self):
            events.append("redis_closed")

    monkeypatch.setattr(identity, "Database", Database)
    monkeypatch.setattr(identity, "RedisClient", Redis)
    settings = SimpleNamespace(
        database_url="mysql+asyncmy://test",
        database_pool_size=1,
        database_max_overflow=0,
        redis_url="redis://test",
        app_env="test",
    )
    app = identity.create_app(jwt_secret=SECRET, settings=settings)

    async with app.router.lifespan_context(app):
        assert app.state.session_provider is not None
        assert app.state.redis is not None

    assert events == ["database_connected", "redis_connected", "redis_closed", "database_closed"]


@pytest.mark.asyncio
async def test_send_code_requires_an_available_delivery_path(monkeypatch) -> None:
    app = identity.create_app(jwt_secret=SECRET, session_provider=provide_session)
    app.state.settings = SimpleNamespace(app_env="prod", expose_dev_verification_code=False)
    app.state.redis = SimpleNamespace(raw=RedisRaw())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://identity"
    ) as client:
        blocked = await client.post("/api/user/sendCode", params={"phone": "13800000000"})
        app.state.settings = SimpleNamespace(app_env="test", expose_dev_verification_code=True)

        async def send_code(request, phone):
            assert phone == "13800000000"
            return "123456"

        monkeypatch.setattr(identity.user_service, "send_verify_code", send_code)
        allowed = await client.post("/api/user/sendCode", params={"phone": "13800000000"})

    assert blocked.status_code == 503
    assert allowed.json()["data"] == {"devCode": "123456"}


@pytest.mark.asyncio
async def test_logout_revocation_applies_to_dining_service() -> None:
    redis = SimpleNamespace(raw=RedisRaw())
    identity_app = identity.create_app(jwt_secret=SECRET, session_provider=provide_session)
    dining_app = dining.create_app(jwt_secret=SECRET, session_provider=provide_session)
    identity_app.state.redis = dining_app.state.redis = redis
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=identity_app), base_url="http://identity"
    ) as client:
        assert (await client.post("/api/user/logout", headers=headers)).status_code == 200

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=dining_app), base_url="http://dining"
    ) as client:
        rejected = await client.get("/api/dining/cuisines", headers=headers)

    assert rejected.status_code == 401
    assert rejected.json()["message"] == "登录已过期，请重新登录"


@pytest.mark.asyncio
async def test_dining_runtime_connects_and_closes_dependencies(monkeypatch) -> None:
    events = []

    class Database:
        def __init__(self, url, *, pool_size, max_overflow):
            self.session = provide_session

        async def connect(self):
            events.append("database_connected")

        async def close(self):
            events.append("database_closed")

    class Redis:
        def __init__(self, url):
            self.raw = RedisRaw()

        async def connect(self):
            events.append("redis_connected")

        async def close(self):
            events.append("redis_closed")

    monkeypatch.setattr(dining, "Database", Database)
    monkeypatch.setattr(dining, "RedisClient", Redis)
    settings = SimpleNamespace(
        database_url="mysql+asyncmy://test",
        database_pool_size=1,
        database_max_overflow=0,
        redis_url="redis://test",
    )
    app = dining.create_app(jwt_secret=SECRET, settings=settings)

    async with app.router.lifespan_context(app):
        assert app.state.session_provider is not None
        assert app.state.redis is not None

    assert events == ["database_connected", "redis_connected", "redis_closed", "database_closed"]
