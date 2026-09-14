"""Dining 对 catalog-service 的窄接口。

点菜服务只缓存订单快照，不拥有菜品主数据。加入购物车时必须从目录服务读取
当前已发布菜品，客户端提交的价格或名称不会作为结算依据。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

import httpx


class CatalogReader(Protocol):
    async def get_dish(self, dish_id: int, request_id: str) -> dict[str, Any] | None: ...

    async def list_cuisines(self, request_id: str) -> object: ...

    async def list_dishes(self, query: list[tuple[str, str]], request_id: str) -> object: ...


class HttpCatalogReader:
    def __init__(self, base_url: str, *, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=timeout_seconds)

    async def _get(
        self,
        path: str,
        request_id: str,
        params: Mapping[str, str] | list[tuple[str, str]] | None = None,
    ) -> object:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {"X-Request-ID": request_id}
            url = f"{self.base_url}{path}"
            if isinstance(params, list):
                response = await client.get(url, params=cast(Any, params), headers=headers)
            elif params is not None:
                response = await client.get(url, params=dict(params), headers=headers)
            else:
                response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") != 200:
            return None
        return payload.get("data")

    async def get_dish(self, dish_id: int, request_id: str) -> dict[str, Any] | None:
        payload = await self._get(f"/api/catalog/dishes/{dish_id}", request_id)
        if not isinstance(payload, dict) or payload.get("status") not in {None, "published"}:
            return None
        return payload

    async def list_cuisines(self, request_id: str) -> object:
        return await self._get("/api/catalog/cuisines", request_id)

    async def list_dishes(self, query: list[tuple[str, str]], request_id: str) -> object:
        return await self._get("/api/catalog/dishes", request_id, query)


__all__ = ["CatalogReader", "HttpCatalogReader"]
