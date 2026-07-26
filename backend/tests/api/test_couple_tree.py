import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.services import couple_tree as couple_tree_service


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


def authenticated_app() -> tuple[FastAPI, object]:
    app = create_app(settings())
    session_sentinel = object()

    async def authenticated_user() -> int:
        return 1

    async def no_database_session() -> AsyncIterator[object]:
        yield session_sentinel

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_database_session
    return app, session_sentinel


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


@pytest.mark.parametrize("amount", [0, 1001])
async def test_water_rejects_invalid_amount_with_result_envelope(
    monkeypatch: pytest.MonkeyPatch, amount: int
) -> None:
    app, _ = authenticated_app()
    service_mock = AsyncMock()
    monkeypatch.setattr(couple_tree_service, "water", service_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/coupleTree/water", json={"nutrientAmount": amount})

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
    service_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ("path", "service_name"),
    [
        ("/api/coupleTree/nutrientLogs?limit=0", "nutrient_logs"),
        ("/api/coupleTree/nutrientLogs?limit=101", "nutrient_logs"),
        ("/api/coupleTree/skin/change?skinId=", "change_skin"),
        (f"/api/coupleTree/skin/change?skinId={'s' * 65}", "change_skin"),
    ],
)
async def test_couple_tree_boundary_validation(
    monkeypatch: pytest.MonkeyPatch, path: str, service_name: str
) -> None:
    app, _ = authenticated_app()
    service_mock = AsyncMock()
    monkeypatch.setattr(couple_tree_service, service_name, service_mock)
    method = "GET" if service_name == "nutrient_logs" else "POST"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
    service_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "path", "payload", "service_name", "expected_value"),
    [
        ("POST", "/api/coupleTree/water", {"nutrientAmount": 1}, "water", 1),
        ("POST", "/api/coupleTree/water", {"nutrientAmount": 1000}, "water", 1000),
        ("GET", "/api/coupleTree/nutrientLogs?limit=1", None, "nutrient_logs", 1),
        ("GET", "/api/coupleTree/nutrientLogs?limit=100", None, "nutrient_logs", 100),
        ("POST", "/api/coupleTree/skin/change?skinId=s", None, "change_skin", "s"),
        (
            "POST",
            f"/api/coupleTree/skin/change?skinId={'s' * 64}",
            None,
            "change_skin",
            "s" * 64,
        ),
    ],
)
async def test_couple_tree_valid_boundaries_reach_service(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, int] | None,
    service_name: str,
    expected_value: int | str,
) -> None:
    app, session_sentinel = authenticated_app()
    service_mock = AsyncMock(return_value=[] if service_name == "nutrient_logs" else None)
    monkeypatch.setattr(couple_tree_service, service_name, service_mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=payload)

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert service_mock.await_count == 1
    call_args = service_mock.await_args.args
    assert call_args[1] is session_sentinel
    assert call_args[2] == 1
    if service_name == "water":
        assert call_args[3].nutrient_amount == expected_value
    else:
        assert call_args[3] == expected_value
