import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

from app.core.auth import create_access_token, current_user_id, decode_access_token
from app.core.config import Settings
from app.core.errors import BusinessError, install_exception_handlers
from app.redis.keys import couple_code_key, logout_blacklist_key, verify_code_key

SECRET = "s" * 64


def spring_claims(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "42",
        "userId": 42,
        "jti": "contract-jti",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return claims


def encode(claims: dict[str, Any], *, secret: str = SECRET, algorithm: str = "HS512") -> str:
    return jwt.encode(claims, secret, algorithm=algorithm)


def assert_unauthorized(token: str, *, forbidden_values: tuple[str, ...] = ()) -> None:
    with capture_logs() as logs:
        with pytest.raises(BusinessError) as caught:
            decode_access_token(token, SECRET)
    assert caught.value.code == 401
    assert caught.value.http_status == 401
    assert token not in caught.value.message
    assert "contract-jti" not in caught.value.message
    serialized_logs = json.dumps(logs, ensure_ascii=False)
    assert token not in serialized_logs
    assert "contract-jti" not in serialized_logs
    for value in forbidden_values:
        assert value not in caught.value.message
        assert value not in serialized_logs


def test_decodes_spring_hs512_claim_shape() -> None:
    claims = decode_access_token(encode(spring_claims()), SECRET)
    assert claims.user_id == 42
    assert claims.jti == "contract-jti"
    assert claims.expires_at > datetime.now(UTC)


def test_created_token_uses_spring_claim_shape() -> None:
    token = create_access_token(42, SECRET, expiration_ms=300_000)
    payload = jwt.decode(token, SECRET, algorithms=["HS512"])
    assert payload["sub"] == "42"
    assert payload["userId"] == 42
    assert isinstance(payload["jti"], str) and payload["jti"]
    assert isinstance(payload["iat"], int)
    assert 299 <= payload["exp"] - payload["iat"] <= 300


@pytest.mark.parametrize("missing_claim", ["sub", "userId", "jti", "iat", "exp"])
def test_rejects_missing_required_claim(missing_claim: str) -> None:
    claims = spring_claims()
    del claims[missing_claim]
    assert_unauthorized(encode(claims))


@pytest.mark.parametrize(
    "token",
    [
        encode(spring_claims(exp=datetime.now(UTC) - timedelta(seconds=1))),
        encode(spring_claims(), secret="w" * 64),
        encode(spring_claims(), algorithm="HS256"),
        encode(spring_claims(sub="not-an-integer")),
        encode(spring_claims(userId="not-an-integer")),
        encode(spring_claims(userId="42")),
        encode(spring_claims(userId=42.0)),
        encode(spring_claims(sub="42", userId=43)),
        encode(spring_claims(jti="")),
        encode(spring_claims(jti="unsafe:jti")),
    ],
    ids=[
        "expired",
        "wrong-signature",
        "wrong-algorithm",
        "invalid-sub",
        "invalid-user-id",
        "string-user-id",
        "float-user-id",
        "inconsistent-user-id",
        "empty-jti",
        "unsafe-jti",
    ],
)
def test_rejects_invalid_token_contract(token: str) -> None:
    assert_unauthorized(token)


@pytest.mark.parametrize(
    "claims",
    [
        spring_claims(exp="4102444800"),
        spring_claims(iat="1700000000"),
        spring_claims(iat=True),
        spring_claims(exp=10**30),
        spring_claims(iat=10**30),
        spring_claims(exp=float("nan")),
        spring_claims(exp=float("inf")),
        spring_claims(iat=float("nan")),
        spring_claims(iat=float("inf")),
    ],
    ids=[
        "string-exp",
        "string-iat",
        "bool-iat",
        "overflow-exp",
        "overflow-iat",
        "nan-exp",
        "infinite-exp",
        "nan-iat",
        "infinite-iat",
    ],
)
def test_rejects_invalid_numeric_date_claims(claims: dict[str, Any]) -> None:
    invalid_values = tuple(
        str(claims[name])
        for name in ("iat", "exp")
        if not isinstance(claims[name], datetime)
    )
    assert_unauthorized(encode(claims), forbidden_values=invalid_values)


def test_redis_keys_keep_spring_compatible_names() -> None:
    assert logout_blacklist_key("safe-jti") == "logout:blacklist:safe-jti"
    assert verify_code_key("13800138000") == "user:verify:code:13800138000"
    assert couple_code_key("ABC123") == "couple:code:ABC123"


@pytest.mark.parametrize("jti", ["", "contains:colon"])
def test_logout_key_rejects_unsafe_jti(jti: str) -> None:
    with pytest.raises(ValueError, match="invalid jti"):
        logout_blacklist_key(jti)


class FakeRawRedis:
    def __init__(self, *, blacklisted: bool = False) -> None:
        self.blacklisted = blacklisted
        self.queried_keys: list[str] = []

    async def exists(self, key: str) -> int:
        self.queried_keys.append(key)
        return int(self.blacklisted)


def auth_app(*, blacklisted: bool = False) -> tuple[FastAPI, FakeRawRedis]:
    app = FastAPI()
    install_exception_handlers(app)
    app.state.settings = Settings(
        _env_file=None,
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET=SECRET,  # noqa: S106
    )
    raw = FakeRawRedis(blacklisted=blacklisted)
    app.state.redis = type("RedisState", (), {"raw": raw})()

    @app.get("/protected")
    async def protected(user_id: int = Depends(current_user_id)) -> dict[str, int]:
        return {"userId": user_id}

    return app, raw


async def request_protected(
    authorization: str | list[tuple[str, str]] | None,
    *,
    blacklisted: bool = False,
) -> tuple[Any, FakeRawRedis]:
    app, raw = auth_app(blacklisted=blacklisted)
    headers: dict[str, str] | list[tuple[str, str]] = {}
    if isinstance(authorization, str):
        headers = {"Authorization": authorization}
    elif authorization is not None:
        headers = authorization
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/protected", headers=headers)
    return response, raw


async def test_current_user_returns_user_id_and_checks_blacklist() -> None:
    token = encode(spring_claims())
    response, raw = await request_protected(f"Bearer {token}")
    assert response.status_code == 200
    assert response.json() == {"userId": 42}
    assert raw.queried_keys == ["logout:blacklist:contract-jti"]


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Basic credentials",
        "Bearer ",
        "Bearer token with spaces",
        "Bearer token,second-token",
        [("Authorization", "Bearer first"), ("Authorization", "Bearer second")],
    ],
)
async def test_current_user_rejects_invalid_authorization_with_401_envelope(
    authorization: str | list[tuple[str, str]] | None,
) -> None:
    response, raw = await request_protected(authorization)
    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None
    assert response.json()["message"]
    assert raw.queried_keys == []


async def test_current_user_rejects_blacklisted_token_with_401_envelope() -> None:
    token = encode(spring_claims())
    response, raw = await request_protected(f"Bearer {token}", blacklisted=True)
    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "登录已过期，请重新登录", "data": None}
    assert raw.queried_keys == ["logout:blacklist:contract-jti"]
    assert token not in response.text
    assert "contract-jti" not in response.text


async def test_current_user_rejects_duplicate_headers_before_redis_lookup() -> None:
    token = encode(spring_claims())
    response, raw = await request_protected(
        [("Authorization", f"Bearer {token}"), ("Authorization", "arbitrary-second-value")]
    )
    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None
    assert token not in response.text
    assert raw.queried_keys == []
