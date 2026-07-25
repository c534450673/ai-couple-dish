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
        ("GET", "/api/dailyTask/today"),
        ("GET", "/api/dailyTask/detail/1"),
        ("POST", "/api/dailyTask/progress/1?count=1"),
        ("POST", "/api/dailyTask/claim/1"),
        ("GET", "/api/dailyTask/today/stats"),
    ],
)
async def test_daily_task_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


async def test_progress_rejects_non_positive_count_before_database_access() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/dailyTask/progress/1?count=0")

    assert response.status_code == 401
