from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import love_calendar as service

router = APIRouter(prefix="/loveCalendar", tags=["专属恋爱日历模块"])


@router.get("/month")
async def month(
    request: Request,
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.month(request, session, user_id, year, month),
    }


@router.get("/events/date")
async def events_by_date(
    request: Request,
    date: date = Query(...),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.events_by_date(request, session, user_id, date),
    }


@router.get("/events/range")
async def events_by_range(
    request: Request,
    start_date: date = Query(..., alias="startDate"),
    end_date: date = Query(..., alias="endDate"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.events_by_range(request, session, user_id, start_date, end_date),
    }


@router.get("/events/upcoming")
async def upcoming(
    request: Request,
    limit: int = Query(default=10, ge=0, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.upcoming(request, session, user_id, limit),
    }


@router.get("/events/today")
async def today(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.today(request, session, user_id),
    }


@router.get("/year/overview")
async def year_overview(
    request: Request,
    year: int | None = Query(default=None),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.year_overview(request, session, user_id, year),
    }
