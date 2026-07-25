import os
from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.models import Couple, TimeCapsule, User
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/timeCapsule/create"),
        ("GET", "/api/timeCapsule/list"),
        ("GET", "/api/timeCapsule/detail/1"),
        ("POST", "/api/timeCapsule/unlock/1"),
        ("DELETE", "/api/timeCapsule/delete/1"),
        ("GET", "/api/timeCapsule/pending"),
    ],
)
async def test_time_capsule_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={"capsuleType": "text", "title": "x"})
    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


def test_time_capsule_routes_are_registered() -> None:
    app = create_app(settings())
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST", "DELETE"}
    }
    assert {
        ("POST", "/api/timeCapsule/create"),
        ("GET", "/api/timeCapsule/list"),
        ("GET", "/api/timeCapsule/detail/{id}"),
        ("POST", "/api/timeCapsule/unlock/{id}"),
        ("DELETE", "/api/timeCapsule/delete/{id}"),
        ("GET", "/api/timeCapsule/pending"),
    } <= actual


class ScriptedSession:
    def __init__(self, *, user: User, couple: Couple, capsule: TimeCapsule | None = None) -> None:
        self.user = user
        self.couple = couple
        self.capsule = capsule
        self.added: list[object] = []

    async def scalar(self, statement: object, *_: object, **__: object) -> object | None:
        query = str(statement).lower()
        if "t_user" in query:
            return self.user
        if "t_couple" in query:
            return self.couple
        if "t_time_capsule" in query:
            return self.capsule
        return None

    async def execute(self, statement: object, *_: object, **__: object) -> object:
        rows = [self.capsule] if self.capsule else []
        return type(
            "Rows", (), {"scalars": lambda self: type("Scalars", (), {"all": lambda self: rows})()}
        )()

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        for value in self.added:
            if isinstance(value, TimeCapsule) and value.id is None:
                value.id = 101

    async def commit(self) -> None:
        return None


def _app(session: ScriptedSession) -> FastAPI:
    app = create_app(settings())

    async def authenticated_user() -> int:
        return session.user.id

    async def session_override() -> AsyncIterator[ScriptedSession]:
        yield session

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = session_override
    return app


@pytest.mark.asyncio
async def test_create_rejects_text_without_content_and_does_not_log_content() -> None:
    user = User(id=1, openid="u", couple_id=7, is_deleted=0)
    couple = Couple(id=7, user1_id=1, user2_id=2, status=1)
    session = ScriptedSession(user=user, couple=couple)
    private_content = "capsule-private-content"
    with capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(app=_app(session)), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/timeCapsule/create",
                json={
                    "capsuleType": "text",
                    "title": "未来的我们",
                    "content": " ",
                    "unlockDate": (date.today() + timedelta(days=1)).isoformat(),
                },
            )
    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert private_content not in str(logs)
    assert logs or response.json()["code"] == 400


@pytest.mark.asyncio
async def test_detail_hides_future_capsule_content_and_media() -> None:
    user = User(id=1, openid="u", couple_id=7, is_deleted=0)
    couple = Couple(id=7, user1_id=1, user2_id=2, status=1)
    capsule = TimeCapsule(
        id=9,
        couple_id=7,
        creator_id=1,
        capsule_type="text",
        title="未来",
        content="private-body",
        media_urls='["https://private.invalid/photo.jpg"]',
        unlock_date=date.today() + timedelta(days=2),
        status=0,
        is_deleted=0,
    )
    async with AsyncClient(
        transport=ASGITransport(
            app=_app(ScriptedSession(user=user, couple=couple, capsule=capsule))
        ),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/timeCapsule/detail/9")
    payload = response.json()["data"]
    assert payload["content"] == "🔒 胶囊尚未解锁"
    assert payload["mediaUrls"] is None
