from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import MoodRecordRequest
from app.services import mood as mood_service

router = APIRouter(prefix="/mood", tags=["情绪投递箱模块"])


@router.post("/send")
async def send(
    request: Request,
    payload: MoodRecordRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "心情发送成功",
        "data": await mood_service.send(request, session, user_id, payload),
    }


@router.get("/today")
async def today(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await mood_service.today(request, session, user_id),
    }


@router.get("/history")
async def history(
    request: Request,
    limit: int = Query(default=30),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await mood_service.history(request, session, user_id, limit),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await mood_service.detail(request, session, user_id, id),
    }


@router.post("/read/{id}")
async def mark_read(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await mood_service.mark_read(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/stats")
async def stats(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await mood_service.stats(request, session, user_id),
    }


@router.get("/types")
async def types(
    request: Request,
    _: int = Depends(current_user_id),
) -> dict[str, object]:
    return {"code": 200, "message": "操作成功", "data": await mood_service.types(request)}


@router.get("/unread/count")
async def unread_count(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await mood_service.unread_count(request, session, user_id),
    }
