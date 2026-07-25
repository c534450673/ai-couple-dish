import math
from datetime import datetime
from time import perf_counter
from typing import Any, Never

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, Order, Recipe, User
from app.schemas.business import CreateOrderRequest
from app.services.cart import RECIPE_UNIT_PRICE

logger = structlog.get_logger()

STATUS_PENDING = 0
STATUS_COOKING = 1
STATUS_WAITING_DELIVERY = 2
STATUS_COMPLETED = 3
STATUS_CANCELLED = 4
STATUS_REFUNDING = 5
STATUS_REFUNDED = 6
STATUS_NAMES = {
    STATUS_PENDING: "待接单",
    STATUS_COOKING: "制作中",
    STATUS_WAITING_DELIVERY: "待送达",
    STATUS_COMPLETED: "已完成",
    STATUS_CANCELLED: "已取消",
    STATUS_REFUNDING: "退款中",
    STATUS_REFUNDED: "已退款",
}


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "order",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(
    request: Request,
    operation: str,
    started: float,
    code: int,
    message: str,
) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _success(request: Request, operation: str, started: float, **ids: int) -> None:
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "success", started),
        **ids,
    )


async def _user(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


async def _couple_context(
    request: Request,
    session: AsyncSession,
    user: User,
    operation: str,
    started: float,
) -> tuple[int, int]:
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    couple = await session.scalar(
        select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    )
    partner = await session.scalar(
        select(User).where(
            User.couple_id == user.couple_id,
            User.id != user.id,
            User.is_deleted == 0,
        )
    )
    if couple is None or partner is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return couple.id, partner.id


async def create(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: CreateOrderRequest,
) -> int:
    started = perf_counter()
    operation = "create"
    user = await _user(request, session, user_id, operation, started)
    couple_id, partner_id = await _couple_context(request, session, user, operation, started)
    recipe = await session.scalar(
        select(Recipe).where(Recipe.id == payload.recipe_id, Recipe.is_deleted == 0)
    )
    if recipe is None:
        await _fail(request, operation, started, 8001, "菜谱不存在")
    if recipe.status != 1:
        await _fail(request, operation, started, 8003, "菜谱未发布")
    if recipe.user_id == user_id:
        await _fail(request, operation, started, 8002, "不能购买自己的菜谱")
    if recipe.user_id != partner_id:
        await _fail(request, operation, started, 8002, "只能购买伴侣的菜谱")
    order = Order(
        couple_id=couple_id,
        buyer_id=user_id,
        seller_id=recipe.user_id,
        recipe_id=recipe.id,
        recipe_name=recipe.title,
        quantity=payload.quantity,
        total_amount=RECIPE_UNIT_PRICE * payload.quantity,
        address=payload.address,
        status=STATUS_PENDING,
        remark=payload.remark,
    )
    session.add(order)
    await session.flush()
    await session.commit()
    await _success(
        request,
        operation,
        started,
        userId=user_id,
        orderId=order.id,
        recipeId=recipe.id,
    )
    return order.id


async def _locked_order(
    request: Request,
    session: AsyncSession,
    order_id: int,
    operation: str,
    started: float,
) -> Order:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        await _fail(request, operation, started, 7001, "订单不存在")
    return order


async def _transition(
    request: Request,
    session: AsyncSession,
    user_id: int,
    order_id: int,
    *,
    operation: str,
    role: str,
    expected: set[int],
    target: int,
    permission_message: str,
    status_message: str,
    status_code: int = 7002,
) -> None:
    started = perf_counter()
    await _user(request, session, user_id, operation, started)
    order = await _locked_order(request, session, order_id, operation, started)
    allowed = (
        order.buyer_id == user_id
        if role == "buyer"
        else order.seller_id == user_id
        if role == "seller"
        else user_id in {order.buyer_id, order.seller_id}
    )
    if not allowed:
        await _fail(request, operation, started, 9999, permission_message)
    if order.status not in expected:
        await _fail(request, operation, started, status_code, status_message)
    order.status = target
    now = datetime.now()
    if operation == "cancel":
        order.cancel_time = now
    elif operation == "accept":
        order.accept_time = now
    elif operation == "complete":
        order.complete_time = now
    await session.commit()
    await _success(request, operation, started, userId=user_id, orderId=order_id)


async def cancel(request: Request, session: AsyncSession, user_id: int, order_id: int) -> None:
    await _transition(
        request,
        session,
        user_id,
        order_id,
        operation="cancel",
        role="buyer",
        expected={STATUS_PENDING},
        target=STATUS_CANCELLED,
        permission_message="无权取消该订单",
        status_message="订单状态不允许取消",
        status_code=7003,
    )


async def accept(request: Request, session: AsyncSession, user_id: int, order_id: int) -> None:
    await _transition(
        request,
        session,
        user_id,
        order_id,
        operation="accept",
        role="seller",
        expected={STATUS_PENDING},
        target=STATUS_COOKING,
        permission_message="无权接单",
        status_message="订单状态不允许接单",
    )


async def start_cooking(
    request: Request, session: AsyncSession, user_id: int, order_id: int
) -> None:
    started = perf_counter()
    operation = "start_cooking"
    await _user(request, session, user_id, operation, started)
    order = await _locked_order(request, session, order_id, operation, started)
    if order.seller_id != user_id:
        await _fail(request, operation, started, 9999, "无权操作")
    if order.status != STATUS_COOKING:
        await _fail(request, operation, started, 7002, "订单状态不允许开始制作")
    await session.commit()
    await _success(request, operation, started, userId=user_id, orderId=order_id)


async def finish_cooking(
    request: Request, session: AsyncSession, user_id: int, order_id: int
) -> None:
    await _transition(
        request,
        session,
        user_id,
        order_id,
        operation="finish_cooking",
        role="seller",
        expected={STATUS_COOKING},
        target=STATUS_WAITING_DELIVERY,
        permission_message="无权操作",
        status_message="订单状态不允许完成制作",
    )


async def complete(request: Request, session: AsyncSession, user_id: int, order_id: int) -> None:
    await _transition(
        request,
        session,
        user_id,
        order_id,
        operation="complete",
        role="either",
        expected={STATUS_WAITING_DELIVERY},
        target=STATUS_COMPLETED,
        permission_message="无权操作",
        status_message="订单状态不允许确认完成",
    )


async def refund(
    request: Request,
    session: AsyncSession,
    user_id: int,
    order_id: int,
    reason: str | None,
) -> None:
    started = perf_counter()
    operation = "refund"
    await _user(request, session, user_id, operation, started)
    order = await _locked_order(request, session, order_id, operation, started)
    if order.buyer_id != user_id:
        await _fail(request, operation, started, 9999, "只有买家可以申请退款")
    if order.status not in {STATUS_PENDING, STATUS_COOKING}:
        await _fail(request, operation, started, 7002, "订单状态不允许退款")
    normalized_reason = reason.strip() if reason else ""
    if normalized_reason:
        prefix = f"{order.remark} | " if order.remark else ""
        order.remark = f"{prefix}退款原因: {normalized_reason}"
    order.status = STATUS_REFUNDING
    await session.commit()
    await _success(request, operation, started, userId=user_id, orderId=order_id)


async def confirm_refund(
    request: Request, session: AsyncSession, user_id: int, order_id: int
) -> None:
    await _transition(
        request,
        session,
        user_id,
        order_id,
        operation="confirm_refund",
        role="seller",
        expected={STATUS_REFUNDING},
        target=STATUS_REFUNDED,
        permission_message="只有卖家可以确认退款",
        status_message="订单状态不正确",
    )


def _time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def _payloads(session: AsyncSession, orders: list[Order]) -> list[dict[str, object | None]]:
    user_ids = {item for order in orders for item in (order.buyer_id, order.seller_id)}
    users: dict[int, User] = {}
    if user_ids:
        user_rows = await session.execute(
            select(User).where(User.id.in_(user_ids), User.is_deleted == 0)
        )
        users = {user.id: user for user in user_rows.scalars().all()}
    recipe_ids = {order.recipe_id for order in orders}
    recipes: dict[int, Recipe] = {}
    if recipe_ids:
        recipe_rows = await session.execute(
            select(Recipe).where(Recipe.id.in_(recipe_ids), Recipe.is_deleted == 0)
        )
        recipes = {recipe.id: recipe for recipe in recipe_rows.scalars().all()}
    result: list[dict[str, object | None]] = []
    for order in orders:
        buyer = users.get(order.buyer_id)
        seller = users.get(order.seller_id)
        recipe = recipes.get(order.recipe_id)
        result.append(
            {
                "id": order.id,
                "coupleId": order.couple_id,
                "buyerId": order.buyer_id,
                "buyerName": buyer.nick_name if buyer else None,
                "buyerAvatar": buyer.avatar_url if buyer else None,
                "sellerId": order.seller_id,
                "sellerName": seller.nick_name if seller else None,
                "sellerAvatar": seller.avatar_url if seller else None,
                "recipeId": order.recipe_id,
                "recipeName": order.recipe_name,
                "recipeCoverUrl": recipe.cover_url if recipe else None,
                "quantity": order.quantity,
                "totalAmount": order.total_amount,
                "address": order.address,
                "status": order.status,
                "statusDesc": STATUS_NAMES.get(order.status, "未知"),
                "remark": order.remark,
                "createTime": _time(order.create_time),
                "payTime": _time(order.pay_time),
                "acceptTime": _time(order.accept_time),
                "completeTime": _time(order.complete_time),
                "cancelTime": _time(order.cancel_time),
            }
        )
    return result


async def detail(
    request: Request, session: AsyncSession, user_id: int, order_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    user = await _user(request, session, user_id, operation, started)
    couple_id, _ = await _couple_context(request, session, user, operation, started)
    order = await session.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        await _fail(request, operation, started, 7001, "订单不存在")
    if order.couple_id != couple_id:
        await _fail(request, operation, started, 9999, "无权查看该订单")
    result = (await _payloads(session, [order]))[0]
    await _success(request, operation, started, userId=user_id, orderId=order_id)
    return result


async def _page(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    conditions: list[Any],
    status: int | None,
    page_num: int,
    page_size: int,
    started: float,
) -> dict[str, object]:
    filters = list(conditions)
    if status is not None:
        filters.append(Order.status == status)
    total = int((await session.scalar(select(func.count(Order.id)).where(*filters))) or 0)
    rows = await session.execute(
        select(Order)
        .where(*filters)
        .order_by(Order.create_time.desc(), Order.id.desc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
    )
    records = await _payloads(session, list(rows.scalars().all()))
    await _success(request, operation, started, userId=user_id)
    return {
        "records": records,
        "total": total,
        "size": page_size,
        "current": page_num,
        "pages": math.ceil(total / page_size) if total else 0,
    }


async def my_buy(
    request: Request,
    session: AsyncSession,
    user_id: int,
    status: int | None,
    page_num: int,
    page_size: int,
) -> dict[str, object]:
    started = perf_counter()
    await _user(request, session, user_id, "my_buy", started)
    return await _page(
        request,
        session,
        user_id,
        "my_buy",
        [Order.buyer_id == user_id],
        status,
        page_num,
        page_size,
        started,
    )


async def my_sell(
    request: Request,
    session: AsyncSession,
    user_id: int,
    status: int | None,
    page_num: int,
    page_size: int,
) -> dict[str, object]:
    started = perf_counter()
    await _user(request, session, user_id, "my_sell", started)
    return await _page(
        request,
        session,
        user_id,
        "my_sell",
        [Order.seller_id == user_id],
        status,
        page_num,
        page_size,
        started,
    )


async def couple_orders(
    request: Request,
    session: AsyncSession,
    user_id: int,
    status: int | None,
    page_num: int,
    page_size: int,
) -> dict[str, object]:
    started = perf_counter()
    user = await _user(request, session, user_id, "couple", started)
    couple_id, _ = await _couple_context(request, session, user, "couple", started)
    return await _page(
        request,
        session,
        user_id,
        "couple",
        [Order.couple_id == couple_id],
        status,
        page_num,
        page_size,
        started,
    )


async def pending_count(request: Request, session: AsyncSession, user_id: int) -> int:
    started = perf_counter()
    operation = "pending_count"
    await _user(request, session, user_id, operation, started)
    buy = await session.scalar(
        select(func.count(Order.id)).where(
            Order.buyer_id == user_id, Order.status == STATUS_WAITING_DELIVERY
        )
    )
    sell = await session.scalar(
        select(func.count(Order.id)).where(
            Order.seller_id == user_id,
            Order.status.in_([STATUS_PENDING, STATUS_COOKING]),
        )
    )
    await _success(request, operation, started, userId=user_id)
    return int(buy or 0) + int(sell or 0)
