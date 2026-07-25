from datetime import date
from time import perf_counter

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Anniversary, User
from app.schemas.business import (
    AnniversaryCreateRequest,
    AnniversaryUpdateRequest,
    ReminderConfigRequest,
)

logger = structlog.get_logger()


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "anniversary",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


async def _couple_id(session: AsyncSession, user_id: int) -> int:
    user = await _user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    return user.couple_id


def _next_date(value: date, today: date | None = None) -> date:
    current = today or date.today()
    try:
        candidate = value.replace(year=current.year)
    except ValueError:
        candidate = date(current.year, 2, 28)
    if candidate < current:
        try:
            candidate = value.replace(year=current.year + 1)
        except ValueError:
            candidate = date(current.year + 1, 2, 28)
    return candidate


def _type_name(value: int | None) -> str:
    return {1: "相识", 2: "恋爱", 3: "表白", 4: "其他"}.get(value or 0, "其他")


def _payload(item: Anniversary, today: date | None = None) -> dict[str, object | None]:
    current = today or date.today()
    next_date = _next_date(item.anniversary_date, current)
    return {
        "id": item.id,
        "name": item.name,
        "anniversaryDate": item.anniversary_date.isoformat(),
        "anniversaryType": item.anniversary_type,
        "typeName": _type_name(item.anniversary_type),
        "remindDaysBefore": item.remind_days_before,
        "autoRemind": item.auto_remind,
        "isLunarDate": bool(item.is_lunar_date),
        "lunarMonth": item.lunar_month,
        "lunarDay": item.lunar_day,
        "lunarDateName": None,
        "daysUntil": (next_date - current).days,
        "isPast": False,
        "remindChannels": item.remind_channels,
        "remindHour": item.remind_hour,
        "wechatRemindEnabled": item.wechat_remind_enabled,
        "smsRemindEnabled": item.sms_remind_enabled,
        "appRemindEnabled": item.app_remind_enabled,
    }


async def _item_for_couple(session: AsyncSession, user_id: int, anniversary_id: int) -> Anniversary:
    couple_id = await _couple_id(session, user_id)
    item = await session.scalar(
        select(Anniversary).where(Anniversary.id == anniversary_id, Anniversary.is_deleted == 0)
    )
    if item is None:
        raise BusinessError(5001, "纪念日不存在")
    if item.couple_id != couple_id:
        raise BusinessError(3002, "无权操作此纪念日")
    return item


async def list_anniversaries(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    result = await session.execute(
        select(Anniversary)
        .where(Anniversary.couple_id == couple_id, Anniversary.is_deleted == 0)
        .order_by(Anniversary.anniversary_date.asc(), Anniversary.id.asc())
    )
    items = [_payload(item) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "list", "success", started)
    )
    return items


async def upcoming(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    result = await session.execute(
        select(Anniversary).where(Anniversary.couple_id == couple_id, Anniversary.is_deleted == 0)
    )
    items = sorted(
        result.scalars().all(), key=lambda item: (_next_date(item.anniversary_date), item.id)
    )
    payload = [_payload(item) for item in items]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "upcoming", "success", started)
    )
    return payload


async def next_anniversary(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None] | None:
    started = perf_counter()
    user = await _user(session, user_id)
    if user.couple_id is None:
        await logger.ainfo(
            "business_operation_completed", **_log_fields(request, "next", "empty", started)
        )
        return None
    result = await session.execute(
        select(Anniversary).where(
            Anniversary.couple_id == user.couple_id, Anniversary.is_deleted == 0
        )
    )
    item = min(
        result.scalars().all(),
        key=lambda value: (_next_date(value.anniversary_date), value.id),
        default=None,
    )
    payload = _payload(item) if item else None
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "next", "success" if payload else "empty", started),
    )
    return payload


async def add(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: AnniversaryCreateRequest,
) -> int:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    if payload.anniversary_type == 2:
        existing = await session.scalar(
            select(Anniversary).where(
                Anniversary.couple_id == couple_id,
                Anniversary.anniversary_type == 2,
                Anniversary.is_deleted == 0,
            )
        )
        if existing is not None:
            raise BusinessError(5002, "该日期的纪念日已存在")
    item = Anniversary(
        couple_id=couple_id,
        creator_id=user_id,
        name=payload.name,
        anniversary_date=payload.anniversary_date,
        is_lunar_date=payload.is_lunar_date,
        lunar_month=payload.lunar_month,
        lunar_day=payload.lunar_day,
        anniversary_type=payload.anniversary_type,
        remind_days_before=payload.remind_days_before,
        auto_remind=payload.auto_remind,
        is_deleted=0,
    )
    session.add(item)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "add", "success", started)
    )
    return item.id


async def update(
    request: Request,
    session: AsyncSession,
    user_id: int,
    anniversary_id: int,
    payload: AnniversaryUpdateRequest,
) -> None:
    started = perf_counter()
    item = await _item_for_couple(session, user_id, anniversary_id)
    if item.creator_id != user_id:
        raise BusinessError(3002, "无权操作此纪念日")
    if item.anniversary_type == 2 and payload.anniversary_type not in (None, 2):
        raise BusinessError(5003, "恋爱日类型不能修改")
    if payload.anniversary_type == 2 and item.anniversary_type != 2:
        existing = await session.scalar(
            select(Anniversary).where(
                Anniversary.couple_id == item.couple_id,
                Anniversary.anniversary_type == 2,
                Anniversary.is_deleted == 0,
                Anniversary.id != item.id,
            )
        )
        if existing is not None:
            raise BusinessError(5002, "该日期的纪念日已存在")
    if payload.name is not None:
        item.name = payload.name
    if payload.anniversary_date is not None:
        item.anniversary_date = payload.anniversary_date
    if payload.is_lunar_date is not None:
        item.is_lunar_date = payload.is_lunar_date
    if payload.lunar_month is not None:
        item.lunar_month = payload.lunar_month
    if payload.lunar_day is not None:
        item.lunar_day = payload.lunar_day
    if payload.anniversary_type is not None:
        item.anniversary_type = payload.anniversary_type
    if payload.remind_days_before is not None:
        item.remind_days_before = payload.remind_days_before
    if payload.auto_remind is not None:
        item.auto_remind = payload.auto_remind
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "update", "success", started)
    )


async def delete_anniversary(
    request: Request, session: AsyncSession, user_id: int, anniversary_id: int
) -> None:
    started = perf_counter()
    item = await _item_for_couple(session, user_id, anniversary_id)
    if item.creator_id != user_id:
        raise BusinessError(3002, "无权操作此纪念日")
    if item.anniversary_type == 2:
        raise BusinessError(5003, "恋爱日不能删除")
    item.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "delete", "success", started)
    )


async def today(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None] | None:
    started = perf_counter()
    user = await _user(session, user_id)
    if user.couple_id is None:
        await logger.ainfo(
            "business_operation_completed", **_log_fields(request, "today", "empty", started)
        )
        return None
    couple_id = user.couple_id
    current = date.today()
    result = await session.execute(
        select(Anniversary).where(Anniversary.couple_id == couple_id, Anniversary.is_deleted == 0)
    )
    item = next(
        (
            value
            for value in result.scalars().all()
            if value.anniversary_date.month == current.month
            and value.anniversary_date.day == current.day
        ),
        None,
    )
    payload = _payload(item, current) if item else None
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "today", "success" if payload else "empty", started),
    )
    return payload


async def update_reminder_config(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: ReminderConfigRequest,
) -> None:
    started = perf_counter()
    item = await _item_for_couple(session, user_id, payload.anniversary_id)
    if payload.auto_remind is not None:
        item.auto_remind = payload.auto_remind
    if payload.remind_days_before is not None:
        item.remind_days_before = payload.remind_days_before
    if payload.remind_channels is not None:
        item.remind_channels = payload.remind_channels
    if payload.remind_hour is not None:
        item.remind_hour = payload.remind_hour
    if payload.wechat_remind_enabled is not None:
        item.wechat_remind_enabled = payload.wechat_remind_enabled
    if payload.sms_remind_enabled is not None:
        item.sms_remind_enabled = payload.sms_remind_enabled
    if payload.app_remind_enabled is not None:
        item.app_remind_enabled = payload.app_remind_enabled
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "reminder_config", "success", started),
    )
