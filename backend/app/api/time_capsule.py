from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import TimeCapsuleRequest
from app.services import time_capsule as service

router = APIRouter(prefix="/timeCapsule", tags=["时光胶囊模块"])


@router.post("/create")
async def create(
    request: Request,
    payload: TimeCapsuleRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "时光胶囊创建成功",
        "data": await service.create(request, session, user_id, payload),
    }


@router.get("/list")
async def list_capsules(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.list_capsules(request, session, user_id),
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
        "data": await service.detail(request, session, user_id, id),
    }


@router.post("/unlock/{id}")
async def unlock(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "时光胶囊已解锁",
        "data": await service.unlock(request, session, user_id, id),
    }


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.delete(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/pending")
async def pending(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.pending(request, session, user_id),
    }
