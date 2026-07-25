from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import daily_task as daily_task_service

router = APIRouter(prefix="/dailyTask", tags=["每日情侣任务模块"])


@router.get("/today")
async def today(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_task_service.today(request, session, user_id),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int = Path(gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_task_service.detail(request, session, user_id, id),
    }


@router.post("/progress/{id}")
async def progress(
    request: Request,
    count: int = Query(ge=1, le=1000),
    id: int = Path(gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await daily_task_service.update_progress(request, session, user_id, id, count)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/claim/{id}")
async def claim(
    request: Request,
    id: int = Path(gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await daily_task_service.claim(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/today/stats")
async def today_stats(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_task_service.today_stats(request, session, user_id),
    }
