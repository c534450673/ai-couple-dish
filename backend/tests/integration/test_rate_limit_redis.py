import asyncio

import pytest

from app.core.rate_limit import (
    RateLimitPolicy,
    check_rate_limit,
    hash_ip_identity,
    hash_user_identity,
)
from app.redis.client import RedisClient

SECRET = "integration-rate-limit-secret"  # noqa: S105


@pytest.mark.integration
async def test_concurrent_limit_is_atomic_and_sets_ttl(redis_url: str) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    raw_identity = "user-42"
    identity_hash = hash_user_identity(raw_identity, SECRET)
    policy = RateLimitPolicy(scope="user", requests=3, window_seconds=60)
    key = f"rate_limit:{policy.scope}:{identity_hash}"
    try:
        results = await asyncio.gather(
            *(check_rate_limit(redis.raw, policy, identity_hash) for _ in range(6))
        )

        assert results.count(True) == 3
        assert results.count(False) == 3
        ttl = await redis.raw.ttl(key)
        assert 0 < ttl <= policy.window_seconds
        keys = await redis.raw.keys("rate_limit:*")
        assert key in keys
        assert all(raw_identity not in stored_key for stored_key in keys)
    finally:
        await redis.raw.delete(key)
        await redis.close()


@pytest.mark.integration
async def test_existing_key_without_ttl_recovers_policy_ttl(redis_url: str) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    raw_identity = "203.0.113.42"
    identity_hash = hash_ip_identity(raw_identity, SECRET)
    policy = RateLimitPolicy(scope="ip", requests=3, window_seconds=45)
    key = f"rate_limit:{policy.scope}:{identity_hash}"
    try:
        await redis.raw.set(key, "1")
        assert await redis.raw.ttl(key) == -1

        assert await check_rate_limit(redis.raw, policy, identity_hash) is True

        ttl = await redis.raw.ttl(key)
        assert 0 < ttl <= policy.window_seconds
        assert raw_identity not in key
    finally:
        await redis.raw.delete(key)
        await redis.close()
