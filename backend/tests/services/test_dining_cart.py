from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from services.dining.app.services.cart import _item_payload, list_items


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
