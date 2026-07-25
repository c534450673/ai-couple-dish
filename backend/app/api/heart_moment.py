from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import HeartMomentRequest
from app.services import heart_moment as service

router = APIRouter(prefix="/heartMoment", tags=["心动时刻模块"])


@router.post("/create")
async def create(
    request: Request,
    payload: HeartMomentRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "心动时刻创建成功",
        "data": await service.create(request, session, user_id, payload),
    }


@router.get("/list")
async def list_moments(
    request: Request,
    page: int = Query(default=1),
    page_size: int = Query(default=20, alias="pageSize", le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.list_moments(request, session, user_id, page, page_size),
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


@router.get("/random")
async def random_moment(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.random_moment(request, session, user_id),
    }
