import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/api/dailyGreeting/send", {"greetingType": 1}),
        ("GET", "/api/dailyGreeting/today/status?greetingType=1", None),
        ("GET", "/api/dailyGreeting/both/status?greetingType=1", None),
        ("GET", "/api/dailyGreeting/streak?streakType=1", None),
        ("GET", "/api/dailyGreeting/history", None),
        ("GET", "/api/dailyGreeting/detail/1", None),
    ],
)
async def test_daily_greeting_routes_require_authentication(
    method: str, path: str, payload: dict[str, object] | None
) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


async def test_send_validates_greeting_type_after_authentication() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/dailyGreeting/send", json={"greetingType": 3})

    assert response.status_code == 401
