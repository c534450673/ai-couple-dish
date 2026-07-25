from datetime import datetime
from time import perf_counter

import structlog
from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Notification

logger = structlog.get_logger()


def _log_fields(request: Request, operation: str, result: str, started: float) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "notification",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": "NONE",
    }


def _payload(item: Notification) -> dict[str, object | None]:
    return {
        "id": item.id,
        "userId": item.user_id,
        "type": item.type,
        "title": item.title,
        "content": item.content,
        "relatedId": item.related_id,
        "relatedType": item.related_type,
        "senderId": item.sender_id,
        "isRead": item.is_read,
        "readTime": item.read_time.isoformat() if item.read_time else None,
        "createTime": item.create_time.isoformat() if item.create_time else None,
    }


async def list_notifications(
    request: Request,
    session: AsyncSession,
    user_id: int,
    notification_type: int | None,
    page: int,
    page_size: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    if page < 1 or page_size < 1 or page_size > 100:
        raise BusinessError(9001, "参数无效")
    conditions = [Notification.user_id == user_id]
    if notification_type is not None:
        conditions.append(Notification.type == notification_type)
    result = await session.execute(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.create_time.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_payload(item) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "list", "success", started)
    )
    return items


async def unread_count(request: Request, session: AsyncSession, user_id: int) -> int:
    started = perf_counter()
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == 0
        )
    )
    count = int(result.scalar_one() or 0)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "unread_count", "success", started)
    )
    return count


async def mark_read(
    request: Request, session: AsyncSession, user_id: int, notification_id: int
) -> None:
    started = perf_counter()
    item = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    if item is not None and item.is_read == 0:
        item.is_read = 1
        item.read_time = datetime.now()
        await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "read_one", "success", started)
    )


async def mark_all_read(request: Request, session: AsyncSession, user_id: int) -> None:
    started = perf_counter()
    await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == 0)
        .values(is_read=1, read_time=datetime.now())
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "read_all", "success", started)
    )


async def delete_notification(
    request: Request, session: AsyncSession, user_id: int, notification_id: int
) -> None:
    started = perf_counter()
    item = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    if item is not None:
        await session.delete(item)
        await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "delete", "success", started)
    )
