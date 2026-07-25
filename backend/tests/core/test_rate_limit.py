import json
import traceback
from collections.abc import Sequence

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import install_exception_handlers
from app.core.rate_limit import (
    RateLimitPolicy,
    check_rate_limit,
    enforce_rate_limit,
    hash_ip_identity,
    hash_user_identity,
)


class StubRedis:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[str, int, Sequence[object]]] = []

    async def eval(self, script: str, numkeys: int, *values: object) -> object:
        self.calls.append((script, numkeys, values))
        return self.result


@pytest.mark.parametrize(
    ("scope", "requests", "window_seconds"),
    [
        ("", 1, 1),
        ("user:login", 1, 1),
        (" user", 1, 1),
        ("user ", 1, 1),
        ("user\nlogin", 1, 1),
        ("user\x00login", 1, 1),
        ("user", 0, 1),
        ("user", -1, 1),
        ("user", 1, 0),
        ("user", 1, -1),
    ],
)
def test_policy_rejects_invalid_values(scope: str, requests: int, window_seconds: int) -> None:
    with pytest.raises(ValueError):
        RateLimitPolicy(scope=scope, requests=requests, window_seconds=window_seconds)


def test_identity_helpers_return_domain_separated_hmac_sha256() -> None:
    secret = "rate-limit-secret"  # noqa: S105

    user_hash = hash_user_identity("user-42", secret)
    ip_hash = hash_ip_identity("203.0.113.42", secret)

    assert len(user_hash) == 64
    assert len(ip_hash) == 64
    assert user_hash.isascii() and user_hash.islower() and user_hash.isalnum()
    assert ip_hash.isascii() and ip_hash.islower() and ip_hash.isalnum()
    assert user_hash != ip_hash
    assert ip_hash != hash_user_identity("203.0.113.42", secret)
    assert user_hash == hash_user_identity("user-42", secret)
    assert "user-42" not in user_hash
    assert "203.0.113.42" not in ip_hash


@pytest.mark.parametrize("secret", ["", b""])
def test_identity_helpers_reject_empty_secret(secret: str | bytes) -> None:
    with pytest.raises(ValueError, match="secret"):
        hash_user_identity("user-42", secret)


def test_invalid_ip_error_does_not_retain_raw_identity() -> None:
    raw_identity = "203.0.113.999"

    with pytest.raises(ValueError, match="invalid IP identity") as caught:
        hash_ip_identity(raw_identity, "rate-limit-secret")

    assert caught.value.__cause__ is None
    assert raw_identity not in str(caught.value.__context__)
    assert raw_identity not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    "identity_hash",
    ["user-42", "A" * 64, "f" * 63, "g" * 64, "f" * 65],
)
async def test_check_rate_limit_rejects_unhashed_identity(identity_hash: str) -> None:
    redis = StubRedis([1, 60])
    policy = RateLimitPolicy(scope="user", requests=3, window_seconds=60)

    with pytest.raises(ValueError, match="identity hash"):
        await check_rate_limit(redis, policy, identity_hash)

    assert redis.calls == []


@pytest.mark.parametrize("result", [[1, 60], (b"1", b"60"), ["1", "60"]])
async def test_check_rate_limit_handles_supported_redis_eval_types(result: object) -> None:
    redis = StubRedis(result)
    policy = RateLimitPolicy(scope="user", requests=1, window_seconds=60)
    identity_hash = "a" * 64

    assert await check_rate_limit(redis, policy, identity_hash) is True
    script, numkeys, values = redis.calls[0]
    assert "INCR" in script
    assert "EXPIRE" in script
    assert numkeys == 1
    assert values == (f"rate_limit:user:{identity_hash}", 60)


async def test_check_rate_limit_accepts_ttl_zero_at_window_boundary() -> None:
    redis = StubRedis([1, 0])
    policy = RateLimitPolicy(scope="user", requests=1, window_seconds=60)

    assert await check_rate_limit(redis, policy, "a" * 64) is True


@pytest.mark.parametrize("result", [None, 1, [], [1], [1, 2, 3], ["bad", 60], [1, "bad"]])
async def test_check_rate_limit_rejects_malformed_redis_result_without_identity_leak(
    result: object,
) -> None:
    redis = StubRedis(result)
    policy = RateLimitPolicy(scope="user", requests=1, window_seconds=60)
    identity_hash = "a" * 64

    with structlog.testing.capture_logs() as logs:
        with pytest.raises(RuntimeError, match="invalid Redis rate limit response") as caught:
            await check_rate_limit(redis, policy, identity_hash)

    assert identity_hash not in str(caught.value)
    assert identity_hash not in json.dumps(logs)


async def test_enforce_rate_limit_returns_http_429_result_envelope() -> None:
    redis = StubRedis([4, 0])
    policy = RateLimitPolicy(scope="user", requests=3, window_seconds=60)
    identity_hash = "b" * 64
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/limited")
    async def limited() -> dict[str, bool]:
        await enforce_rate_limit(redis, policy, identity_hash)
        return {"allowed": True}

    with structlog.testing.capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/limited")

    assert response.status_code == 429
    assert response.json() == {
        "code": 429,
        "message": "操作过于频繁，请稍后重试",
        "data": None,
    }
    assert identity_hash not in response.text
    assert identity_hash not in json.dumps(logs, ensure_ascii=False)
