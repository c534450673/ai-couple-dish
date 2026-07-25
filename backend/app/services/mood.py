from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import ColumnElement, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, MoodRecord, Notification, User
from app.schemas.business import MoodRecordRequest

logger = structlog.get_logger()

MOOD_TYPES: tuple[dict[str, str], ...] = (
    {
        "type": "happy",
        "name": "开心",
        "icon": "😊",
        "color": "#FFD700",
        "description": "今天心情很好",
    },
    {
        "type": "love",
        "name": "爱你",
        "icon": "❤️",
        "color": "#FF69B4",
        "description": "想对TA说爱你",
    },
    {"type": "miss_you", "name": "想你", "icon": "🥺", "color": "#87CEEB", "description": "好想TA"},
    {
        "type": "tired",
        "name": "疲惫",
        "icon": "😴",
        "color": "#9370DB",
        "description": "今天有点累",
    },
    {
        "type": "upset",
        "name": "烦躁",
        "icon": "😤",
        "color": "#FF6347",
        "description": "心情不太好",
    },
    {"type": "sad", "name": "难过", "icon": "😢", "color": "#6495ED", "description": "有点伤心"},
    {"type": "angry", "name": "生气", "icon": "😠", "color": "#DC143C", "description": "很生气"},
    {
        "type": "anxious",
        "name": "焦虑",
        "icon": "😰",
        "color": "#808080",
        "description": "有点焦虑",
    },
)
MOOD_BY_TYPE = {item["type"]: item for item in MOOD_TYPES}


def _log_fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "mood",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(
    request: Request,
    operation: str,
    started: float,
    code: int,
    message: str,
) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_log_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _user(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


async def _couple_user(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
) -> User:
    user = await _user(request, session, user_id, operation, started)
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user


def _mood_info(mood_type: str) -> dict[str, str] | None:
    return MOOD_BY_TYPE.get(mood_type)


def _payload(record: MoodRecord, sender: User | None) -> dict[str, object | None]:
    info = _mood_info(record.mood_type)
    return {
        "id": record.id,
        "moodType": record.mood_type,
        "moodTypeName": info["name"] if info else record.mood_type,
        "description": record.description,
        "moodIcon": record.mood_icon,
        "moodColor": record.mood_color,
        "recordDate": record.record_date.isoformat(),
        "isRead": bool(record.is_read),
        "readTime": record.read_time.isoformat() if record.read_time else None,
        "createTime": record.create_time.isoformat() if record.create_time else None,
        "sender": (
            {
                "id": sender.id,
                "nickName": sender.nick_name,
                "avatarUrl": sender.avatar_url,
            }
            if sender
            else None
        ),
    }


async def _payloads(
    session: AsyncSession, records: list[MoodRecord]
) -> list[dict[str, object | None]]:
    if not records:
        return []
    sender_ids = {record.user_id for record in records}
    result = await session.execute(select(User).where(User.id.in_(sender_ids)))
    senders = {sender.id: sender for sender in result.scalars().all()}
    return [_payload(record, senders.get(record.user_id)) for record in records]


async def send(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: MoodRecordRequest,
) -> int:
    started = perf_counter()
    operation = "send"
    user = await _couple_user(request, session, user_id, operation, started)
    mood_type = payload.mood_type.strip()
    info = _mood_info(mood_type)
    if info is None:
        await _fail(request, operation, started, 400, "无效的心情类型")

    record = MoodRecord(
        user_id=user_id,
        couple_id=user.couple_id,
        mood_type=mood_type,
        description=payload.description,
        mood_icon=info["icon"],
        mood_color=info["color"],
        record_date=date.today(),
        is_read=0,
        is_deleted=0,
    )
    session.add(record)
    await session.flush()

    couple = await session.scalar(select(Couple).where(Couple.id == user.couple_id))
    partner_id = None
    if couple is not None:
        partner_id = couple.user2_id if couple.user1_id == user_id else couple.user1_id
    if partner_id is not None and partner_id != user_id:
        session.add(
            Notification(
                user_id=partner_id,
                type=2,
                title="💌 心情投递",
                content=f"TA给你投递了一份心情: {info['name']}",
                related_id=record.id,
                related_type="mood_record",
                sender_id=user_id,
                is_read=0,
            )
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return record.id


async def _list(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    where_clause: ColumnElement[bool],
    started: float,
    limit: int | None = None,
) -> list[dict[str, object | None]]:
    user = await _couple_user(request, session, user_id, operation, started)
    statement = (
        select(MoodRecord)
        .where(MoodRecord.couple_id == user.couple_id, MoodRecord.is_deleted == 0, where_clause)
        .order_by(
            MoodRecord.record_date.desc(), MoodRecord.create_time.desc(), MoodRecord.id.desc()
        )
    )
    if limit is not None:
        safe_limit = limit if 1 <= limit <= 100 else 30
        statement = statement.limit(safe_limit)
    result = await session.execute(statement)
    items = await _payloads(session, list(result.scalars().all()))
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return items


async def today(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    today_date = date.today()
    return await _list(
        request,
        session,
        user_id,
        "today",
        MoodRecord.record_date == today_date,
        started,
    )


async def history(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    return await _list(request, session, user_id, "history", true(), started, limit)


async def _record_for_couple(
    request: Request,
    session: AsyncSession,
    user_id: int,
    mood_id: int,
    operation: str,
    started: float,
) -> tuple[MoodRecord, User]:
    user = await _couple_user(request, session, user_id, operation, started)
    record = await session.scalar(
        select(MoodRecord).where(MoodRecord.id == mood_id, MoodRecord.is_deleted == 0)
    )
    if record is None:
        await _fail(request, operation, started, 9001, "心情记录不存在")
    if record.couple_id != user.couple_id:
        await _fail(request, operation, started, 3002, "无权操作此心情记录")
    return record, user


async def detail(
    request: Request, session: AsyncSession, user_id: int, mood_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    record, _ = await _record_for_couple(request, session, user_id, mood_id, "detail", started)
    sender = await session.scalar(select(User).where(User.id == record.user_id))
    result = _payload(record, sender)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "detail", "success", started)
    )
    return result


async def mark_read(request: Request, session: AsyncSession, user_id: int, mood_id: int) -> None:
    started = perf_counter()
    record, _ = await _record_for_couple(request, session, user_id, mood_id, "read", started)
    if record.is_read == 0:
        record.is_read = 1
        record.read_time = datetime.now()
        await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "read", "success", started)
    )


async def stats(request: Request, session: AsyncSession, user_id: int) -> dict[str, object]:
    started = perf_counter()
    user = await _couple_user(request, session, user_id, "stats", started)
    today_date = date.today()
    week_start = today_date - timedelta(days=today_date.weekday())
    month_start = today_date.replace(day=1)
    base = [MoodRecord.couple_id == user.couple_id, MoodRecord.is_deleted == 0]
    today_count = int(
        await session.scalar(
            select(func.count(MoodRecord.id)).where(*base, MoodRecord.record_date == today_date)
        )
        or 0
    )
    week_count = int(
        await session.scalar(
            select(func.count(MoodRecord.id)).where(
                *base,
                MoodRecord.record_date >= week_start,
                MoodRecord.record_date <= today_date,
            )
        )
        or 0
    )
    month_count = int(
        await session.scalar(
            select(func.count(MoodRecord.id)).where(
                *base,
                MoodRecord.record_date >= month_start,
                MoodRecord.record_date <= today_date,
            )
        )
        or 0
    )
    distribution_result = await session.execute(
        select(MoodRecord.mood_type, func.count(MoodRecord.id))
        .where(
            *base,
            MoodRecord.record_date >= month_start,
            MoodRecord.record_date <= today_date,
        )
        .group_by(MoodRecord.mood_type)
    )
    distribution_rows = list(distribution_result.all())
    counts = {str(mood_type): int(count) for mood_type, count in distribution_rows}
    total = sum(counts.values())
    distribution = []
    for info in MOOD_TYPES:
        mood_type = info["type"]
        count = counts.get(mood_type, 0)
        if count == 0:
            continue
        distribution.append(
            {
                "moodType": mood_type,
                "moodTypeName": info["name"],
                "count": count,
                "percentage": (count / total * 100) if total else 0,
            }
        )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "stats", "success", started)
    )
    return {
        "monthCount": month_count,
        "weekCount": week_count,
        "todayCount": today_count,
        "distribution": distribution,
    }


async def types(request: Request) -> list[dict[str, str]]:
    started = perf_counter()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "types", "success", started)
    )
    return [dict(item) for item in MOOD_TYPES]


async def unread_count(request: Request, session: AsyncSession, user_id: int) -> int:
    started = perf_counter()
    user = await _user(request, session, user_id, "unread_count", started)
    if user.couple_id is None:
        await logger.ainfo(
            "business_operation_completed", **_log_fields(request, "unread_count", "empty", started)
        )
        return 0
    count = await session.scalar(
        select(func.count(MoodRecord.id)).where(
            MoodRecord.couple_id == user.couple_id,
            MoodRecord.user_id != user_id,
            MoodRecord.is_read == 0,
            MoodRecord.is_deleted == 0,
        )
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "unread_count", "success", started)
    )
    return int(count or 0)
