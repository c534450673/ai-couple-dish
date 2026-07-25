from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

import structlog

from app.core.errors import BusinessError

RATE_LIMIT_KEY_PREFIX = "rate_limit:"
IDENTITY_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = redis.call('TTL', KEYS[1])
end
return {current, ttl}
"""

logger = structlog.get_logger()


class RateLimitRedis(Protocol):
    async def eval(self, script: str, numkeys: int, *values: object) -> object: ...


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    requests: int
    window_seconds: int

    def __post_init__(self) -> None:
        if (
            not self.scope
            or self.scope != self.scope.strip()
            or ":" in self.scope
            or any(unicodedata.category(char).startswith("C") for char in self.scope)
        ):
            raise ValueError("invalid rate limit scope")
        if (
            isinstance(self.requests, bool)
            or not isinstance(self.requests, int)
            or self.requests <= 0
        ):
            raise ValueError("rate limit requests must be positive")
        if (
            isinstance(self.window_seconds, bool)
            or not isinstance(self.window_seconds, int)
            or self.window_seconds <= 0
        ):
            raise ValueError("rate limit window must be positive")


def hash_user_identity(user_id: str | int, secret: str | bytes) -> str:
    return _hash_identity("user", str(user_id), secret)


def hash_ip_identity(ip: str, secret: str | bytes) -> str:
    try:
        normalized_ip = ipaddress.ip_address(ip).compressed
    except ValueError:
        normalized_ip = None
    if normalized_ip is None:
        raise ValueError("invalid IP identity")
    return _hash_identity("ip", normalized_ip, secret)


def _hash_identity(kind: str, raw_identity: str, secret: str | bytes) -> str:
    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not secret_bytes:
        raise ValueError("identity HMAC secret must not be empty")
    if not raw_identity:
        raise ValueError("identity must not be empty")
    message = f"rate-limit:{kind}\0{raw_identity}".encode()
    return hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()


async def check_rate_limit(
    redis: RateLimitRedis,
    policy: RateLimitPolicy,
    identity_hash: str,
) -> bool:
    if IDENTITY_HASH_PATTERN.fullmatch(identity_hash) is None:
        raise ValueError("identity hash must be 64 lowercase hexadecimal characters")

    key = f"{RATE_LIMIT_KEY_PREFIX}{policy.scope}:{identity_hash}"
    response = await redis.eval(RATE_LIMIT_SCRIPT, 1, key, policy.window_seconds)
    try:
        if not isinstance(response, (list, tuple)) or len(response) != 2:
            raise TypeError
        current = int(response[0])
        ttl = int(response[1])
        if current < 1 or ttl < 0:
            raise ValueError
    except (TypeError, ValueError, IndexError) as error:
        await logger.aerror(
            "rate_limit_response_invalid",
            module="rate_limit",
            operation="check_rate_limit",
            result="error",
            scope=policy.scope,
            errorCode="INVALID_REDIS_RESPONSE",
        )
        raise RuntimeError("invalid Redis rate limit response") from error

    allowed = current <= policy.requests
    await logger.ainfo(
        "rate_limit_checked",
        module="rate_limit",
        operation="check_rate_limit",
        result="allowed" if allowed else "limited",
        scope=policy.scope,
        current=current,
        limit=policy.requests,
        ttlSeconds=ttl,
    )
    return allowed


async def enforce_rate_limit(
    redis: RateLimitRedis,
    policy: RateLimitPolicy,
    identity_hash: str,
) -> None:
    if not await check_rate_limit(redis, policy, identity_hash):
        raise BusinessError(429, "操作过于频繁，请稍后重试", http_status=429)
