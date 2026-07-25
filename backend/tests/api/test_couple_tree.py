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
        ("GET", "/api/coupleTree/info", None),
        ("POST", "/api/coupleTree/water", {"nutrientAmount": 10}),
        ("GET", "/api/coupleTree/nutrientLogs", None),
        ("GET", "/api/coupleTree/skins", None),
        ("POST", "/api/coupleTree/skin/change?skinId=default", None),
    ],
)
async def test_couple_tree_routes_require_authentication(
    method: str, path: str, payload: dict[str, object] | None
) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


async def test_water_rejects_invalid_amount_with_result_envelope() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/coupleTree/water", json={"nutrientAmount": 0})

    assert response.status_code == 401
    assert response.json()["data"] is None
