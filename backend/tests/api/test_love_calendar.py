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
from app.services import love_calendar as calendar_service


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/loveCalendar/month"),
        ("GET", "/api/loveCalendar/events/date?date=2026-07-26"),
        ("GET", "/api/loveCalendar/events/range?startDate=2026-07-26&endDate=2026-07-27"),
        ("GET", "/api/loveCalendar/events/upcoming"),
        ("GET", "/api/loveCalendar/events/today"),
        ("GET", "/api/loveCalendar/year/overview"),
    ],
)
async def test_love_calendar_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)
    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "请先登录", "data": None}


async def test_range_rejects_reversed_business_dates() -> None:
    app = create_app(settings())

    async def authenticated_user() -> int:
        return 1

    async def no_session() -> AsyncIterator[object]:
        yield object()

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/loveCalendar/events/range?startDate=2026-07-27&endDate=2026-07-26"
        )
    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert response.json()["data"] is None


async def test_upcoming_zero_limit_is_empty_without_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(settings())
    service_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(calendar_service, "upcoming", service_mock)

    async def authenticated_user() -> int:
        return 1

    async def no_session() -> AsyncIterator[object]:
        yield object()

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/loveCalendar/events/upcoming?limit=0")
    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "操作成功", "data": []}
    assert service_mock.await_args is not None
    assert service_mock.await_args.args[-1] == 0
