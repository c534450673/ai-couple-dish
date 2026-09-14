"""Dining 对 catalog-service 的窄接口。

点菜服务只缓存订单快照，不拥有菜品主数据。加入购物车时必须从目录服务读取
当前已发布菜品，客户端提交的价格或名称不会作为结算依据。
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, cast

import httpx
import structlog

logger = structlog.get_logger()


class CatalogReader(Protocol):
    async def get_dish(self, dish_id: int, request_id: str) -> dict[str, Any] | None: ...

    async def list_cuisines(self, request_id: str) -> object: ...

    async def list_dishes(self, query: list[tuple[str, str]], request_id: str) -> object: ...


class HttpCatalogReader:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=timeout_seconds)
        self.transport = transport

    async def _get(
        self,
        path: str,
        request_id: str,
        params: Mapping[str, str] | list[tuple[str, str]] | None = None,
    ) -> object:
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
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
        try:
            payload = await self._get(f"/api/catalog/dishes/{dish_id}", request_id)
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
            await logger.ainfo(
                "dining_catalog_dish_unavailable",
                requestId=request_id,
                module="dining",
                operation="catalog_get_dish",
                result="not_found",
                dishId=dish_id,
            )
            return None
        if not isinstance(payload, dict) or not self._is_usable_dish(payload, dish_id):
            await logger.awarning(
                "dining_catalog_contract_rejected",
                requestId=request_id,
                module="dining",
                operation="catalog_get_dish",
                result="rejected",
                dishId=dish_id,
                errorCode="CATALOG_DISH_CONTRACT_INVALID",
            )
            return None
        await logger.ainfo(
            "dining_catalog_dish_loaded",
            requestId=request_id,
            module="dining",
            operation="catalog_get_dish",
            result="success",
            dishId=dish_id,
        )
        return payload

    @staticmethod
    def _is_usable_dish(payload: dict[str, Any], dish_id: int) -> bool:
        try:
            price = Decimal(str(payload.get("unitPrice", payload.get("price"))))
            returned_id = int(payload["id"])
        except (InvalidOperation, KeyError, TypeError, ValueError):
            return False
        return (
            returned_id == dish_id
            and payload.get("status") == "published"
            and bool(str(payload.get("name", "")).strip())
            and price.is_finite()
            and price >= 0
        )

    async def list_cuisines(self, request_id: str) -> object:
        return await self._get("/api/catalog/cuisines", request_id)

    async def list_dishes(self, query: list[tuple[str, str]], request_id: str) -> object:
        return await self._get("/api/catalog/dishes", request_id, query)


__all__ = ["CatalogReader", "HttpCatalogReader"]
