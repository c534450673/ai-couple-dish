import pytest
from httpx import ASGITransport, AsyncClient

from packages.platform.service import create_service_app

SERVICE_NAMES = ("catalog", "dining", "admin", "analytics", "media", "worker")


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name", SERVICE_NAMES)
async def test_service_health_routes_use_result_envelope(service_name: str) -> None:
    app = create_service_app(service_name)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/health", "/health/live", "/health/ready", "/actuator/health"):
            response = await client.get(path)
            assert response.status_code == 200
            payload = response.json()
            assert set(payload) == {"code", "message", "data"}
            assert payload["code"] == 200
            assert payload["data"] == {"status": "UP", "service": service_name}


@pytest.mark.asyncio
async def test_service_readiness_returns_safe_down_envelope() -> None:
    async def unavailable() -> bool:
        raise RuntimeError("database password must not be returned")

    app = create_service_app("catalog", readiness=unavailable)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "code": 503,
        "message": "服务暂不可用",
        "data": {"status": "DOWN", "service": "catalog"},
    }
    assert "password" not in response.text.lower()
