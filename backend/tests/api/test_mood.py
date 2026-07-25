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
    ("method", "path"),
    [
        ("POST", "/api/mood/send"),
        ("GET", "/api/mood/today"),
        ("GET", "/api/mood/history"),
        ("GET", "/api/mood/detail/1"),
        ("POST", "/api/mood/read/1"),
        ("GET", "/api/mood/stats"),
        ("GET", "/api/mood/types"),
        ("GET", "/api/mood/unread/count"),
    ],
)
async def test_mood_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={"moodType": "happy"})

    assert response.status_code == 401
    assert response.json()["code"] == 401
