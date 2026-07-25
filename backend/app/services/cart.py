from datetime import datetime
from decimal import Decimal
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Cart, Couple, Order, Recipe, User
from app.schemas.business import AddToCartRequest

logger = structlog.get_logger()
RECIPE_UNIT_PRICE = Decimal("9.90")


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "cart",
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


async def _log_success(request: Request, operation: str, started: float, **ids: int) -> None:
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
    *,
    lock: bool = False,
) -> User:
    query = select(User).where(User.id == user_id, User.is_deleted == 0)
    if lock:
        query = query.with_for_update()
    user = await session.scalar(query)
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


async def _purchasable_recipe(
    request: Request,
    session: AsyncSession,
    user_id: int,
    partner_id: int,
    recipe_id: int,
    operation: str,
    started: float,
) -> Recipe:
    recipe = await session.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.is_deleted == 0)
    )
    if recipe is None:
        await _fail(request, operation, started, 8001, "菜谱不存在")
    if recipe.status != 1:
        await _fail(request, operation, started, 8003, "菜谱未发布")
    if recipe.user_id == user_id:
        await _fail(request, operation, started, 8002, "不能添加自己的菜谱")
    if recipe.user_id != partner_id:
        await _fail(request, operation, started, 8002, "只能购买伴侣的菜谱")
    return recipe


async def add(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: AddToCartRequest,
) -> int:
    started = perf_counter()
    operation = "add"
    user = await _user(request, session, user_id, operation, started, lock=True)
    _, partner_id = await _couple_context(request, session, user, operation, started)
    await _purchasable_recipe(
        request,
        session,
        user_id,
        partner_id,
        payload.recipe_id,
        operation,
        started,
    )
    rows = await session.execute(
        select(Cart)
        .where(
            Cart.user_id == user_id,
            Cart.recipe_id == payload.recipe_id,
            Cart.is_deleted == 0,
        )
        .order_by(Cart.id.asc())
        .with_for_update()
    )
    existing = list(rows.scalars().all())
    if existing:
        cart = existing[0]
        cart.quantity = sum(item.quantity for item in existing) + payload.quantity
        cart.update_time = datetime.now()
        for duplicate in existing[1:]:
            duplicate.is_deleted = 1
            duplicate.update_time = datetime.now()
    else:
        cart = Cart(
            user_id=user_id,
            recipe_id=payload.recipe_id,
            quantity=payload.quantity,
            is_deleted=0,
        )
        session.add(cart)
        await session.flush()
    await session.commit()
    await _log_success(
        request,
        operation,
        started,
        userId=user_id,
        cartId=cart.id,
        recipeId=payload.recipe_id,
    )
    return cart.id


async def _owned_cart(
    request: Request,
    session: AsyncSession,
    user_id: int,
    cart_id: int,
    operation: str,
    started: float,
) -> Cart:
    cart = await session.scalar(
        select(Cart).where(Cart.id == cart_id, Cart.is_deleted == 0).with_for_update()
    )
    if cart is None:
        await _fail(request, operation, started, 9999, "购物车项目不存在")
    if cart.user_id != user_id:
        await _fail(request, operation, started, 9999, "无权操作该购物车项目")
    return cart


async def update_quantity(
    request: Request,
    session: AsyncSession,
    user_id: int,
    cart_id: int,
    quantity: int,
) -> None:
    started = perf_counter()
    operation = "update_quantity"
    await _user(request, session, user_id, operation, started, lock=True)
    cart = await _owned_cart(request, session, user_id, cart_id, operation, started)
    cart.quantity = quantity
    cart.update_time = datetime.now()
    await session.commit()
    await _log_success(request, operation, started, userId=user_id, cartId=cart_id)


async def remove(
    request: Request,
    session: AsyncSession,
    user_id: int,
    cart_id: int,
) -> None:
    started = perf_counter()
    operation = "remove"
    await _user(request, session, user_id, operation, started, lock=True)
    cart = await _owned_cart(request, session, user_id, cart_id, operation, started)
    cart.is_deleted = 1
    cart.update_time = datetime.now()
    await session.commit()
    await _log_success(request, operation, started, userId=user_id, cartId=cart_id)


def _validated_ids(cart_ids: list[int]) -> list[int]:
    unique_ids = list(dict.fromkeys(cart_ids))
    if not unique_ids or len(unique_ids) != len(cart_ids) or any(item <= 0 for item in unique_ids):
        raise BusinessError(9999, "购物车项目不存在")
    return unique_ids


async def batch_remove(
    request: Request,
    session: AsyncSession,
    user_id: int,
    cart_ids: list[int],
) -> None:
    started = perf_counter()
    operation = "batch_remove"
    try:
        unique_ids = _validated_ids(cart_ids)
    except BusinessError as error:
        await _fail(request, operation, started, error.code, error.message)
    await _user(request, session, user_id, operation, started, lock=True)
    rows = await session.execute(
        select(Cart).where(Cart.id.in_(unique_ids), Cart.is_deleted == 0).with_for_update()
    )
    carts = list(rows.scalars().all())
    if len(carts) != len(unique_ids):
        await _fail(request, operation, started, 9999, "购物车项目不存在")
    if any(cart.user_id != user_id for cart in carts):
        await _fail(request, operation, started, 9999, "无权操作部分购物车项目")
    now = datetime.now()
    for cart in carts:
        cart.is_deleted = 1
        cart.update_time = now
    await session.commit()
    await _log_success(request, operation, started, userId=user_id)


async def clear(request: Request, session: AsyncSession, user_id: int) -> None:
    started = perf_counter()
    operation = "clear"
    await _user(request, session, user_id, operation, started, lock=True)
    await session.execute(
        update(Cart)
        .where(Cart.user_id == user_id, Cart.is_deleted == 0)
        .values(is_deleted=1, update_time=datetime.now())
    )
    await session.commit()
    await _log_success(request, operation, started, userId=user_id)


async def list_items(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "list"
    await _user(request, session, user_id, operation, started)
    rows = await session.execute(
        select(Cart)
        .where(Cart.user_id == user_id, Cart.is_deleted == 0)
        .order_by(Cart.create_time.desc(), Cart.id.desc())
    )
    carts = list(rows.scalars().all())
    recipe_ids = {cart.recipe_id for cart in carts}
    recipes: dict[int, Recipe] = {}
    if recipe_ids:
        recipe_rows = await session.execute(
            select(Recipe).where(Recipe.id.in_(recipe_ids), Recipe.is_deleted == 0)
        )
        recipes = {recipe.id: recipe for recipe in recipe_rows.scalars().all()}
    seller_ids = {recipe.user_id for recipe in recipes.values()}
    sellers: dict[int, User] = {}
    if seller_ids:
        seller_rows = await session.execute(
            select(User).where(User.id.in_(seller_ids), User.is_deleted == 0)
        )
        sellers = {seller.id: seller for seller in seller_rows.scalars().all()}
    result: list[dict[str, object | None]] = []
    for cart in carts:
        recipe = recipes.get(cart.recipe_id)
        seller = sellers.get(recipe.user_id) if recipe else None
        result.append(
            {
                "id": cart.id,
                "recipeId": cart.recipe_id,
                "recipeTitle": recipe.title if recipe else None,
                "recipeCoverUrl": recipe.cover_url if recipe else None,
                "recipeDescription": recipe.description if recipe else None,
                "sellerId": recipe.user_id if recipe else None,
                "sellerName": seller.nick_name if seller else None,
                "sellerAvatar": seller.avatar_url if seller else None,
                "quantity": cart.quantity,
                "unitPrice": RECIPE_UNIT_PRICE,
                "subtotal": RECIPE_UNIT_PRICE * cart.quantity,
                "createTime": cart.create_time.isoformat() if cart.create_time else None,
            }
        )
    await _log_success(request, operation, started, userId=user_id)
    return result


async def count(request: Request, session: AsyncSession, user_id: int) -> int:
    started = perf_counter()
    operation = "count"
    await _user(request, session, user_id, operation, started)
    value = await session.scalar(
        select(func.count(Cart.id)).where(Cart.user_id == user_id, Cart.is_deleted == 0)
    )
    await _log_success(request, operation, started, userId=user_id)
    return int(value or 0)


async def checkout(
    request: Request,
    session: AsyncSession,
    user_id: int,
    cart_ids: list[int],
) -> list[int]:
    started = perf_counter()
    operation = "checkout"
    try:
        unique_ids = _validated_ids(cart_ids)
    except BusinessError as error:
        await _fail(request, operation, started, error.code, "请选择要结算的商品")
    user = await _user(request, session, user_id, operation, started, lock=True)
    couple_id, partner_id = await _couple_context(request, session, user, operation, started)
    rows = await session.execute(
        select(Cart)
        .where(Cart.id.in_(unique_ids), Cart.is_deleted == 0)
        .order_by(Cart.id.asc())
        .with_for_update()
    )
    carts = list(rows.scalars().all())
    if len(carts) != len(unique_ids):
        await _fail(request, operation, started, 9999, "购物车项目不存在")
    if any(cart.user_id != user_id for cart in carts):
        await _fail(request, operation, started, 9999, "无权操作该购物车项目")

    orders: list[Order] = []
    for cart in carts:
        recipe = await _purchasable_recipe(
            request,
            session,
            user_id,
            partner_id,
            cart.recipe_id,
            operation,
            started,
        )
        order = Order(
            couple_id=couple_id,
            buyer_id=user_id,
            seller_id=recipe.user_id,
            recipe_id=recipe.id,
            recipe_name=recipe.title,
            quantity=cart.quantity,
            total_amount=RECIPE_UNIT_PRICE * cart.quantity,
            status=0,
        )
        session.add(order)
        orders.append(order)
    await session.flush()
    now = datetime.now()
    for cart in carts:
        cart.is_deleted = 1
        cart.update_time = now
    await session.commit()
    await _log_success(request, operation, started, userId=user_id)
    return [order.id for order in orders]
