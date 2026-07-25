import os

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


async def test_options_is_handled_before_authentication() -> None:
    app = create_app(settings())
    request_id = "71994549-3f20-4d51-a1eb-7975d6b7a48e"
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "X-Request-ID": request_id,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/api/health/live", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-request-id"] == request_id


async def test_internal_error_keeps_request_id() -> None:
    app = create_app(settings())

    @app.get("/api/fail")
    async def fail() -> None:
        raise RuntimeError("failure")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get("/api/fail", headers={"X-Request-ID": "invalid"})

    assert response.status_code == 500
    assert response.headers["x-request-id"]
