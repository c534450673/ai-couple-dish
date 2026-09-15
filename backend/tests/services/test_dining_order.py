from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from packages.platform.auth import issue_user_token
from services.dining.app.models import (
    DiningOrder,
    IdempotencyRecord,
    OrderStatusHistory,
    OutboxEvent,
    SharedCart,
)
from services.dining.app.services.idempotency import run_once
from services.dining.app.services.order import STATUSES, TRANSITIONS, payload, transition


class FakeSession:
    def __init__(self, scalars: list[object | None]) -> None:
        self.values = scalars
        self.added: list[object] = []
        self.queries: list[object] = []

    async def scalar(self, query: object) -> object | None:
        self.queries.append(query)
        return self.values.pop(0)

    def add(self, value: object) -> None:
        self.added.append(value)


def test_order_state_machine_only_allows_declared_flow() -> None:
    assert TRANSITIONS["pending_confirmation"] == {"confirmed", "cancelled"}
    assert TRANSITIONS["confirmed"] == {"cooking"}
    assert TRANSITIONS["cooking"] == {"completed"}
    assert TRANSITIONS["completed"] == set()
    assert TRANSITIONS["cancelled"] == set()


def test_order_payload_preserves_snapshot_fields() -> None:
    order = SimpleNamespace(
        id=11,
        order_no="D1",
        couple_id=None,
        user_id=7,
        status="pending_confirmation",
        total_amount=Decimal("20.00"),
        remark=None,
        create_time=datetime(2026, 9, 14, 12, 0),
    )
    item = SimpleNamespace(
        id=21,
        dish_id=5,
        dish_name="旧菜名",
        image_url="old.webp",
        unit_price=Decimal("10.00"),
        quantity=2,
        remark="不放香菜",
    )

    result = payload(order, [item])

    assert result["statusDesc"] == STATUSES["pending_confirmation"]
    assert result["coupleId"] is None
    assert result["items"][0]["dishName"] == "旧菜名"
    assert result["items"][0]["unitPrice"] == "10.00"


def test_new_shared_cart_has_python_version_default_for_async_writes() -> None:
    """Incrementing a freshly-created cart must not trigger implicit async IO."""
    cart = SharedCart(couple_id=7)

    assert cart.version == 0


def test_dining_registers_order_routes() -> None:
    from services.dining.app.main import create_app

    app = create_app(jwt_secret="dining-test-secret-" + "x" * 64)
    paths = {route.path for route in app.routes}
    assert {
        "/api/dining/orders",
        "/api/dining/orders/{order_id}",
        "/api/dining/orders/{order_id}/confirm",
        "/api/dining/orders/{order_id}/cancel",
        "/api/dining/orders/{order_id}/cooking",
        "/api/dining/orders/{order_id}/complete",
    } <= paths


@pytest.mark.asyncio
async def test_transition_locks_order_and_writes_history_and_outbox() -> None:
    row = DiningOrder(
        id=3,
        order_no="D3",
        couple_id=None,
        user_id=7,
        status="pending_confirmation",
        total_amount=Decimal("8.00"),
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    session = FakeSession([row])

    changed = await transition(session, order_id=3, user_id=7, target="confirmed")

    assert changed.status == "confirmed"
    assert session.queries[0]._for_update_arg is not None
    assert any(isinstance(item, OrderStatusHistory) for item in session.added)
    assert any(isinstance(item, OutboxEvent) for item in session.added)


@pytest.mark.asyncio
async def test_duplicate_confirmation_is_rejected_without_new_event() -> None:
    row = DiningOrder(
        id=4,
        order_no="D4",
        couple_id=None,
        user_id=7,
        status="confirmed",
        total_amount=Decimal("8.00"),
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    session = FakeSession([row])

    with pytest.raises(ValueError, match="状态不允许"):
        await transition(session, order_id=4, user_id=7, target="confirmed")

    assert session.added == []


@pytest.mark.asyncio
async def test_idempotency_returns_first_response_without_running_action() -> None:
    record = IdempotencyRecord(
        user_id=7,
        idempotency_key="same-key",
        response_code=200,
        response_json='{"code": 200, "message": "首次", "data": {"id": 1}}',
    )
    session = FakeSession([record])
    calls = 0

    async def action() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"code": 200, "message": "第二次"}

    result = await run_once(session, 7, "same-key", action)

    assert result["message"] == "首次"
    assert calls == 0


@pytest.mark.asyncio
async def test_idempotency_rechecks_after_user_lock_before_running_action() -> None:
    record = IdempotencyRecord(
        user_id=7,
        idempotency_key="same-key",
        response_code=200,
        response_json='{"code": 200, "message": "首次", "data": {"id": 1}}',
    )
    session = FakeSession([None, None, record])
    calls = 0

    async def action() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"code": 200, "message": "不应执行"}

    result = await run_once(session, 7, "same-key", action)

    assert result["message"] == "首次"
    assert calls == 0
    assert len(session.queries) == 3
    assert session.queries[0]._for_update_arg is not None
    assert session.queries[1]._for_update_arg is not None
    assert session.queries[2]._for_update_arg is not None


@pytest.mark.asyncio
async def test_unbound_user_cannot_read_another_users_order_detail() -> None:
    from services.dining.app.main import create_app

    secret = "dining-test-secret-" + "x" * 64
    session = FakeSession(
        [
            SimpleNamespace(id=8, couple_id=None),
            SimpleNamespace(id=12, user_id=7, couple_id=None),
        ]
    )

    @asynccontextmanager
    async def provide_session():
        yield session

    app = create_app(jwt_secret=secret, session_provider=provide_session)
    token = issue_user_token(user_id=8, secret=secret, expires_ms=60_000)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining"
    ) as client:
        response = await client.get(
            "/api/dining/orders/12", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert response.json() == {"code": 4041, "message": "订单不存在", "data": None}


@pytest.mark.asyncio
@pytest.mark.parametrize("idempotency_key", [None, "   "])
async def test_order_creation_requires_non_blank_idempotency_key(
    idempotency_key: str | None,
) -> None:
    from services.dining.app.main import create_app

    class Session:
        def __init__(self) -> None:
            self.scalar_calls = 0

        async def scalar(self, _query: object) -> object:
            self.scalar_calls += 1
            return SimpleNamespace(id=7, couple_id=None)

    session = Session()

    @asynccontextmanager
    async def provide_session():
        yield session

    secret = "dining-test-secret-" + "x" * 64
    app = create_app(jwt_secret=secret, session_provider=provide_session)
    token = issue_user_token(user_id=7, secret=secret, expires_ms=60_000)
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining"
    ) as client:
        response = await client.post("/api/dining/orders", headers=headers, json={})

    assert response.status_code == 200
    assert response.json() == {"code": 4002, "message": "Idempotency-Key不能为空", "data": None}
    assert session.scalar_calls == 1


@pytest.mark.asyncio
async def test_order_creation_rejects_overlong_idempotency_key_before_database_access() -> None:
    from services.dining.app.main import create_app

    class Session:
        def __init__(self) -> None:
            self.scalar_calls = 0

        async def scalar(self, _query: object) -> object:
            self.scalar_calls += 1
            return SimpleNamespace(id=7, couple_id=None)

    session = Session()

    @asynccontextmanager
    async def provide_session():
        yield session

    secret = "dining-test-secret-" + "x" * 64
    app = create_app(jwt_secret=secret, session_provider=provide_session)
    token = issue_user_token(user_id=7, secret=secret, expires_ms=60_000)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining"
    ) as client:
        response = await client.post(
            "/api/dining/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"  {'x' * 129}  ",
            },
            json={},
        )

    assert response.status_code == 200
    assert response.json() == {
        "code": 4002,
        "message": "Idempotency-Key长度不能超过128",
        "data": None,
    }
    assert session.scalar_calls == 0


@pytest.mark.asyncio
async def test_order_list_uses_bounded_sql_pagination() -> None:
    from services.dining.app.main import create_app

    class Result:
        def all(self) -> list[object]:
            return []

    class Session:
        def __init__(self) -> None:
            self.scalar_calls = 0
            self.page_statement: object | None = None

        async def scalar(self, _query: object) -> object:
            self.scalar_calls += 1
            return SimpleNamespace(id=7, couple_id=None) if self.scalar_calls == 1 else 23

        async def scalars(self, statement: object) -> Result:
            self.page_statement = statement
            return Result()

    session = Session()

    @asynccontextmanager
    async def provide_session():
        yield session

    secret = "dining-test-secret-" + "x" * 64
    app = create_app(jwt_secret=secret, session_provider=provide_session)
    token = issue_user_token(user_id=7, secret=secret, expires_ms=60_000)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining"
    ) as client:
        response = await client.get(
            "/api/dining/orders?page=3&pageSize=7",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["data"] == {"records": [], "total": 23}
    assert session.page_statement is not None
    statement = cast(Any, session.page_statement)
    assert statement._limit_clause.value == 7
    assert statement._offset_clause.value == 14
