from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import relationship_weather as service

router = APIRouter(prefix="/relationshipWeather", tags=["关系气象站模块"])


@router.get("/current")
async def current(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.current(request, session, user_id),
    }


@router.get("/interactions")
async def interactions(
    request: Request,
    limit: int = Query(default=10, ge=0, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.interactions(request, session, user_id, limit),
    }


@router.get("/suggestions")
async def suggestions(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.suggestions(request, session, user_id),
    }


@router.get("/forecast")
async def forecast(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.forecast(request, session, user_id),
    }
