from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import WishCreateRequest, WishUpdateRequest
from app.services import wish as wish_service

router = APIRouter(prefix="/wish", tags=["心愿模块"])


@router.get("/list")
async def list_wishes(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await wish_service.list_wishes(request, session, user_id),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await wish_service.detail(request, session, user_id, id),
    }


@router.post("/add")
async def add(
    request: Request,
    payload: WishCreateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await wish_service.add(request, session, user_id, payload),
    }


@router.put("/update/{id}")
async def update(
    request: Request,
    id: int,
    payload: WishUpdateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await wish_service.update_wish(request, session, user_id, id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await wish_service.delete_wish(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/fulfill/{id}")
async def fulfill(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await wish_service.fulfill(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/unfulfill/{id}")
async def unfulfill(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await wish_service.unfulfill(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}
