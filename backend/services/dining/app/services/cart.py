"""购物车领域服务。

所有写操作在同一会话内完成并锁定购物车行；订单服务会复用这里的
``cart_scope``，因此情侣与单人购物车不会串数据。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from services.dining.app.models import SharedCart, SharedCartItem

logger = structlog.get_logger()


async def cart_scope(
    session: AsyncSession, *, user_id: int, couple_id: int | None, lock: bool = False
) -> SharedCart:
    filters = (
        (SharedCart.couple_id == couple_id,)
        if couple_id is not None
        else (SharedCart.user_id == user_id,)
    )
    query = select(SharedCart).where(*filters)
    if lock:
        query = query.with_for_update()
    cart = await session.scalar(query)
    if cart is None:
        cart = SharedCart(couple_id=couple_id, user_id=None if couple_id else user_id)
        session.add(cart)
        await session.flush()
    return cart


async def list_items(
    session: AsyncSession, *, user_id: int, couple_id: int | None
) -> dict[str, object]:
    scope = (
        SharedCart.couple_id == couple_id
        if couple_id is not None
        else SharedCart.user_id == user_id
    )
    cart = await session.scalar(select(SharedCart).where(scope))
    if cart is None:
        return {
            "cartId": None,
            "coupleId": couple_id,
            "userId": None if couple_id is not None else user_id,
            "items": [],
            "totalAmount": "0.00",
            "count": 0,
        }
    rows = await session.scalars(
        select(SharedCartItem)
        .where(SharedCartItem.cart_id == cart.id)
        .order_by(SharedCartItem.id.asc())
    )
    items = list(rows.all())
    total = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
    return {
        "cartId": cart.id,
        "coupleId": cart.couple_id,
        "userId": cart.user_id,
        "items": [_item_payload(item) for item in items],
        "totalAmount": str(total.quantize(Decimal("0.01"))),
        "count": sum(item.quantity for item in items),
    }


async def add_item(
    session: AsyncSession,
    *,
    user_id: int,
    couple_id: int | None,
    dish: dict[str, Any],
    quantity: int,
    remark: str | None,
) -> dict[str, object]:
    try:
        dish_id = int(dish["id"])
        dish_name = str(dish["name"]).strip()
        raw_price = dish.get("unitPrice", dish.get("price"))
        unit_price = Decimal(str(raw_price))
    except (InvalidOperation, KeyError, TypeError, ValueError) as error:
        raise ValueError("菜品目录数据不完整") from error
    if not dish_name or raw_price is None or not unit_price.is_finite() or unit_price < 0:
        raise ValueError("菜品目录数据不完整")
    cart = await cart_scope(session, user_id=user_id, couple_id=couple_id, lock=True)
    item = await session.scalar(
        select(SharedCartItem)
        .where(SharedCartItem.cart_id == cart.id, SharedCartItem.dish_id == dish_id)
        .with_for_update()
    )
    if item is None:
        item = SharedCartItem(
            cart_id=cart.id,
            dish_id=dish_id,
            quantity=quantity,
            dish_name=dish_name,
            image_url=dish.get("imageUrl"),
            unit_price=unit_price,
            remark=remark,
        )
        session.add(item)
    else:
        item.quantity += quantity
        if remark is not None:
            item.remark = remark
        item.dish_name = dish_name
        item.image_url = dish.get("imageUrl")
        item.unit_price = unit_price
        item.update_time = datetime.now()
    cart.version += 1
    await session.flush()
    await logger.ainfo(
        "dining_cart_item_changed",
        module="dining",
        operation="cart_add",
        result="success",
        userId=user_id,
        cartId=cart.id,
        dishId=item.dish_id,
        quantity=item.quantity,
    )
    return _item_payload(item)


async def update_item(
    session: AsyncSession, *, user_id: int, couple_id: int | None, item_id: int, quantity: int
) -> dict[str, object]:
    cart = await cart_scope(session, user_id=user_id, couple_id=couple_id, lock=True)
    item = await session.scalar(
        select(SharedCartItem)
        .where(SharedCartItem.id == item_id, SharedCartItem.cart_id == cart.id)
        .with_for_update()
    )
    if item is None:
        raise ValueError("购物车项目不存在")
    item.quantity = quantity
    cart.version += 1
    return _item_payload(item)


async def remove_item(
    session: AsyncSession, *, user_id: int, couple_id: int | None, item_id: int
) -> None:
    cart = await cart_scope(session, user_id=user_id, couple_id=couple_id, lock=True)
    result = await session.execute(
        delete(SharedCartItem).where(
            SharedCartItem.id == item_id, SharedCartItem.cart_id == cart.id
        )
    )
    if isinstance(result, CursorResult) and result.rowcount == 0:
        raise ValueError("购物车项目不存在")
    cart.version += 1


async def clear(session: AsyncSession, *, user_id: int, couple_id: int | None) -> None:
    cart = await cart_scope(session, user_id=user_id, couple_id=couple_id, lock=True)
    await session.execute(delete(SharedCartItem).where(SharedCartItem.cart_id == cart.id))
    cart.version += 1


def _item_payload(item: SharedCartItem) -> dict[str, object]:
    return {
        "id": item.id,
        "dishId": item.dish_id,
        "dishName": item.dish_name,
        "imageUrl": item.image_url,
        "unitPrice": str(item.unit_price),
        "quantity": item.quantity,
        "remark": item.remark,
        "subtotal": str((item.unit_price * item.quantity).quantize(Decimal("0.01"))),
    }
