from datetime import UTC, datetime

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.auth import create_access_token, current_user_id, decode_access_token
from app.core.config import Settings
from app.core.errors import install_exception_handlers
from app.redis.client import RedisClient
from app.redis.keys import logout_blacklist_key

SECRET = "i" * 64


@pytest.mark.integration
async def test_blacklist_uses_remaining_token_ttl_and_rejects_token(redis_url: str) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    try:
        settings = Settings(
            _env_file=None,
            DB_PASSWORD="db-secret",  # noqa: S106
            JWT_SECRET=SECRET,  # noqa: S106
        )
        app = FastAPI()
        install_exception_handlers(app)
        app.state.settings = settings
        app.state.redis = redis

        @app.get("/protected")
        async def protected(user_id: int = Depends(current_user_id)) -> dict[str, int]:
            return {"userId": user_id}

        token = create_access_token(42, SECRET, expiration_ms=30_000)
        claims = decode_access_token(token, SECRET)
        remaining_seconds = max(1, int((claims.expires_at - datetime.now(UTC)).total_seconds()))
        key = logout_blacklist_key(claims.jti)
        await redis.raw.set(key, "1", ex=remaining_seconds)

        ttl = await redis.raw.ttl(key)
        assert abs(ttl - remaining_seconds) <= 1
        payload = jwt.decode(token, SECRET, algorithms=["HS512"])
        assert abs(ttl - int(payload["exp"] - datetime.now(UTC).timestamp())) <= 1

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 401
        assert response.json() == {
            "code": 401,
            "message": "登录已过期，请重新登录",
            "data": None,
        }
        assert token not in response.text
        assert claims.jti not in response.text
    finally:
        await redis.close()
