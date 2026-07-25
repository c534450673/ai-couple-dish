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
        ("GET", "/api/invite/code"),
        ("POST", "/api/invite/use?inviteCode=ABC123"),
        ("GET", "/api/invite/referrals"),
        ("GET", "/api/invite/stats"),
        ("GET", "/api/invite/rank"),
        ("GET", "/api/invite/validate?inviteCode=ABC123"),
        ("GET", "/api/invite/info/ABC123"),
    ],
)
async def test_all_invite_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)
    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


def test_invite_routes_are_registered_with_spring_paths() -> None:
    app = create_app(settings())
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST"}
    }
    assert {
        ("GET", "/api/invite/code"),
        ("POST", "/api/invite/use"),
        ("GET", "/api/invite/referrals"),
        ("GET", "/api/invite/stats"),
        ("GET", "/api/invite/rank"),
        ("GET", "/api/invite/validate"),
        ("GET", "/api/invite/info/{inviteCode}"),
    } <= actual
