from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from packages.platform.catalog import Dish
from services.catalog.app.main import create_app as create_catalog_app
from services.dining.app.services.cart import _item_payload, list_items
from services.dining.app.services.catalog import HttpCatalogReader


def test_cart_item_payload_contains_price_snapshot_and_subtotal() -> None:
    item = SimpleNamespace(
        id=1,
        dish_id=8,
        dish_name="宫保鸡丁",
        image_url="https://example.test/dish.webp",
        unit_price=Decimal("12.30"),
        quantity=2,
        remark="少辣",
    )

    payload = _item_payload(item)

    assert payload["unitPrice"] == "12.30"
    assert payload["subtotal"] == "24.60"
    assert payload["remark"] == "少辣"


def test_dining_registers_cart_routes() -> None:
    from services.dining.app.main import create_app

    app = create_app(jwt_secret="dining-test-secret-" + "x" * 64)
    paths = {route.path for route in app.routes}
    assert {
        "/api/dining/cart",
        "/api/dining/cart/items",
        "/api/dining/cart/items/{item_id}",
    } <= paths


@pytest.mark.asyncio
async def test_dining_rejects_missing_token_before_database_dependency() -> None:
    from services.dining.app.main import create_app

    app = create_app(jwt_secret="dining-test-secret-" + "x" * 64)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining"
    ) as client:
        response = await client.get("/api/dining/cart")

    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "请先登录", "data": None}


@pytest.mark.asyncio
async def test_empty_cart_read_does_not_create_an_uncommitted_cart() -> None:
    class Session:
        def __init__(self):
            self.added = []

        async def scalar(self, query):
            return None

        def add(self, value):
            self.added.append(value)

    session = Session()
    result = await list_items(session, user_id=8, couple_id=None)

    assert result["cartId"] is None
    assert result["items"] == []
    assert session.added == []


@pytest.mark.asyncio
async def test_http_catalog_reader_returns_legal_dish_with_cart_price_contract() -> None:
    dish = Dish(
        slug="checkout-dish",
        name="可结算菜品",
        cuisine="chuan",
        tags=(),
        spicy_level=1,
        status="published",
        sources=(
            {
                "url": "https://example.test/source",
                "license": "CC-BY-4.0",
                "attribution": "Example Author",
                "reviewStatus": "approved",
            },
        ),
        id=801,
        unit_price=Decimal("19.90"),
    )

    class Store:
        async def get_published_dish(self, session, dish_reference):
            return dish if dish_reference == "801" else None

    @asynccontextmanager
    async def session_provider():
        yield SimpleNamespace()

    catalog_app = create_catalog_app(session_provider=session_provider, store=Store())
    reader = HttpCatalogReader("http://catalog", transport=httpx.ASGITransport(app=catalog_app))

    dish = await reader.get_dish(801, "catalog-contract-test")

    assert dish is not None
    assert dish["id"] == 801
    assert dish["name"] == "可结算菜品"
    assert dish["unitPrice"] == "19.90"


@pytest.mark.asyncio
async def test_http_catalog_reader_rejects_incomplete_published_contract() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "message": "操作成功",
                "data": {"id": 802, "name": "缺失价格", "status": "published"},
            },
        )

    reader = HttpCatalogReader("http://catalog", transport=httpx.MockTransport(handler))

    assert await reader.get_dish(802, "catalog-contract-invalid") is None
