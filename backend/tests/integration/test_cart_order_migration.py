import asyncio
import logging
import os
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import create_access_token
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient

SECRET = "o" * 64
TOKEN_EXPIRATION_MS = 300_000
logger = logging.getLogger(__name__)


def _reset_schema(connection: Connection) -> None:
    table_names = inspect(connection).get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in table_names:
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    schema_path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = schema_path.read_text()
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_cart_order_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        logger.info("cart_order_schema_ready tables_source=schema-test.sql")
        yield engine
    finally:
        await engine.dispose()


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, SECRET, expiration_ms=TOKEN_EXPIRATION_MS)
    return {"Authorization": f"Bearer {token}"}


@dataclass(frozen=True)
class CartOrderContext:
    client: AsyncClient
    engine: AsyncEngine
    auth: dict[int, dict[str, str]]


async def _seed_two_couples(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user (id, openid, nick_name, couple_id, status, is_deleted)
                VALUES
                    (101, 'cart-buyer-one', '买家甲', 11, 1, 0),
                    (102, 'cart-seller-one', '卖家乙', 11, 1, 0),
                    (201, 'cart-buyer-two', '买家丙', 22, 1, 0),
                    (202, 'cart-seller-two', '卖家丁', 22, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status)
                VALUES
                    (11, 'CART-COUPLE-ONE', 101, 102, 1),
                    (22, 'CART-COUPLE-TWO', 201, 202, 1)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_recipe
                    (id, user_id, title, status, like_count, collect_count, is_deleted)
                VALUES
                    (1001, 102, '一号情侣菜谱', 1, 0, 0, 0),
                    (1002, 102, '一号情侣备用菜谱', 1, 0, 0, 0),
                    (2001, 202, '二号情侣菜谱', 1, 0, 0, 0)
                """
            )
        )
    logger.info(
        "cart_order_seed_completed couples=%s users=%s recipes=%s",
        [11, 22],
        [101, 102, 201, 202],
        [1001, 1002, 2001],
    )


@pytest.fixture
async def cart_order_context(
    mysql_cart_order_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[CartOrderContext]:
    await _seed_two_couples(mysql_cart_order_engine)
    redis = RedisClient(redis_url)
    await redis.connect()
    assert await redis.raw.ping() is True
    session_factory = async_sessionmaker(mysql_cart_order_engine, expire_on_commit=False)
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield CartOrderContext(
                client=client,
                engine=mysql_cart_order_engine,
                auth={user_id: _headers(user_id) for user_id in (101, 102, 201, 202)},
            )
    finally:
        await redis.close()


def _response_code(response: Response) -> int:
    payload = response.json()
    assert response.status_code == 200, payload
    assert set(payload) == {"code", "message", "data"}
    return int(payload["code"])


def _log_responses(operation: str, responses: Sequence[Response]) -> None:
    logger.info(
        "cart_order_concurrent_result operation=%s responses=%s",
        operation,
        [
            {
                "httpStatus": response.status_code,
                "businessCode": response.json().get("code"),
                "requestId": response.headers.get("X-Request-ID"),
            }
            for response in responses
        ],
    )


async def _add_cart(
    context: CartOrderContext, user_id: int, recipe_id: int, quantity: int = 1
) -> int:
    response = await context.client.post(
        "/api/cart/add",
        headers=context.auth[user_id],
        json={"recipeId": recipe_id, "quantity": quantity},
    )
    assert _response_code(response) == 200, response.json()
    return int(response.json()["data"])


async def _checkout(context: CartOrderContext, user_id: int, cart_id: int) -> int:
    response = await context.client.post(
        "/api/cart/checkout", headers=context.auth[user_id], json=[cart_id]
    )
    assert _response_code(response) == 200, response.json()
    order_ids = response.json()["data"]
    assert isinstance(order_ids, list) and len(order_ids) == 1
    return int(order_ids[0])


async def _fetch_all(
    engine: AsyncEngine, statement: str, **parameters: Any
) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), parameters)
        return [dict(row) for row in result.mappings().all()]


@pytest.mark.integration
async def test_concurrent_duplicate_add_keeps_one_cart_and_accumulates_every_quantity(
    cart_order_context: CartOrderContext,
) -> None:
    context = cart_order_context
    request_count = 8
    quantity_per_request = 2

    responses = await asyncio.gather(
        *[
            context.client.post(
                "/api/cart/add",
                headers=context.auth[101],
                json={"recipeId": 1001, "quantity": quantity_per_request},
            )
            for _ in range(request_count)
        ]
    )
    _log_responses("concurrent_add", responses)

    assert [_response_code(response) for response in responses] == [200] * request_count
    assert len({int(response.json()["data"]) for response in responses}) == 1
    rows = await _fetch_all(
        context.engine,
        """
        SELECT id, quantity, is_deleted
        FROM t_cart
        WHERE user_id = :user_id AND recipe_id = :recipe_id AND is_deleted = 0
        """,
        user_id=101,
        recipe_id=1001,
    )
    logger.info("cart_order_database_result operation=concurrent_add rows=%s", rows)
    assert len(rows) == 1
    assert rows[0]["quantity"] == request_count * quantity_per_request


@pytest.mark.integration
async def test_concurrent_checkout_creates_one_order_and_soft_deletes_cart_atomically(
    cart_order_context: CartOrderContext,
) -> None:
    context = cart_order_context
    cart_id = await _add_cart(context, 101, 1001, quantity=3)

    responses = await asyncio.gather(
        *[
            context.client.post("/api/cart/checkout", headers=context.auth[101], json=[cart_id])
            for _ in range(2)
        ]
    )
    _log_responses("concurrent_checkout", responses)

    codes = [_response_code(response) for response in responses]
    assert sorted(codes) == [200, 9999]
    orders = await _fetch_all(
        context.engine,
        """
        SELECT id, couple_id, buyer_id, seller_id, recipe_id, quantity, status
        FROM t_order
        WHERE buyer_id = :buyer_id AND recipe_id = :recipe_id
        """,
        buyer_id=101,
        recipe_id=1001,
    )
    carts = await _fetch_all(
        context.engine,
        "SELECT id, quantity, is_deleted FROM t_cart WHERE id = :cart_id",
        cart_id=cart_id,
    )
    logger.info(
        "cart_order_database_result operation=concurrent_checkout orders=%s carts=%s",
        orders,
        carts,
    )
    assert len(orders) == 1
    assert orders[0] == {
        "id": orders[0]["id"],
        "couple_id": 11,
        "buyer_id": 101,
        "seller_id": 102,
        "recipe_id": 1001,
        "quantity": 3,
        "status": 0,
    }
    assert carts == [{"id": cart_id, "quantity": 3, "is_deleted": 1}]


@pytest.mark.integration
async def test_checkout_failure_rolls_back_without_deleting_cart(
    cart_order_context: CartOrderContext,
) -> None:
    context = cart_order_context
    cart_id = await _add_cart(context, 101, 1002, quantity=4)
    async with context.engine.begin() as connection:
        await connection.execute(
            text("UPDATE t_recipe SET status = 0 WHERE id = :recipe_id"), {"recipe_id": 1002}
        )

    response = await context.client.post(
        "/api/cart/checkout", headers=context.auth[101], json=[cart_id]
    )
    logger.info(
        "cart_order_failure_result operation=checkout_unpublished_recipe httpStatus=%s "
        "businessCode=%s requestId=%s",
        response.status_code,
        response.json().get("code"),
        response.headers.get("X-Request-ID"),
    )
    assert _response_code(response) != 200

    carts = await _fetch_all(
        context.engine,
        "SELECT id, quantity, is_deleted FROM t_cart WHERE id = :cart_id",
        cart_id=cart_id,
    )
    orders = await _fetch_all(
        context.engine,
        "SELECT id FROM t_order WHERE buyer_id = :buyer_id AND recipe_id = :recipe_id",
        buyer_id=101,
        recipe_id=1002,
    )
    logger.info(
        "cart_order_database_result operation=checkout_rollback carts=%s orders=%s",
        carts,
        orders,
    )
    assert carts == [{"id": cart_id, "quantity": 4, "is_deleted": 0}]
    assert orders == []


@pytest.mark.integration
async def test_concurrent_accept_and_cancel_allows_exactly_one_pending_transition(
    cart_order_context: CartOrderContext,
) -> None:
    context = cart_order_context
    order_id = await _checkout(context, 101, await _add_cart(context, 101, 1001))

    responses = await asyncio.gather(
        context.client.post(f"/api/order/accept/{order_id}", headers=context.auth[102]),
        context.client.post(f"/api/order/accept/{order_id}", headers=context.auth[102]),
        context.client.post(f"/api/order/cancel/{order_id}", headers=context.auth[101]),
        context.client.post(f"/api/order/cancel/{order_id}", headers=context.auth[101]),
    )
    _log_responses("concurrent_accept_cancel", responses)

    codes = [_response_code(response) for response in responses]
    assert codes.count(200) == 1
    assert all(code in {200, 7002, 7003} for code in codes)
    orders = await _fetch_all(
        context.engine,
        """
        SELECT status, accept_time, cancel_time
        FROM t_order
        WHERE id = :order_id
        """,
        order_id=order_id,
    )
    logger.info("cart_order_database_result operation=concurrent_accept_cancel rows=%s", orders)
    assert len(orders) == 1
    order = orders[0]
    assert order["status"] in {1, 4}
    assert (order["accept_time"] is not None) is (order["status"] == 1)
    assert (order["cancel_time"] is not None) is (order["status"] == 4)


@pytest.mark.integration
async def test_cart_and_order_data_are_isolated_between_couples(
    cart_order_context: CartOrderContext,
) -> None:
    context = cart_order_context
    cart_id = await _add_cart(context, 101, 1001)

    outsider_cart = await context.client.get("/api/cart/list", headers=context.auth[201])
    outsider_checkout = await context.client.post(
        "/api/cart/checkout", headers=context.auth[201], json=[cart_id]
    )
    assert _response_code(outsider_cart) == 200
    assert outsider_cart.json()["data"] == []
    assert _response_code(outsider_checkout) == 9999
    assert await _fetch_all(
        context.engine,
        "SELECT id FROM t_cart WHERE id = :cart_id AND is_deleted = 0",
        cart_id=cart_id,
    ) == [{"id": cart_id}]

    order_id = await _checkout(context, 101, cart_id)
    outsider_detail = await context.client.get(
        f"/api/order/detail/{order_id}", headers=context.auth[201]
    )
    outsider_accept = await context.client.post(
        f"/api/order/accept/{order_id}", headers=context.auth[202]
    )
    outsider_cancel = await context.client.post(
        f"/api/order/cancel/{order_id}", headers=context.auth[201]
    )
    logger.info(
        "cart_order_isolation_result orderId=%s detailCode=%s acceptCode=%s cancelCode=%s",
        order_id,
        outsider_detail.json().get("code"),
        outsider_accept.json().get("code"),
        outsider_cancel.json().get("code"),
    )
    assert _response_code(outsider_detail) == 9999
    assert _response_code(outsider_accept) == 9999
    assert _response_code(outsider_cancel) == 9999

    outsider_orders = await context.client.get("/api/order/couple", headers=context.auth[201])
    assert _response_code(outsider_orders) == 200
    assert outsider_orders.json()["data"]["records"] == []
