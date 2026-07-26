import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET="x" * 64,
        FILE_BASE_URL="/api/uploads",
        FILE_PUBLIC_PATH="/api/uploads",
    )  # noqa: S106


EXPECTED_POSTER_ROUTES = {
    ("GET", "/api/poster/templates"),
    ("POST", "/api/poster/generate"),
    ("GET", "/api/poster/list"),
    ("GET", "/api/poster/detail/{id}"),
    ("DELETE", "/api/poster/delete/{id}"),
    ("GET", "/api/poster/share/{id}"),
}


def test_poster_exposes_six_spring_compatible_routes() -> None:
    schema = create_app(_settings()).openapi()
    actual = {
        (method.upper(), path)
        for path, item in schema["paths"].items()
        for method in item
        if method != "parameters" and path.startswith("/api/poster/")
    }

    assert actual == EXPECTED_POSTER_ROUTES


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/poster/templates"),
        ("POST", "/api/poster/generate"),
        ("GET", "/api/poster/list"),
        ("GET", "/api/poster/detail/1"),
        ("DELETE", "/api/poster/delete/1"),
        ("GET", "/api/poster/share/1"),
    ],
)
async def test_every_poster_route_requires_authentication(method: str, path: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(_settings())), base_url="http://test"
    ) as client:
        response = await client.request(method, path, json={} if method == "POST" else None)

    assert response.status_code == 401


async def test_poster_routes_keep_result_wrapper_and_query_aliases(monkeypatch) -> None:
    from app.services import poster as poster_service

    app = create_app(_settings())

    async def authenticated_user() -> int:
        return 42

    async def no_session() -> AsyncIterator[object]:
        yield object()

    async def templates(*_args, **_kwargs):
        return [{"id": 1, "templateType": "annual"}]

    async def posters(*_args, **_kwargs):
        return [{"id": 2, "posterType": "map"}]

    monkeypatch.setattr(poster_service, "get_templates", templates)
    monkeypatch.setattr(poster_service, "list_posters", posters)
    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        template_response = await client.get(
            "/api/poster/templates", params={"posterType": "annual"}
        )
        list_response = await client.get(
            "/api/poster/list", params={"posterType": "map", "limit": 10}
        )

    assert template_response.json() == {
        "code": 200,
        "message": "操作成功",
        "data": [{"id": 1, "templateType": "annual"}],
    }
    assert list_response.json() == {
        "code": 200,
        "message": "操作成功",
        "data": [{"id": 2, "posterType": "map"}],
    }
