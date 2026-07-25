from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import notification as notification_service

router = APIRouter(prefix="/notification", tags=["通知模块"])


@router.get("/list")
async def list_notifications(
    request: Request,
    notification_type: int | None = Query(default=None, alias="type"),
    page: int = Query(default=1),
    page_size: int = Query(default=20, alias="pageSize"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    items = await notification_service.list_notifications(
        request, session, user_id, notification_type, page, page_size
    )
    return {"code": 200, "message": "操作成功", "data": items}


@router.get("/unreadCount")
async def unread_count(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await notification_service.unread_count(request, session, user_id),
    }


@router.put("/read/{id}")
async def mark_read(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await notification_service.mark_read(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.put("/readAll")
async def mark_all_read(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await notification_service.mark_all_read(request, session, user_id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/delete/{id}")
async def delete_notification(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await notification_service.delete_notification(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}
