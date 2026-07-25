from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import (
    AnniversaryCreateRequest,
    AnniversaryUpdateRequest,
    ReminderConfigRequest,
)
from app.services import anniversary as anniversary_service

router = APIRouter(prefix="/anniversary", tags=["纪念日模块"])


@router.get("/list")
async def list_anniversaries(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await anniversary_service.list_anniversaries(request, session, user_id),
    }


@router.get("/upcoming")
async def upcoming(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await anniversary_service.upcoming(request, session, user_id),
    }


@router.get("/next")
async def next_anniversary(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await anniversary_service.next_anniversary(request, session, user_id),
    }


@router.post("/add")
async def add(
    request: Request,
    payload: AnniversaryCreateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "纪念日添加成功",
        "data": await anniversary_service.add(request, session, user_id, payload),
    }


@router.put("/update/{id}")
async def update(
    request: Request,
    id: int,
    payload: AnniversaryUpdateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await anniversary_service.update(request, session, user_id, id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await anniversary_service.delete_anniversary(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/today")
async def today(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await anniversary_service.today(request, session, user_id),
    }


@router.put("/reminderConfig")
async def reminder_config(
    request: Request,
    payload: ReminderConfigRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await anniversary_service.update_reminder_config(request, session, user_id, payload)
    return {"code": 200, "message": "操作成功", "data": None}
