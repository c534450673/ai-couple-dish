"""恋爱日历 shadow 服务。

日历是对情侣业务数据的只读聚合，Spring 仍是 writer；FastAPI 只提供兼容查询。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from time import perf_counter
from typing import Never
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import (
    Anniversary,
    Couple,
    CoupleMenu,
    FoodNote,
    HeartMoment,
    TimeCapsule,
    User,
    Wish,
)

logger = structlog.get_logger()
BUSINESS_ZONE = ZoneInfo("Asia/Shanghai")

Event = dict[str, object | None]


def _today() -> date:
    return datetime.now(BUSINESS_ZONE).date()


def _fields(
    request: object, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    state = getattr(request, "state", None)
    return {
        "requestId": getattr(state, "request_id", "unknown"),
        "module": "love_calendar",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(
    request: object, operation: str, started: float, code: int, message: str
) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _couple_context(
    request: object, session: AsyncSession, user_id: int, operation: str, started: float
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


def _anniversary_date(item: Anniversary, year: int) -> date | None:
    """计算阳历重复纪念日；农历转换由后续迁移任务补齐。"""
    month = item.anniversary_date.month
    day = item.anniversary_date.day
    if item.is_lunar_date:
        return None
    if month == 2 and day == 29:
        day = 28 if (year % 4 != 0 or year % 100 == 0 and year % 400 != 0) else 29
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _event(
    *,
    item_id: int,
    event_type: str,
    type_name: str,
    title: str,
    description: str | None,
    icon: str,
    color: str,
    creator_id: int | None,
    create_time: datetime,
    extra_info: dict[str, object | None] | None = None,
) -> Event:
    return {
        "id": item_id,
        "eventType": event_type,
        "eventTypeName": type_name,
        "title": title,
        "description": description,
        "icon": icon,
        "color": color,
        "creatorId": creator_id,
        "creatorName": None,
        "createTime": create_time.isoformat(),
        "extraInfo": extra_info,
    }


async def _events(
    request: object,
    session: AsyncSession,
    couple_id: int,
    start_date: date,
    end_date: date,
) -> list[Event]:
    """聚合六类 Spring 业务事件。"""
    started = perf_counter()
    records: list[tuple[date, Event, int | None]] = []

    anniversary_items = (
        await session.scalars(
            select(Anniversary).where(
                Anniversary.couple_id == couple_id,
                Anniversary.is_deleted == 0,
            )
        )
    ).all()
    for anniversary in anniversary_items:
        if anniversary.is_lunar_date:
            await logger.awarning(
                "calendar_event_skipped",
                **_fields(request, "aggregate", "partial", started, "LUNAR_UNSUPPORTED"),
            )
            continue
        for year in range(start_date.year, end_date.year + 1):
            event_date = _anniversary_date(anniversary, year)
            if event_date is None or not start_date <= event_date <= end_date:
                continue
            records.append(
                (
                    event_date,
                    _event(
                        item_id=anniversary.id,
                        event_type="anniversary",
                        type_name="纪念日",
                        title=anniversary.name,
                        description="纪念日提醒",
                        icon="📅",
                        color="#FF6B6B",
                        creator_id=anniversary.creator_id,
                        create_time=datetime.combine(event_date, time(9, 0)),
                        extra_info={
                            "anniversaryType": anniversary.anniversary_type,
                            "isLunarDate": anniversary.is_lunar_date,
                        },
                    ),
                    anniversary.creator_id,
                )
            )

    capsule_items = (
        await session.scalars(
            select(TimeCapsule).where(
                TimeCapsule.couple_id == couple_id,
                TimeCapsule.is_deleted == 0,
                TimeCapsule.unlock_date >= start_date,
                TimeCapsule.unlock_date <= end_date,
            )
        )
    ).all()
    for capsule in capsule_items:
        event_date = capsule.unlock_date
        records.append(
            (
                event_date,
                _event(
                    item_id=capsule.id,
                    event_type="timeCapsule",
                    type_name="时光胶囊",
                    title=capsule.title or "时光胶囊解锁",
                    description="时光胶囊解锁日",
                    icon="📦",
                    color="#4ECDC4",
                    creator_id=capsule.creator_id,
                    create_time=datetime.combine(event_date, time.min),
                ),
                capsule.creator_id,
            )
        )

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
    moment_items = (
        await session.scalars(
            select(HeartMoment).where(
                HeartMoment.couple_id == couple_id,
                HeartMoment.is_deleted == 0,
                HeartMoment.create_time >= start_dt,
                HeartMoment.create_time < end_dt,
            )
        )
    ).all()
    for moment in moment_items:
        event_date = moment.create_time.date()
        records.append(
            (
                event_date,
                _event(
                    item_id=moment.id,
                    event_type="heartMoment",
                    type_name="心动时刻",
                    title="心动时刻",
                    description=moment.content,
                    icon="💕",
                    color="#FF69B4",
                    creator_id=moment.creator_id,
                    create_time=moment.create_time,
                ),
                moment.creator_id,
            )
        )

    menu_items = (
        await session.scalars(
            select(CoupleMenu).where(
                CoupleMenu.couple_id == couple_id,
                CoupleMenu.is_deleted == 0,
                CoupleMenu.eaten_date.is_not(None),
                CoupleMenu.eaten_date >= start_date,
                CoupleMenu.eaten_date <= end_date,
            )
        )
    ).all()
    for menu in menu_items:
        if menu.eaten_date is None:
            continue
        event_date = menu.eaten_date
        records.append(
            (
                event_date,
                _event(
                    item_id=menu.id,
                    event_type="menu",
                    type_name="约会记录",
                    title=menu.restaurant_name,
                    description=menu.dish_name or "美食约会",
                    icon="🍽️",
                    color="#45B7D1",
                    creator_id=menu.creator_id,
                    create_time=datetime.combine(event_date, time(12, 0)),
                    extra_info={"location": menu.location, "rating": menu.rating},
                ),
                menu.creator_id,
            )
        )

    note_items = (
        await session.scalars(
            select(FoodNote).where(
                FoodNote.couple_id == couple_id,
                FoodNote.is_deleted == 0,
                FoodNote.create_time >= start_dt,
                FoodNote.create_time < end_dt,
            )
        )
    ).all()
    for note in note_items:
        description = note.content[:50] + "..." if len(note.content) > 50 else note.content
        event_date = note.create_time.date()
        records.append(
            (
                event_date,
                _event(
                    item_id=note.id,
                    event_type="note",
                    type_name="美食笔记",
                    title=note.title,
                    description=description,
                    icon="📝",
                    color="#96CEB4",
                    creator_id=note.author_id,
                    create_time=note.create_time,
                ),
                note.author_id,
            )
        )

    wish_items = (
        await session.scalars(
            select(Wish).where(
                Wish.couple_id == couple_id,
                Wish.is_deleted == 0,
                Wish.status == 1,
                Wish.achieved_date.is_not(None),
                Wish.achieved_date >= start_date,
                Wish.achieved_date <= end_date,
            )
        )
    ).all()
    for wish in wish_items:
        if wish.achieved_date is None:
            continue
        event_date = wish.achieved_date
        records.append(
            (
                event_date,
                _event(
                    item_id=wish.id,
                    event_type="wish",
                    type_name="心愿实现",
                    title=wish.title,
                    description="心愿达成！",
                    icon="🎉",
                    color="#FFD93D",
                    creator_id=wish.creator_id,
                    create_time=datetime.combine(event_date, time.min),
                ),
                wish.creator_id,
            )
        )

    creator_ids = {creator_id for _, _, creator_id in records if creator_id is not None}
    creators: dict[int, User] = {}
    if creator_ids:
        users = (
            await session.scalars(
                select(User).where(User.id.in_(creator_ids), User.is_deleted == 0)
            )
        ).all()
        creators = {item.id: item for item in users}
    for _, event, creator_id in records:
        creator = creators.get(creator_id) if creator_id is not None else None
        event["creatorName"] = creator.nick_name if creator else None
    records.sort(key=lambda item: (item[0], str(item[1]["createTime"]), str(item[1]["id"])))
    return [event for _, event, _ in records]


async def events_by_range(
    request: object,
    session: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[Event]:
    started = perf_counter()
    operation = "events_range"
    if start_date > end_date:
        await _fail(request, operation, started, 400, "开始日期不能晚于结束日期")
    _, couple = await _couple_context(request, session, user_id, operation, started)
    result = await _events(request, session, couple.id, start_date, end_date)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def events_by_date(
    request: object, session: AsyncSession, user_id: int, event_date: date
) -> list[Event]:
    return await events_by_range(request, session, user_id, event_date, event_date)


async def today(request: object, session: AsyncSession, user_id: int) -> list[Event]:
    event_date = _today()
    return await events_by_date(request, session, user_id, event_date)


async def upcoming(
    request: object, session: AsyncSession, user_id: int, limit: int
) -> list[Event]:
    started = perf_counter()
    operation = "upcoming"
    if limit <= 0:
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "empty", started)
        )
        return []
    event_date = _today()
    _, couple = await _couple_context(request, session, user_id, operation, started)
    events = await _events(
        request, session, couple.id, event_date, event_date + timedelta(days=30)
    )
    result = events[: min(limit, 100)]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


def _stats(events: list[Event]) -> dict[str, int]:
    event_types = [str(item["eventType"]) for item in events]
    return {
        "anniversaryCount": event_types.count("anniversary"),
        "timeCapsuleCount": event_types.count("timeCapsule"),
        "heartMomentCount": event_types.count("heartMoment"),
        "dateCount": event_types.count("menu") + event_types.count("note"),
        "totalEvents": len(events),
    }


async def month(
    request: object,
    session: AsyncSession,
    user_id: int,
    year: int | None,
    month_value: int | None,
) -> dict[str, object]:
    started = perf_counter()
    operation = "month"
    current = _today()
    target_year = year or current.year
    target_month = month_value or current.month
    try:
        first = date(target_year, target_month, 1)
    except ValueError:
        await _fail(request, operation, started, 400, "年份或月份无效")
    next_month = first.replace(day=28) + timedelta(days=4)
    last = next_month - timedelta(days=next_month.day)
    user, couple = await _couple_context(request, session, user_id, operation, started)
    events = await _events(request, session, couple.id, first, last)
    by_date: dict[str, list[Event]] = {}
    for event in events:
        by_date.setdefault(str(event["createTime"])[:10], []).append(event)
    love_start = couple.start_date or (
        user.love_start_date.date() if user.love_start_date else None
    )
    days: list[dict[str, object]] = []
    for offset in range(last.day):
        item_date = first + timedelta(days=offset)
        day_events = by_date.get(item_date.isoformat(), [])
        days.append(
            {
                "date": item_date.isoformat(),
                "dayOfWeek": item_date.isoweekday(),
                "isToday": item_date == current,
                "isLoveAnniversary": bool(love_start and love_start.day == item_date.day),
                "events": day_events,
                "eventCount": len(day_events),
            }
        )
    result = {
        "year": target_year,
        "month": target_month,
        "days": days,
        "monthStats": _stats(events),
    }
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def year_overview(
    request: object, session: AsyncSession, user_id: int, year: int | None
) -> dict[str, object]:
    started = perf_counter()
    operation = "year_overview"
    target_year = year or _today().year
    try:
        first = date(target_year, 1, 1)
        last = date(target_year, 12, 31)
    except ValueError:
        await _fail(request, operation, started, 400, "年份无效")
    _, couple = await _couple_context(request, session, user_id, operation, started)
    events = await _events(request, session, couple.id, first, last)
    result: dict[str, object] = {
        "year": target_year,
        "month": None,
        "days": None,
        "monthStats": _stats(events),
    }
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result
