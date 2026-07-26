import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.schemas.business import ChallengeCheckinRequest, ChallengeCreateRequest
from app.services import challenge as challenge_service


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


ROUTES = {
    ("POST", "/api/challenge/create"),
    ("POST", "/api/challenge/accept/{challengeId}"),
    ("POST", "/api/challenge/reject/{challengeId}"),
    ("POST", "/api/challenge/cancel/{challengeId}"),
    ("POST", "/api/challenge/checkin"),
    ("GET", "/api/challenge/detail/{challengeId}"),
    ("GET", "/api/challenge/list"),
    ("GET", "/api/challenge/checkin-records/{challengeId}"),
    ("GET", "/api/challenge/pending"),
}


def test_challenge_openapi_registers_exact_nine_routes() -> None:
    app = create_app(_settings())
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/challenge")
        for method in operations
        if method.upper() in {"GET", "POST"}
    }
    assert actual == ROUTES


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/challenge/create"),
        ("POST", "/api/challenge/accept/1"),
        ("POST", "/api/challenge/reject/1"),
        ("POST", "/api/challenge/cancel/1"),
        ("POST", "/api/challenge/checkin"),
        ("GET", "/api/challenge/detail/1"),
        ("GET", "/api/challenge/list"),
        ("GET", "/api/challenge/checkin-records/1"),
        ("GET", "/api/challenge/pending"),
    ],
)
async def test_challenge_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(_settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "请先登录", "data": None}


def test_challenge_request_aliases_and_boundaries() -> None:
    payload = ChallengeCreateRequest.model_validate(
        {"challengeType": " sport ", "title": " title ", "targetDays": 3650}
    )
    assert payload.challenge_type == " sport "
    assert payload.target_days == 3650
    assert payload.start_date is None
    checkin = ChallengeCheckinRequest.model_validate(
        {"challengeId": 1, "content": "", "imageUrl": "https://private.invalid/image"}
    )
    assert checkin.challenge_id == 1
    assert checkin.content == ""


@pytest.mark.parametrize("target_days", [0, -1, 3651])
def test_challenge_target_days_rejects_out_of_range(target_days: int) -> None:
    with pytest.raises(ValueError):
        ChallengeCreateRequest.model_validate(
            {"challengeType": "sport", "title": "title", "targetDays": target_days}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("challengeType", "x" * 65),
        ("title", "x" * 65),
        ("description", "x" * 257),
        ("reward", "x" * 129),
    ],
)
def test_challenge_create_rejects_overlong_fields(field: str, value: str) -> None:
    body = {"challengeType": "sport", "title": "title", "targetDays": 1, field: value}
    with pytest.raises(ValueError):
        ChallengeCreateRequest.model_validate(body)


@pytest.mark.parametrize(
    ("field", "value"),
    [("content", "x" * 513), ("imageUrl", "x" * 513)],
)
def test_challenge_checkin_rejects_overlong_fields(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        ChallengeCheckinRequest.model_validate({"challengeId": 1, field: value})


class _NoopSession:
    pass


def _validation_app():
    app = create_app(_settings())

    async def authenticated() -> int:
        return 1

    async def session_override() -> AsyncIterator[_NoopSession]:
        yield _NoopSession()

    app.dependency_overrides[current_user_id] = authenticated
    app.dependency_overrides[get_session] = session_override
    return app


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("POST", "/api/challenge/accept/0", None),
        ("POST", "/api/challenge/reject/0", None),
        ("POST", "/api/challenge/cancel/0", None),
        ("GET", "/api/challenge/list?status=4", None),
        ("GET", "/api/challenge/list?status=-1", None),
        ("GET", "/api/challenge/checkin-records/1?pageNum=0", None),
        ("GET", "/api/challenge/checkin-records/1?pageSize=0", None),
        ("GET", "/api/challenge/checkin-records/1?pageSize=101", None),
        ("GET", "/api/challenge/checkin-records/0", None),
        ("GET", "/api/challenge/detail/0", None),
        ("POST", "/api/challenge/checkin", {"challengeId": 0}),
    ],
)
async def test_challenge_route_validation_is_http_400(
    method: str, path: str, json: dict[str, int] | None
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_validation_app()), base_url="http://test"
    ) as client:
        response = await client.request(method, path, json=json)
    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None


async def test_challenge_routes_return_exact_success_envelopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _validation_app()
    record = {
        "id": 1,
        "challengeId": 9,
        "userId": 1,
        "userName": None,
        "userAvatar": None,
        "checkinDate": "2026-07-26",
        "content": None,
        "imageUrl": None,
        "createTime": "2026-07-26T08:00:00",
    }
    challenge = {"id": 9, "checkinRecords": None, "todayChecked": None}
    monkeypatch.setattr(challenge_service, "create", AsyncMock(return_value=9))
    monkeypatch.setattr(challenge_service, "accept", AsyncMock(return_value=None))
    monkeypatch.setattr(challenge_service, "reject", AsyncMock(return_value=None))
    monkeypatch.setattr(challenge_service, "cancel", AsyncMock(return_value=None))
    monkeypatch.setattr(challenge_service, "checkin", AsyncMock(return_value=record))
    monkeypatch.setattr(challenge_service, "detail", AsyncMock(return_value=challenge))
    monkeypatch.setattr(challenge_service, "list_challenges", AsyncMock(return_value=[challenge]))
    monkeypatch.setattr(
        challenge_service,
        "checkin_records",
        AsyncMock(
            return_value={"records": [record], "total": 1, "size": 10, "current": 1, "pages": 1}
        ),
    )
    monkeypatch.setattr(challenge_service, "pending", AsyncMock(return_value=[challenge]))

    requests = [
        ("POST", "/api/challenge/create", {"challengeType": "x", "title": "x", "targetDays": 1}),
        ("POST", "/api/challenge/accept/9", None),
        ("POST", "/api/challenge/reject/9", None),
        ("POST", "/api/challenge/cancel/9", None),
        ("POST", "/api/challenge/checkin", {"challengeId": 9}),
        ("GET", "/api/challenge/detail/9", None),
        ("GET", "/api/challenge/list", None),
        ("GET", "/api/challenge/checkin-records/9", None),
        ("GET", "/api/challenge/pending", None),
    ]
    expected = [
        {"code": 200, "message": "操作成功", "data": 9},
        {"code": 200, "message": "接受成功", "data": None},
        {"code": 200, "message": "已拒绝", "data": None},
        {"code": 200, "message": "已取消", "data": None},
        {"code": 200, "message": "操作成功", "data": record},
        {"code": 200, "message": "操作成功", "data": challenge},
        {"code": 200, "message": "操作成功", "data": [challenge]},
        {
            "code": 200,
            "message": "操作成功",
            "data": {"records": [record], "total": 1, "size": 10, "current": 1, "pages": 1},
        },
        {"code": 200, "message": "操作成功", "data": [challenge]},
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = [
            await client.request(method, path, json=json) for method, path, json in requests
        ]
    assert [response.json() for response in responses] == expected
