import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.services import relationship_weather as service


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    "path",
    [
        "/api/relationshipWeather/current",
        "/api/relationshipWeather/interactions",
        "/api/relationshipWeather/suggestions",
        "/api/relationshipWeather/forecast",
    ],
)
async def test_relationship_weather_routes_require_authentication(path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "请先登录", "data": None}


async def test_interactions_accepts_zero_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings())
    mocked = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "interactions", mocked)

    async def authenticated_user() -> int:
        return 1

    async def no_session() -> AsyncIterator[object]:
        yield object()

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/relationshipWeather/interactions?limit=0")
    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "操作成功", "data": []}
    assert mocked.await_args is not None
    assert mocked.await_args.args[-1] == 0


async def test_interactions_rejects_negative_limit() -> None:
    app = create_app(settings())

    async def authenticated_user() -> int:
        return 1

    async def no_session() -> AsyncIterator[object]:
        yield object()

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/relationshipWeather/interactions?limit=-1")
    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
