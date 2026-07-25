"""时光胶囊 shadow 服务。

该模块只实现与现有 Spring API 兼容的 FastAPI shadow 路由，不改变切流配置。
"""

import json
from datetime import UTC, date, datetime, timedelta
from time import perf_counter
from typing import Never
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, Notification, TimeCapsule, User
from app.schemas.business import TimeCapsuleRequest

logger = structlog.get_logger()
BUSINESS_ZONE = ZoneInfo("Asia/Shanghai")
CAPSULE_TYPES = {"text", "voice", "video", "photo"}


def _today() -> date:
    return datetime.now(BUSINESS_ZONE).date()


def _fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "time_capsule",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _couple_context(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> tuple[User, Couple]:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    couple = await session.scalar(
        select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    )
    if couple is None or user.id not in {couple.user1_id, couple.user2_id}:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user, couple


async def _item_for_couple(
    request: Request,
    session: AsyncSession,
    couple_id: int,
    capsule_id: int,
    operation: str,
    started: float,
    *,
    lock: bool = False,
) -> TimeCapsule:
    statement = select(TimeCapsule).where(
        TimeCapsule.id == capsule_id,
        TimeCapsule.is_deleted == 0,
    )
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        await _fail(request, operation, started, 9001, "时光胶囊不存在")
    if item.couple_id != couple_id:
        await _fail(request, operation, started, 9999, "无权查看此时光胶囊")
    return item


def _media(item: TimeCapsule) -> list[str] | None:
    if not item.media_urls:
        return None
    try:
        values = json.loads(item.media_urls)
    except (TypeError, json.JSONDecodeError):
        return None
    return (
        values
        if isinstance(values, list) and all(isinstance(value, str) for value in values)
        else None
    )


async def _payload(
    session: AsyncSession, item: TimeCapsule, *, reveal: bool
) -> dict[str, object | None]:
    creator = await session.scalar(
        select(User).where(User.id == item.creator_id, User.is_deleted == 0)
    )
    today = _today()
    unlocked = item.status == 1 or item.unlock_date <= today
    can_unlock = item.status == 0 and item.unlock_date <= today
    days_until = max(0, (item.unlock_date - today).days) if item.status == 0 else 0
    should_reveal = reveal and (item.status == 1 or unlocked)
    return {
        "id": item.id,
        "capsuleType": item.capsule_type,
        "title": item.title,
        "content": item.content if should_reveal else "🔒 胶囊尚未解锁",
        "mediaUrls": _media(item) if should_reveal else None,
        "unlockDate": item.unlock_date.isoformat(),
        "status": item.status,
        "statusName": "已解锁" if item.status == 1 else "待解锁",
        "createTime": item.create_time.isoformat() if item.create_time else None,
        "unlockTime": item.unlock_time.isoformat() if item.unlock_time else None,
        "canUnlock": can_unlock,
        "daysUntilUnlock": days_until,
        "creator": {
            "id": creator.id,
            "nickName": creator.nick_name,
            "avatarUrl": creator.avatar_url,
        }
        if creator
        else None,
    }


async def create(
    request: Request, session: AsyncSession, user_id: int, payload: TimeCapsuleRequest
) -> int:
    started = perf_counter()
    operation = "create"
    user, couple = await _couple_context(request, session, user_id, operation, started)
    capsule_type = payload.capsule_type.strip().lower()
    title = payload.title.strip()
    if capsule_type not in CAPSULE_TYPES or not title:
        await _fail(request, operation, started, 400, "胶囊参数无效")
    if capsule_type == "text" and not (payload.content and payload.content.strip()):
        await _fail(request, operation, started, 400, "文本胶囊内容不能为空")
    if payload.unlock_date < _today() + timedelta(days=1):
        await _fail(request, operation, started, 400, "解锁日期必须至少是明天")
    media_urls = payload.media_urls or None
    item = TimeCapsule(
        couple_id=couple.id,
        creator_id=user.id,
        capsule_type=capsule_type,
        title=title,
        content=payload.content,
        media_urls=json.dumps(media_urls, ensure_ascii=False) if media_urls else None,
        unlock_date=payload.unlock_date,
        status=0,
        is_deleted=0,
    )
    session.add(item)
    await session.flush()
    partner_id = couple.user2_id if couple.user1_id == user.id else couple.user1_id
    if partner_id:
        session.add(
            Notification(
                user_id=partner_id,
                type=1,
                title="新的时光胶囊",
                content="你的伴侣给你留下了一个时光胶囊",
                related_id=item.id,
                related_type="time_capsule",
                sender_id=user.id,
                is_read=0,
            )
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return item.id


async def list_capsules(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "list"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    result = await session.execute(
        select(TimeCapsule)
        .where(TimeCapsule.couple_id == couple.id, TimeCapsule.is_deleted == 0)
        .order_by(TimeCapsule.unlock_date.asc(), TimeCapsule.id.asc())
    )
    items = [await _payload(session, item, reveal=True) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return items


async def detail(
    request: Request, session: AsyncSession, user_id: int, capsule_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    item = await _item_for_couple(request, session, couple.id, capsule_id, operation, started)
    result = await _payload(session, item, reveal=True)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def unlock(
    request: Request, session: AsyncSession, user_id: int, capsule_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "unlock"
    user, couple = await _couple_context(request, session, user_id, operation, started)
    item = await _item_for_couple(
        request, session, couple.id, capsule_id, operation, started, lock=True
    )
    if item.status == 1:
        await _fail(request, operation, started, 9999, "时光胶囊已解锁")
    if item.unlock_date > _today():
        await _fail(request, operation, started, 400, "尚未到达解锁日期")
    item.status = 1
    item.unlock_time = datetime.now(UTC).replace(tzinfo=None)
    if item.creator_id != user.id:
        session.add(
            Notification(
                user_id=item.creator_id,
                type=2,
                title="时光胶囊已解锁",
                content="你的时光胶囊已被伴侣解锁",
                related_id=item.id,
                related_type="time_capsule",
                sender_id=user.id,
                is_read=0,
            )
        )
    await session.commit()
    result = await _payload(session, item, reveal=True)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def delete(request: Request, session: AsyncSession, user_id: int, capsule_id: int) -> None:
    started = perf_counter()
    operation = "delete"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    item = await _item_for_couple(
        request, session, couple.id, capsule_id, operation, started, lock=True
    )
    if item.creator_id != user_id:
        await _fail(request, operation, started, 3002, "无权操作此时光胶囊")
    item.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def pending(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "pending"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    result = await session.execute(
        select(TimeCapsule)
        .where(
            TimeCapsule.couple_id == couple.id,
            TimeCapsule.status == 0,
            TimeCapsule.is_deleted == 0,
            TimeCapsule.unlock_date <= _today(),
        )
        .order_by(TimeCapsule.unlock_date.asc(), TimeCapsule.id.asc())
    )
    items = [await _payload(session, item, reveal=True) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return items
