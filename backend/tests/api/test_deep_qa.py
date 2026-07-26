import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


def test_deep_qa_routes_and_openapi_constraints_are_registered() -> None:
    schema = create_app(_settings()).openapi()
    assert {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST"}
    } >= {
        ("GET", "/api/deepQa/current"),
        ("GET", "/api/deepQa/week/{weekNumber}"),
        ("POST", "/api/deepQa/submit"),
        ("POST", "/api/deepQa/reveal/{questionId}"),
        ("GET", "/api/deepQa/progress"),
        ("GET", "/api/deepQa/history"),
        ("POST", "/api/deepQa/skip"),
    }
    submit = schema["components"]["schemas"]["DeepQaSubmitRequest"]
    assert set(submit["required"]) == {"questionId", "answerText"}
    assert submit["properties"]["questionId"]["minimum"] == 1
    assert submit["properties"]["answerText"]["maxLength"] == 5000


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("GET", "/api/deepQa/current", None),
        ("GET", "/api/deepQa/week/1", None),
        ("POST", "/api/deepQa/submit", {"questionId": 1, "answerText": "answer"}),
        ("POST", "/api/deepQa/reveal/1", None),
        ("GET", "/api/deepQa/progress", None),
        ("GET", "/api/deepQa/history", None),
        ("POST", "/api/deepQa/skip", None),
    ],
)
async def test_deep_qa_routes_require_authentication(
    method: str, path: str, json: dict[str, object] | None
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(_settings())), base_url="http://test"
    ) as client:
        response = await client.request(method, path, json=json)
    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "请先登录", "data": None}


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("GET", "/api/deepQa/week/0", None),
        ("POST", "/api/deepQa/reveal/0", None),
        ("GET", "/api/deepQa/history?limit=0", None),
        ("GET", "/api/deepQa/history?limit=101", None),
        ("POST", "/api/deepQa/submit", {"questionId": 0, "answerText": "answer"}),
        ("POST", "/api/deepQa/submit", {"questionId": 1, "answerText": ""}),
        ("POST", "/api/deepQa/submit", {"questionId": 1, "answerText": "   "}),
        ("POST", "/api/deepQa/submit", {"questionId": 1, "answerText": "字" * 5001}),
    ],
)
async def test_deep_qa_request_validation_uses_http_400_result_envelope(
    method: str, path: str, json: dict[str, object] | None
) -> None:
    app = create_app(_settings())

    async def authenticated_user() -> int:
        return 1

    async def no_session():
        yield None

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=json)
    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
