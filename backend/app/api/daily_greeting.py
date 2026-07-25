from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import DailyGreetingRequest
from app.services import daily_greeting as daily_greeting_service

router = APIRouter(prefix="/dailyGreeting", tags=["早安晚安心动打卡模块"])


@router.post("/send")
async def send(
    request: Request,
    payload: DailyGreetingRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "问候发送成功",
        "data": await daily_greeting_service.send(request, session, user_id, payload),
    }


@router.get("/today/status")
async def today_status(
    request: Request,
    greeting_type: int = Query(alias="greetingType", ge=1, le=2),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_greeting_service.today_status(request, session, user_id, greeting_type),
    }


@router.get("/both/status")
async def both_status(
    request: Request,
    greeting_type: int = Query(alias="greetingType", ge=1, le=2),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_greeting_service.both_status(request, session, user_id, greeting_type),
    }


@router.get("/streak")
async def streak(
    request: Request,
    streak_type: int = Query(alias="streakType", ge=1, le=2),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_greeting_service.streak(request, session, user_id, streak_type),
    }


@router.get("/history")
async def history(
    request: Request,
    greeting_type: int | None = Query(default=None, alias="greetingType", ge=1, le=2),
    limit: int = Query(default=30, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_greeting_service.history(
            request, session, user_id, greeting_type, limit
        ),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int = Path(gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await daily_greeting_service.detail(request, session, user_id, id),
    }
