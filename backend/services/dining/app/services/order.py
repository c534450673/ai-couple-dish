"""订单快照、状态机和 outbox 写入。"""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from services.dining.app.models import (
    DiningOrder,
    DiningOrderItem,
    OrderStatusHistory,
    OutboxEvent,
    SharedCart,
    SharedCartItem,
)

logger = structlog.get_logger()
STATUSES = {
    "pending_confirmation": "待确认",
    "confirmed": "已确认",
    "cooking": "制作中",
    "completed": "已完成",
    "cancelled": "已取消",
}
TRANSITIONS: dict[str, set[str]] = {
    "pending_confirmation": {"confirmed", "cancelled"},
    "confirmed": {"cooking"},
    "cooking": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


async def create_from_cart(
    session: AsyncSession,
    *,
    user_id: int,
    couple_id: int | None,
    cart_id: int,
    item_ids: Iterable[int] | None,
    remark: str | None,
) -> DiningOrder:
    cart = await session.scalar(
        select(SharedCart).where(SharedCart.id == cart_id).with_for_update()
    )
    if (
        cart is None
        or (couple_id is not None and cart.couple_id != couple_id)
        or (couple_id is None and cart.user_id != user_id)
    ):
        raise ValueError("购物车不存在")
    query = select(SharedCartItem).where(SharedCartItem.cart_id == cart.id).with_for_update()
    selected = set(item_ids or [])
    if selected:
        query = query.where(SharedCartItem.id.in_(selected))
    items = list((await session.scalars(query)).all())
    if not items:
        raise ValueError("购物车为空")
    total = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
    order = DiningOrder(
        order_no=f"D{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(4).upper()}",
        couple_id=couple_id,
        user_id=user_id,
        status="pending_confirmation",
        total_amount=total,
        remark=remark,
    )
    session.add(order)
    await session.flush()
    for item in items:
        session.add(
            DiningOrderItem(
                order_id=order.id,
                dish_id=item.dish_id,
                quantity=item.quantity,
                dish_name=item.dish_name,
                image_url=item.image_url,
                unit_price=item.unit_price,
                remark=item.remark,
            )
        )
        await session.delete(item)
    await _history(session, order, None, "pending_confirmation", user_id, "create")
    await _outbox(session, "order_created", order, user_id)
    return order


async def transition(
    session: AsyncSession,
    *,
    order_id: int,
    user_id: int,
    target: str,
    reason: str | None = None,
) -> DiningOrder:
    order = await session.scalar(
        select(DiningOrder).where(DiningOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise ValueError("订单不存在")
    if order.user_id != user_id:
        if order.couple_id is None:
            raise PermissionError("无权操作该订单")
        member = await session.scalar(
            select(User.id).where(
                User.id == user_id,
                User.couple_id == order.couple_id,
                User.is_deleted == 0,
            )
        )
        if member is None:
            raise PermissionError("无权操作该订单")
    if target not in TRANSITIONS.get(order.status, set()):
        raise ValueError(f"订单状态不允许变更为{STATUSES.get(target, target)}")
    previous = order.status
    order.status = target
    order.version = (order.version or 0) + 1
    order.update_time = datetime.now()
    await _history(session, order, previous, target, user_id, reason)
    await _outbox(session, "order_status_changed", order, user_id)
    await logger.ainfo(
        "dining_order_status_changed",
        module="dining",
        operation="order_transition",
        result="success",
        userId=user_id,
        orderId=order.id,
        fromStatus=previous,
        toStatus=target,
    )
    return order


async def _history(
    session: AsyncSession,
    order: DiningOrder,
    old: str | None,
    new: str,
    operator_id: int,
    reason: str | None,
) -> None:
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=old,
            to_status=new,
            operator_id=operator_id,
            reason=reason,
        )
    )


async def _outbox(session: AsyncSession, event_type: str, order: DiningOrder, user_id: int) -> None:
    session.add(
        OutboxEvent(
            event_type=event_type,
            aggregate_type="dining_order",
            aggregate_id=order.id,
            payload=json.dumps(
                {
                    "orderId": order.id,
                    "orderNo": order.order_no,
                    "status": order.status,
                    "userId": user_id,
                },
                ensure_ascii=False,
            ),
        )
    )


def payload(order: DiningOrder, items: list[DiningOrderItem] | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "id": order.id,
        "orderNo": order.order_no,
        "coupleId": order.couple_id,
        "userId": order.user_id,
        "status": order.status,
        "statusDesc": STATUSES.get(order.status, "未知"),
        "totalAmount": str(order.total_amount),
        "remark": order.remark,
        "createTime": order.create_time.isoformat() if order.create_time else None,
    }
    if items is not None:
        result["items"] = [
            {
                "id": item.id,
                "dishId": item.dish_id,
                "dishName": item.dish_name,
                "imageUrl": item.image_url,
                "unitPrice": str(item.unit_price),
                "quantity": item.quantity,
                "remark": item.remark,
            }
            for item in items
        ]
    return result
