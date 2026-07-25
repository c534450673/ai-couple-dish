from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import AddToCartRequest
from app.services import cart as service

router = APIRouter(prefix="/cart", tags=["购物车模块"])
CartIds = Annotated[list[int], Body(min_length=1)]


@router.post("/add")
async def add(
    request: Request,
    payload: AddToCartRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.add(request, session, user_id, payload),
    }


@router.put("/quantity/{cartId}")
async def update_quantity(
    request: Request,
    cart_id: int = Path(alias="cartId", ge=1),
    quantity: int = Query(ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.update_quantity(request, session, user_id, cart_id, quantity)
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/remove/{cartId}")
async def remove(
    request: Request,
    cart_id: int = Path(alias="cartId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.remove(request, session, user_id, cart_id)
    return {"code": 200, "message": "移除成功", "data": None}


@router.delete("/batch-remove")
async def batch_remove(
    request: Request,
    cart_ids: CartIds,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.batch_remove(request, session, user_id, cart_ids)
    return {"code": 200, "message": "移除成功", "data": None}


@router.delete("/clear")
async def clear(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.clear(request, session, user_id)
    return {"code": 200, "message": "清空成功", "data": None}


@router.get("/list")
async def list_items(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.list_items(request, session, user_id),
    }


@router.get("/count")
async def count(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.count(request, session, user_id),
    }


@router.post("/checkout")
async def checkout(
    request: Request,
    cart_ids: CartIds,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.checkout(request, session, user_id, cart_ids),
    }
