import os
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.api.heart_moment import service
from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.models import User
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/heartMoment/create"),
        ("GET", "/api/heartMoment/list"),
        ("DELETE", "/api/heartMoment/delete/1"),
        ("GET", "/api/heartMoment/random"),
    ],
)
async def test_heart_moment_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={"momentType": "text"})

    assert response.status_code == 401
    assert response.json()["code"] == 401


async def test_create_rejects_blank_type_without_logging_content() -> None:
    app = create_app(settings())

    async def authenticated_user() -> int:
        return 1

    session = AsyncMock()
    session.scalar.return_value = User(id=1, couple_id=1, is_deleted=0)

    async def no_session():
        yield session

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    private_content = "api-private-heart-moment"
    with capture_logs() as logs:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/heartMoment/create",
                json={"momentType": "  ", "content": private_content},
            )

    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert private_content not in str(logs)
    rejected = next(
        item
        for item in logs
        if item.get("module") == "heart_moment" and item.get("operation") == "create"
    )
    assert rejected["result"] == "rejected"
    assert rejected["errorCode"] == "400"


async def test_list_clamps_non_positive_pagination_before_service_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(settings())
    list_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "list_moments", list_mock)

    async def authenticated_user() -> int:
        return 1

    async def no_session():
        yield object()

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/heartMoment/list?page=0&pageSize=0")

    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "操作成功", "data": []}
    assert list_mock.await_args is not None
    assert list_mock.await_args.args[-2:] == (0, 0)
