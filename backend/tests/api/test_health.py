import os

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


async def test_live_does_not_require_dependencies() -> None:
    app = create_app(settings())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "操作成功", "data": {"status": "UP"}}


async def test_health_response_keeps_request_id() -> None:
    app = create_app(settings())
    request_id = "71994549-3f20-4d51-a1eb-7975d6b7a48e"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/live", headers={"X-Request-ID": request_id})

    assert response.headers["x-request-id"] == request_id


async def test_ready_reports_dependency_failure_without_details() -> None:
    app = create_app(settings())

    async def readiness() -> dict[str, bool]:
        return {"database": False, "redis": True}

    app.state.readiness = readiness
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["data"] == {"status": "DOWN"}
    assert "password" not in response.text.lower()


async def test_actuator_health_reuses_readiness_check() -> None:
    app = create_app(settings())
    calls = 0

    async def readiness() -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"database": True, "redis": True}

    app.state.readiness = readiness
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/actuator/health")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "UP"}
    assert calls == 1
