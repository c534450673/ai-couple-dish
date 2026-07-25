from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import SendFeedRequest
from app.services import feed as feed_service

router = APIRouter(prefix="/feed", tags=["投喂模块"])


@router.get("/today")
async def today(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await feed_service.today(request, session, user_id),
    }


@router.post("/send")
async def send(
    request: Request,
    payload: SendFeedRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "投喂发送成功",
        "data": await feed_service.send(request, session, user_id, payload),
    }


@router.get("/received")
async def received(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await feed_service.received(request, session, user_id),
    }


@router.get("/sent")
async def sent(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await feed_service.sent(request, session, user_id),
    }


@router.post("/accept/{id}")
async def accept(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await feed_service.accept(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/reject/{id}")
async def reject(
    request: Request,
    id: int,
    reason: str | None = Query(default=None, max_length=256),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await feed_service.reject(request, session, user_id, id, reason)
    return {"code": 200, "message": "操作成功", "data": None}
