import os
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import current_user_id
from app.core.config import Settings
from app.db.models import Recipe, User
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


EXPECTED_ROUTES = {
    ("POST", "/api/cart/add"),
    ("PUT", "/api/cart/quantity/{cartId}"),
    ("DELETE", "/api/cart/remove/{cartId}"),
    ("DELETE", "/api/cart/batch-remove"),
    ("DELETE", "/api/cart/clear"),
    ("GET", "/api/cart/list"),
    ("GET", "/api/cart/count"),
    ("POST", "/api/cart/checkout"),
    ("POST", "/api/order/create"),
    ("POST", "/api/order/cancel/{orderId}"),
    ("POST", "/api/order/accept/{orderId}"),
    ("POST", "/api/order/start-cooking/{orderId}"),
    ("POST", "/api/order/finish-cooking/{orderId}"),
    ("POST", "/api/order/complete/{orderId}"),
    ("POST", "/api/order/refund/{orderId}"),
    ("POST", "/api/order/confirm-refund/{orderId}"),
    ("GET", "/api/order/detail/{orderId}"),
    ("GET", "/api/order/my-buy"),
    ("GET", "/api/order/my-sell"),
    ("GET", "/api/order/couple"),
    ("GET", "/api/order/pending-count"),
}

AUTH_REQUESTS = [
    ("POST", "/api/cart/add", {"recipeId": 10, "quantity": 1}),
    ("PUT", "/api/cart/quantity/1?quantity=1", None),
    ("DELETE", "/api/cart/remove/1", None),
    ("DELETE", "/api/cart/batch-remove", [1]),
    ("DELETE", "/api/cart/clear", None),
    ("GET", "/api/cart/list", None),
    ("GET", "/api/cart/count", None),
    ("POST", "/api/cart/checkout", [1]),
    ("POST", "/api/order/create", {"recipeId": 10, "quantity": 1}),
    ("POST", "/api/order/cancel/1", None),
    ("POST", "/api/order/accept/1", None),
    ("POST", "/api/order/start-cooking/1", None),
    ("POST", "/api/order/finish-cooking/1", None),
    ("POST", "/api/order/complete/1", None),
    ("POST", "/api/order/refund/1?reason=changed-plan", None),
    ("POST", "/api/order/confirm-refund/1", None),
    ("GET", "/api/order/detail/1", None),
    ("GET", "/api/order/my-buy?status=0&pageNum=1&pageSize=10", None),
    ("GET", "/api/order/my-sell?status=0&pageNum=1&pageSize=10", None),
    ("GET", "/api/order/couple?status=0&pageNum=1&pageSize=10", None),
    ("GET", "/api/order/pending-count", None),
]


class ScriptedSession:
    """根据 SQL 目标表返回约定数据，保持 API 测试不依赖真实 MySQL。"""

    def __init__(
        self,
        *,
        user: User,
        partner: User | None = None,
        recipe: Recipe | None = None,
        cart_items: list[object] | None = None,
        order: object | None = None,
    ) -> None:
        self.user = user
        self.partner = partner
        self.recipe = recipe
        self.cart_items = cart_items or []
        self.order = order
        self.couple = SimpleNamespace(id=1, status=1)
        self.added: list[object] = []

    @staticmethod
    def _statement_text(statement: object) -> str:
        return str(statement).lower()

    async def scalar(self, statement: object, *_: object, **__: object) -> object | None:
        query = self._statement_text(statement)
        if "t_user" in query:
            return self.partner if " != " in query else self.user
        if "t_couple" in query:
            return self.couple
        if "t_recipe" in query:
            return self.recipe
        if "t_cart" in query:
            return self.cart_items[0] if self.cart_items else None
        return self.order

    async def execute(self, statement: object, *_: object, **__: object) -> object:
        query = self._statement_text(statement)
        rows = self.cart_items if "t_cart" in query else ([self.recipe] if self.recipe else [])
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows))

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        for index, value in enumerate(self.added, start=91):
            if getattr(value, "id", None) is None:
                value.id = index

    async def commit(self) -> None:
        return None


def _authenticated_app(session: ScriptedSession, user_id: int = 1):
    app = create_app(settings())

    async def authenticated_user() -> int:
        return user_id

    async def session_override():
        yield session

    app.dependency_overrides[current_user_id] = authenticated_user
    app.dependency_overrides[get_session] = session_override
    return app


def _schema(document: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in value:
        value = document["components"]["schemas"][value["$ref"].rsplit("/", maxsplit=1)[1]]
    return value


def _operation(document: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    return document["paths"][path][method.lower()]


def _parameter(operation: dict[str, Any], name: str, location: str) -> dict[str, Any]:
    return next(
        parameter
        for parameter in operation.get("parameters", [])
        if parameter["name"] == name and parameter["in"] == location
    )


def _user(*, couple_id: int | None = 1) -> User:
    return User(id=1, openid="buyer", couple_id=couple_id, is_deleted=0)


def _partner() -> User:
    return User(id=2, openid="seller", couple_id=1, is_deleted=0)


def _recipe(*, owner_id: int = 2, status: int = 1) -> Recipe:
    return Recipe(
        id=10,
        user_id=owner_id,
        title="partner-recipe",
        status=status,
        is_deleted=0,
    )


def _assert_business_rejection(response: Any, code: int) -> None:
    assert response.status_code == 200
    assert response.json()["code"] == code
    assert response.json()["data"] is None


def test_cart_and_order_routes_are_registered_with_spring_methods() -> None:
    app = create_app(settings())
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "DELETE"}
    }

    assert EXPECTED_ROUTES <= actual


def test_cart_and_order_parameter_locations_and_body_contracts() -> None:
    document = create_app(settings()).openapi()

    cart_add = _operation(document, "POST", "/api/cart/add")
    cart_add_schema = _schema(
        document, cart_add["requestBody"]["content"]["application/json"]["schema"]
    )
    assert cart_add_schema["required"] == ["recipeId"]
    assert set(cart_add_schema["properties"]) == {"recipeId", "quantity"}
    assert cart_add_schema["properties"]["quantity"]["minimum"] == 1

    update_quantity = _operation(document, "PUT", "/api/cart/quantity/{cartId}")
    assert _parameter(update_quantity, "cartId", "path")["required"] is True
    assert _parameter(update_quantity, "quantity", "query")["required"] is True
    assert _parameter(update_quantity, "quantity", "query")["schema"]["minimum"] == 1

    for method, path in (("DELETE", "/api/cart/batch-remove"), ("POST", "/api/cart/checkout")):
        body = _schema(
            document,
            _operation(document, method, path)["requestBody"]["content"]["application/json"][
                "schema"
            ],
        )
        assert body["type"] == "array"
        assert body["items"]["type"] == "integer"

    create_order = _operation(document, "POST", "/api/order/create")
    create_order_schema = _schema(
        document, create_order["requestBody"]["content"]["application/json"]["schema"]
    )
    assert create_order_schema["required"] == ["recipeId"]
    assert set(create_order_schema["properties"]) == {"recipeId", "quantity", "address", "remark"}
    assert create_order_schema["properties"]["quantity"]["minimum"] == 1

    for path in (
        "/api/order/cancel/{orderId}",
        "/api/order/accept/{orderId}",
        "/api/order/start-cooking/{orderId}",
        "/api/order/finish-cooking/{orderId}",
        "/api/order/complete/{orderId}",
        "/api/order/refund/{orderId}",
        "/api/order/confirm-refund/{orderId}",
        "/api/order/detail/{orderId}",
    ):
        method = "POST" if path != "/api/order/detail/{orderId}" else "GET"
        operation = _operation(document, method, path)
        assert _parameter(operation, "orderId", "path")["required"] is True

    refund = _operation(document, "POST", "/api/order/refund/{orderId}")
    assert _parameter(refund, "reason", "query")["required"] is False

    for path in ("/api/order/my-buy", "/api/order/my-sell", "/api/order/couple"):
        operation = _operation(document, "GET", path)
        assert _parameter(operation, "status", "query")["required"] is False
        assert _parameter(operation, "pageNum", "query")["schema"]["default"] == 1
        assert _parameter(operation, "pageSize", "query")["schema"]["default"] == 10


@pytest.mark.parametrize(("method", "path", "payload"), AUTH_REQUESTS)
async def test_cart_and_order_routes_require_authentication(
    method: str, path: str, payload: dict[str, object] | list[int] | None
) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/api/cart/add", {"recipeId": 10, "quantity": 0}),
        ("PUT", "/api/cart/quantity/1?quantity=0", None),
        ("POST", "/api/order/create", {"recipeId": 10, "quantity": 0}),
    ],
)
async def test_cart_and_order_reject_non_positive_quantity(
    method: str, path: str, payload: dict[str, int] | None
) -> None:
    app = _authenticated_app(ScriptedSession(user=_user()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None


async def test_order_creation_rejects_an_unbound_buyer() -> None:
    app = _authenticated_app(ScriptedSession(user=_user(couple_id=None), recipe=_recipe()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/order/create", json={"recipeId": 10, "quantity": 1})

    assert response.status_code == 200
    assert response.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}


async def test_order_creation_rejects_a_missing_recipe() -> None:
    app = _authenticated_app(ScriptedSession(user=_user(), partner=_partner()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/order/create", json={"recipeId": 10, "quantity": 1})

    _assert_business_rejection(response, 8001)


@pytest.mark.parametrize(
    ("recipe", "partner", "code"),
    [
        (_recipe(status=0), _partner(), 8003),
        (_recipe(owner_id=3), _partner(), 8002),
    ],
    ids=("unpublished_recipe", "recipe_not_owned_by_partner"),
)
async def test_order_creation_rejects_unpublished_or_non_partner_recipe(
    recipe: Recipe, partner: User, code: int
) -> None:
    app = _authenticated_app(ScriptedSession(user=_user(), partner=partner, recipe=recipe))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/order/create", json={"recipeId": 10, "quantity": 1})

    _assert_business_rejection(response, code)


@pytest.mark.parametrize(
    ("cart_owner", "expected_success"),
    [(1, True), (9, False)],
    ids=("creates_orders_and_removes_owned_items", "rejects_foreign_cart_item"),
)
async def test_checkout_only_accepts_owned_cart_items(
    cart_owner: int, expected_success: bool
) -> None:
    cart = SimpleNamespace(id=7, user_id=cart_owner, recipe_id=10, quantity=2, is_deleted=0)
    app = _authenticated_app(
        ScriptedSession(user=_user(), partner=_partner(), recipe=_recipe(), cart_items=[cart])
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/cart/checkout", json=[7])

    if expected_success:
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["data"] == [91]
    else:
        _assert_business_rejection(response, 9999)


async def test_checkout_rejects_missing_cart_items() -> None:
    app = _authenticated_app(ScriptedSession(user=_user(), partner=_partner(), recipe=_recipe()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/cart/checkout", json=[7])

    _assert_business_rejection(response, 9999)


async def test_order_operations_reject_missing_orders() -> None:
    app = _authenticated_app(ScriptedSession(user=_user(), order=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/order/cancel/11")

    _assert_business_rejection(response, 7001)


@pytest.mark.parametrize(
    ("path", "actor_id", "buyer_id", "seller_id", "status", "code"),
    [
        ("/api/order/cancel/11", 2, 1, 2, 0, 9999),
        ("/api/order/accept/11", 1, 1, 2, 0, 9999),
        ("/api/order/start-cooking/11", 1, 1, 2, 1, 9999),
        ("/api/order/finish-cooking/11", 1, 1, 2, 1, 9999),
        ("/api/order/complete/11", 3, 1, 2, 2, 9999),
        ("/api/order/refund/11", 2, 1, 2, 0, 9999),
        ("/api/order/confirm-refund/11", 1, 1, 2, 5, 9999),
        ("/api/order/cancel/11", 1, 1, 2, 3, 7003),
        ("/api/order/accept/11", 2, 1, 2, 4, 7002),
        ("/api/order/finish-cooking/11", 2, 1, 2, 0, 7002),
        ("/api/order/complete/11", 1, 1, 2, 1, 7002),
        ("/api/order/refund/11", 1, 1, 2, 3, 7002),
        ("/api/order/confirm-refund/11", 2, 1, 2, 0, 7002),
    ],
    ids=(
        "seller_cannot_cancel",
        "buyer_cannot_accept",
        "buyer_cannot_start_cooking",
        "buyer_cannot_finish_cooking",
        "outsider_cannot_complete",
        "seller_cannot_refund",
        "buyer_cannot_confirm_refund",
        "completed_order_cannot_cancel",
        "cancelled_order_cannot_accept",
        "pending_order_cannot_finish_cooking",
        "cooking_order_cannot_complete",
        "completed_order_cannot_refund",
        "pending_order_cannot_confirm_refund",
    ),
)
async def test_order_role_and_state_transition_rejections(
    path: str, actor_id: int, buyer_id: int, seller_id: int, status: int, code: int
) -> None:
    order = SimpleNamespace(id=11, buyer_id=buyer_id, seller_id=seller_id, status=status)
    app = _authenticated_app(ScriptedSession(user=_user(), order=order), user_id=actor_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(path)

    _assert_business_rejection(response, code)
