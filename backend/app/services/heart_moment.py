from datetime import datetime
from secrets import randbelow
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import HeartMoment, User
from app.schemas.business import HeartMomentRequest

logger = structlog.get_logger()


def _fields(
    request: Request, operation: str, result: str, started: float, error: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "heart_moment",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed", **_fields(request, operation, "rejected", started, str(code))
    )
    raise BusinessError(code, message)


async def _couple_id(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> int:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user.couple_id


async def _payload(session: AsyncSession, item: HeartMoment) -> dict[str, object | None]:
    creator = await session.scalar(select(User).where(User.id == item.creator_id))
    minutes = (
        max(0, int((datetime.now() - item.create_time).total_seconds() // 60))
        if item.create_time
        else 0
    )
    time_desc = (
        "刚刚"
        if minutes < 1
        else f"{minutes}分钟前"
        if minutes < 60
        else f"{minutes // 60}小时前"
        if minutes < 1440
        else f"{minutes // 1440}天前"
        if minutes < 10080
        else item.create_time.date().isoformat()
    )
    return {
        "id": item.id,
        "momentType": item.moment_type,
        "content": item.content,
        "mediaUrl": item.media_url,
        "createTime": item.create_time.isoformat() if item.create_time else None,
        "timeDesc": time_desc,
        "creator": {
            "id": creator.id,
            "nickName": creator.nick_name,
            "avatarUrl": creator.avatar_url,
        }
        if creator
        else None,
    }


async def create(
    request: Request, session: AsyncSession, user_id: int, payload: HeartMomentRequest
) -> int:
    started = perf_counter()
    operation = "create"
    couple_id = await _couple_id(request, session, user_id, operation, started)
    moment_type = payload.moment_type.strip()
    if not moment_type:
        await _fail(request, operation, started, 400, "心动时刻类型不能为空")
    item = HeartMoment(
        couple_id=couple_id,
        creator_id=user_id,
        moment_type=moment_type,
        content=payload.content,
        media_url=payload.media_url,
        is_deleted=0,
    )
    session.add(item)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return item.id


async def list_moments(
    request: Request, session: AsyncSession, user_id: int, page: int, page_size: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "list"
    page = page if page >= 1 else 1
    page_size = page_size if page_size >= 1 else 20
    couple_id = await _couple_id(request, session, user_id, operation, started)
    rows = await session.execute(
        select(HeartMoment)
        .where(HeartMoment.couple_id == couple_id, HeartMoment.is_deleted == 0)
        .order_by(HeartMoment.create_time.desc(), HeartMoment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = [await _payload(session, item) for item in rows.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def delete(request: Request, session: AsyncSession, user_id: int, moment_id: int) -> None:
    started = perf_counter()
    operation = "delete"
    couple_id = await _couple_id(request, session, user_id, operation, started)
    item = await session.scalar(
        select(HeartMoment)
        .where(HeartMoment.id == moment_id, HeartMoment.is_deleted == 0)
        .with_for_update()
    )
    if item is None:
        await _fail(request, operation, started, 9001, "心动时刻不存在")
    if item.couple_id != couple_id or item.creator_id != user_id:
        await _fail(request, operation, started, 3002, "无权操作此心动时刻")
    item.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def random_moment(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None] | None:
    started = perf_counter()
    operation = "random"
    couple_id = await _couple_id(request, session, user_id, operation, started)
    total = int(
        (
            await session.scalar(
                select(func.count(HeartMoment.id)).where(
                    HeartMoment.couple_id == couple_id, HeartMoment.is_deleted == 0
                )
            )
        )
        or 0
    )
    if total == 0:
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "empty", started)
        )
        return None
    item = await session.scalar(
        select(HeartMoment)
        .where(HeartMoment.couple_id == couple_id, HeartMoment.is_deleted == 0)
        .order_by(HeartMoment.id.asc())
        .offset(randbelow(total))
        .limit(1)
    )
    result = await _payload(session, item) if item else None
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "success" if result else "empty", started),
    )
    return result
