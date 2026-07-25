import asyncio
import secrets
from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Never
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import DailyGreeting, GreetingStreak, Notification, User
from app.schemas.business import DailyGreetingRequest

logger = structlog.get_logger()
BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
LOCK_TTL_SECONDS = 10
LOCK_RETRY_COUNT = 40
LOCK_RETRY_SECONDS = 0.025
RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "daily_greeting",
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
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


def _today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()


def _couple_id(user: User) -> int:
    if user.couple_id is None:
        raise RuntimeError("validated couple user is missing couple_id")
    return user.couple_id


async def _couple_user(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user


async def _acquire_send_lock(
    request: Request,
    couple_id: int,
    greeting_type: int,
    operation: str,
    started: float,
) -> tuple[str, str]:
    lock_key = f"daily_greeting:send:{couple_id}:{greeting_type}"
    lock_value = secrets.token_urlsafe(24)
    for attempt in range(LOCK_RETRY_COUNT):
        try:
            acquired = await request.app.state.redis.raw.set(
                lock_key,
                lock_value,
                ex=LOCK_TTL_SECONDS,
                nx=True,
            )
        except Exception:
            await logger.aerror(
                "dependency_operation_failed",
                **_fields(request, "acquire_send_lock", "error", started, "REDIS_LOCK_FAILED"),
            )
            await _fail(request, operation, started, 9001, "问候发送繁忙，请稍后重试")
        if acquired:
            return lock_key, lock_value
        if attempt < LOCK_RETRY_COUNT - 1:
            await asyncio.sleep(LOCK_RETRY_SECONDS)
    await _fail(request, operation, started, 9001, "问候发送繁忙，请稍后重试")


async def _release_send_lock(
    request: Request,
    lock_key: str,
    lock_value: str,
    started: float,
) -> None:
    try:
        await request.app.state.redis.raw.eval(RELEASE_LOCK_SCRIPT, 1, lock_key, lock_value)
    except Exception:
        await logger.aerror(
            "dependency_operation_failed",
            **_fields(
                request,
                "release_send_lock",
                "error",
                started,
                "REDIS_LOCK_RELEASE_FAILED",
            ),
        )


def _type_name(greeting_type: int) -> str:
    return "早安" if greeting_type == 1 else "晚安"


def _empty_payload(greeting_type: int, greeting_date: date) -> dict[str, object | None]:
    return {
        "id": None,
        "greetingType": greeting_type,
        "greetingTypeName": _type_name(greeting_type),
        "content": None,
        "voiceUrl": None,
        "voiceDuration": None,
        "greetingDate": greeting_date.isoformat(),
        "createTime": None,
        "sender": None,
        "streakDays": 0,
        "maxStreakDays": 0,
        "hasCheckedToday": False,
        "bothCheckStatus": None,
    }


def _payload(record: DailyGreeting, sender: User | None) -> dict[str, object | None]:
    payload = _empty_payload(record.greeting_type, record.greeting_date)
    payload.update(
        {
            "id": record.id,
            "content": record.content,
            "voiceUrl": record.voice_url,
            "voiceDuration": record.voice_duration,
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
            "hasCheckedToday": record.greeting_date == _today(),
        }
    )
    return payload


async def _payloads(
    session: AsyncSession,
    records: list[DailyGreeting],
) -> list[dict[str, object | None]]:
    if not records:
        return []
    users = await session.execute(
        select(User).where(User.id.in_({item.user_id for item in records}))
    )
    user_map = {user.id: user for user in users.scalars().all()}
    return [_payload(item, user_map.get(item.user_id)) for item in records]


def _streak_payload(streak_type: int, item: GreetingStreak | None) -> dict[str, object]:
    return {
        "streakType": streak_type,
        "streakTypeName": _type_name(streak_type),
        "streakDays": item.streak_days if item else 0,
        "maxStreakDays": item.max_streak_days if item else 0,
        "hasCheckedToday": bool(item and item.last_date == _today()),
    }


async def _update_streak(
    session: AsyncSession,
    couple_id: int,
    greeting_type: int,
    current_date: date,
) -> None:
    item = await session.scalar(
        select(GreetingStreak).where(
            GreetingStreak.couple_id == couple_id,
            GreetingStreak.streak_type == greeting_type,
        )
    )
    if item is None:
        session.add(
            GreetingStreak(
                couple_id=couple_id,
                streak_type=greeting_type,
                streak_days=1,
                max_streak_days=1,
                last_date=current_date,
            )
        )
        return
    if item.last_date == current_date:
        return
    item.streak_days = (
        item.streak_days + 1 if item.last_date == current_date - timedelta(days=1) else 1
    )
    item.max_streak_days = max(item.max_streak_days, item.streak_days)
    item.last_date = current_date
    item.update_time = datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)


async def send(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: DailyGreetingRequest,
) -> int:
    started = perf_counter()
    operation = "send"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    current_date = _today()
    lock_key, lock_value = await _acquire_send_lock(
        request, couple_id, payload.greeting_type, operation, started
    )
    try:
        # The user lookup starts a REPEATABLE READ transaction before lock acquisition.
        # Reset that snapshot so a waiter can observe the preceding sender's commit.
        await session.rollback()
        user = await _couple_user(request, session, user_id, operation, started)
        couple_id = _couple_id(user)
        existing = await session.scalar(
            select(DailyGreeting.id).where(
                DailyGreeting.user_id == user_id,
                DailyGreeting.greeting_type == payload.greeting_type,
                DailyGreeting.greeting_date == current_date,
                DailyGreeting.is_deleted == 0,
            )
        )
        if existing is not None:
            await _fail(request, operation, started, 8602, "今日已发送过该问候")

        record = DailyGreeting(
            couple_id=couple_id,
            user_id=user_id,
            greeting_type=payload.greeting_type,
            content=payload.content,
            voice_url=payload.voice_url,
            voice_duration=payload.voice_duration,
            greeting_date=current_date,
            is_deleted=0,
        )
        session.add(record)
        await session.flush()
        await _update_streak(session, couple_id, payload.greeting_type, current_date)

        partner = await session.scalar(
            select(User).where(
                User.couple_id == couple_id,
                User.id != user_id,
                User.is_deleted == 0,
            )
        )
        if partner is not None:
            greeting_name = _type_name(payload.greeting_type)
            session.add(
                Notification(
                    user_id=partner.id,
                    type=1,
                    title=f"{greeting_name}心动打卡",
                    content=f"TA给你发来了{greeting_name}问候，快去看看吧~",
                    related_id=record.id,
                    related_type="daily_greeting",
                    sender_id=user_id,
                    is_read=0,
                )
            )
        await session.commit()
        await logger.ainfo(
            "business_operation_completed",
            **_fields(request, operation, "success", started),
        )
        return record.id
    finally:
        await _release_send_lock(request, lock_key, lock_value, started)


async def today_status(
    request: Request,
    session: AsyncSession,
    user_id: int,
    greeting_type: int,
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "today_status"
    user = await _couple_user(request, session, user_id, operation, started)
    current_date = _today()
    record = await session.scalar(
        select(DailyGreeting).where(
            DailyGreeting.user_id == user_id,
            DailyGreeting.greeting_type == greeting_type,
            DailyGreeting.greeting_date == current_date,
            DailyGreeting.is_deleted == 0,
        )
    )
    result = _empty_payload(greeting_type, current_date)
    if record is not None:
        result = _payload(record, user)
    streak_item = await session.scalar(
        select(GreetingStreak).where(
            GreetingStreak.couple_id == _couple_id(user),
            GreetingStreak.streak_type == greeting_type,
        )
    )
    result["streakDays"] = streak_item.streak_days if streak_item else 0
    result["maxStreakDays"] = streak_item.max_streak_days if streak_item else 0
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def both_status(
    request: Request,
    session: AsyncSession,
    user_id: int,
    greeting_type: int,
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "both_status"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    partner = await session.scalar(
        select(User).where(User.couple_id == couple_id, User.id != user_id, User.is_deleted == 0)
    )
    if partner is None:
        await _fail(request, operation, started, 2001, "情侣关系不存在")
    current_date = _today()
    rows = await session.execute(
        select(DailyGreeting).where(
            DailyGreeting.couple_id == couple_id,
            DailyGreeting.greeting_type == greeting_type,
            DailyGreeting.greeting_date == current_date,
            DailyGreeting.is_deleted == 0,
        )
    )
    records = {item.user_id: item for item in rows.scalars().all()}
    mine = records.get(user_id)
    theirs = records.get(partner.id)
    result = _empty_payload(greeting_type, current_date)
    result["bothCheckStatus"] = {
        "myChecked": mine is not None,
        "partnerChecked": theirs is not None,
        "myCheckTime": mine.create_time.isoformat() if mine and mine.create_time else None,
        "partnerCheckTime": theirs.create_time.isoformat()
        if theirs and theirs.create_time
        else None,
    }
    streak_item = await session.scalar(
        select(GreetingStreak).where(
            GreetingStreak.couple_id == couple_id,
            GreetingStreak.streak_type == greeting_type,
        )
    )
    result["streakDays"] = streak_item.streak_days if streak_item else 0
    result["maxStreakDays"] = streak_item.max_streak_days if streak_item else 0
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def streak(
    request: Request,
    session: AsyncSession,
    user_id: int,
    streak_type: int,
) -> dict[str, object]:
    started = perf_counter()
    operation = "streak"
    user = await _couple_user(request, session, user_id, operation, started)
    item = await session.scalar(
        select(GreetingStreak).where(
            GreetingStreak.couple_id == _couple_id(user),
            GreetingStreak.streak_type == streak_type,
        )
    )
    result = _streak_payload(streak_type, item)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def history(
    request: Request,
    session: AsyncSession,
    user_id: int,
    greeting_type: int | None,
    limit: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "history"
    user = await _couple_user(request, session, user_id, operation, started)
    statement = select(DailyGreeting).where(
        DailyGreeting.couple_id == _couple_id(user),
        DailyGreeting.is_deleted == 0,
    )
    if greeting_type is not None:
        statement = statement.where(DailyGreeting.greeting_type == greeting_type)
    rows = await session.execute(
        statement.order_by(
            DailyGreeting.greeting_date.desc(),
            DailyGreeting.create_time.desc(),
            DailyGreeting.id.desc(),
        ).limit(limit)
    )
    result = await _payloads(session, list(rows.scalars().all()))
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def detail(
    request: Request,
    session: AsyncSession,
    user_id: int,
    greeting_id: int,
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    user = await _couple_user(request, session, user_id, operation, started)
    record = await session.scalar(
        select(DailyGreeting).where(
            DailyGreeting.id == greeting_id,
            DailyGreeting.is_deleted == 0,
        )
    )
    if record is None:
        await _fail(request, operation, started, 8601, "问候记录不存在")
    if record.couple_id != _couple_id(user):
        await _fail(request, operation, started, 8603, "无权操作此问候")
    sender = await session.scalar(select(User).where(User.id == record.user_id))
    result = _payload(record, sender)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result
