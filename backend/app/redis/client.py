from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis


class RedisClient:
    """管理启用字符串解码的异步 Redis 客户端。"""

    def __init__(self, url: str) -> None:
        self.raw: Redis[str] = Redis.from_url(
            url,
            decode_responses=True,
            health_check_interval=30,
        )

    async def connect(self) -> None:
        await self.ping()

    async def close(self) -> None:
        await self.raw.aclose()  # type: ignore[attr-defined]

    async def ping(self) -> bool:
        return bool(await self.raw.ping())


def get_redis(request: Request) -> Redis[str]:
    """返回应用生命周期内的底层 Redis 客户端。"""
    client: Redis[str] = request.app.state.redis.raw
    return client
