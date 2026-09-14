from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from packages.platform.auth import issue_user_token
from services.identity_couple.app.main import create_app


def test_identity_couple_contract_routes_are_registered() -> None:
    app = create_app(jwt_secret="identity-test-secret-" + "x" * 64)
    paths = {route.path for route in app.routes}

    assert {
        "/health",
        "/api/user/login",
        "/api/user/profile",
        "/api/couple/generateCode",
        "/api/couple/bind",
    } <= paths


def test_identity_couple_does_not_expose_a_process_memory_store() -> None:
    source = (Path(__file__).parents[2] / "services/identity_couple/app/main.py").read_text(
        encoding="utf-8"
    )
    assert "users = {}" not in source
    assert "codes = {}" not in source
    assert "couples = {}" not in source


@pytest.mark.asyncio
async def test_login_uses_verified_openid_not_client_code() -> None:
    class Result:
        def scalar_one_or_none(self):
            return None

    class Session:
        user = None

        async def execute(self, query):
            return Result()

        def add(self, user):
            self.user = user

        async def flush(self):
            self.user.id = 42

        async def commit(self):
            pass

    session = Session()

    @asynccontextmanager
    async def provide_session():
        yield session

    async def resolve_code(code: str) -> str:
        assert code == "short-lived-code"
        return "trusted-wechat-openid"

    app = create_app(
        jwt_secret="identity-test-secret-" + "x" * 64,
        session_provider=provide_session,
        wechat_code_resolver=resolve_code,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://identity"
    ) as client:
        response = await client.post("/api/user/login", json={"code": "short-lived-code"})

    assert response.status_code == 200
    assert session.user.openid == "trusted-wechat-openid"
    assert response.json()["data"]["userInfo"]["openid"] == "trusted-wechat-openid"


@pytest.mark.asyncio
async def test_wechat_login_fails_closed_without_runtime_credentials(monkeypatch) -> None:
    from services.identity_couple.app.main import _resolve_wechat_code

    monkeypatch.delenv("WECHAT_APP_ID", raising=False)
    monkeypatch.delenv("WECHAT_APP_SECRET", raising=False)
    with pytest.raises(HTTPException) as raised:
        await _resolve_wechat_code("untrusted-openid")
    assert raised.value.status_code == 503


@pytest.mark.asyncio
async def test_bind_locks_code_and_participants_before_commit() -> None:
    class Result:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class Session:
        def __init__(self):
            self.user = SimpleNamespace(id=8, couple_id=None, love_start_date=None)
            self.couple = SimpleNamespace(
                id=12, user1_id=7, user2_id=None, start_date=date.today(),
                love_days=0, couple_nickname=None, status=0,
            )
            self.owner = SimpleNamespace(id=7, couple_id=None, love_start_date=None)
            # 先读候选情侣码，再按用户 ID 升序锁定参与者，最后锁定情侣码。
            self.values = [self.couple, self.owner, self.user, self.couple]
            self.queries = []
            self.lock_user_ids = []
            self.committed = False

        async def execute(self, query):
            self.queries.append(query)
            if query._for_update_arg is not None and "t_user.id" in str(query):
                self.lock_user_ids.append(query.compile().params["id_1"])
            return Result(self.values.pop(0))

        async def commit(self):
            self.committed = True

    session = Session()

    @asynccontextmanager
    async def provide_session():
        yield session

    secret = "identity-test-secret-" + "x" * 64
    token = issue_user_token(user_id=8, secret=secret, expires_ms=60_000)
    app = create_app(jwt_secret=secret, session_provider=provide_session)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://identity"
    ) as client:
        response = await client.post(
            "/api/couple/bind",
            json={"coupleCode": "ABCD"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert session.committed
    assert session.queries[0]._for_update_arg is None
    assert all(query._for_update_arg is not None for query in session.queries[1:])
    assert session.lock_user_ids == [7, 8]
    assert "user.id =" in str(session.queries[1])
    assert "user.id =" in str(session.queries[2])
    assert "couple.id =" in str(session.queries[3])
    assert session.user.couple_id == session.owner.couple_id == session.couple.id
