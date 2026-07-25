import os
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.models import Couple, User
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/sweetBomb/generate"),
        ("GET", "/api/sweetBomb/unread"),
        ("GET", "/api/sweetBomb/detail/1"),
        ("POST", "/api/sweetBomb/read/1"),
        ("POST", "/api/sweetBomb/answer/1?answerContent=private-answer"),
        ("GET", "/api/sweetBomb/history"),
        ("GET", "/api/sweetBomb/unread/count"),
    ],
)
async def test_sweet_bomb_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


async def test_generate_rejects_inactive_membership_without_sensitive_logs() -> None:
    app = create_app(settings())

    async def authenticated_user() -> int:
        return 1

    session = AsyncMock()
    session.scalar.side_effect = [
        User(id=1, openid="private-openid", nick_name="private-name", couple_id=7, is_deleted=0),
        Couple(id=7, user1_id=1, user2_id=2, status=3),
    ]

    async def session_override():
        yield session

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = session_override
    with capture_logs() as logs:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/sweetBomb/generate")

    assert response.status_code == 200
    assert response.json()["code"] == 2006
    assert "private-openid" not in str(logs)
    assert "private-name" not in str(logs)
    rejected = next(item for item in logs if item["event"] == "business_operation_failed")
    assert rejected["module"] == "sweet_bomb"
    assert rejected["operation"] == "generate"
    assert rejected["errorCode"] == "2006"
    assert "requestId" in rejected and "durationMs" in rejected
