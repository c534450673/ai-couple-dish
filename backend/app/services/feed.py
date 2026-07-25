import json
import secrets
from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Feed, Notification, User
from app.schemas.business import SendFeedRequest

logger = structlog.get_logger()
FEED_TYPES = ("meal", "dessert", "snack", "drink")
DAILY_LIMIT = 3
LOCK_TTL_SECONDS = 10
RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


def _log_fields(
    request_id: str, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request_id,
        "module": "feed",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_log_fields(request.state.request_id, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _release_lock(request: Request, lock_key: str, lock_value: str, started: float) -> None:
    try:
        await request.app.state.redis.raw.eval(RELEASE_LOCK_SCRIPT, 1, lock_key, lock_value)
    except Exception:
        await logger.aerror(
            "dependency_operation_failed",
            **_log_fields(
                request.state.request_id,
                "release_send_lock",
                "error",
                started,
                "REDIS_LOCK_RELEASE_FAILED",
            ),
        )


async def _user(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


async def _partner(
    request: Request, session: AsyncSession, user: User, operation: str, started: float
) -> User:
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    partner = await session.scalar(
        select(User).where(
            User.couple_id == user.couple_id,
            User.id != user.id,
            User.is_deleted == 0,
        )
    )
    if partner is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return partner


def _encode_urls(value: list[str] | None) -> str | None:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value else None


def _decode_urls(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _type_name(value: str) -> str:
    return {
        "meal": "正餐",
        "dessert": "甜品",
        "snack": "小吃",
        "drink": "饮品",
    }.get(value, "美食")


def _status_name(value: int) -> str:
    return {0: "待领取", 1: "已领取", 2: "已拒绝", 3: "已过期"}.get(value, "未知")


def _effective_status(item: Feed, now: datetime) -> int:
    return 3 if item.status == 0 and item.expire_time <= now else item.status


async def _payload(
    session: AsyncSession, item: Feed, now: datetime | None = None
) -> dict[str, object | None]:
    current = now or datetime.now()
    status = _effective_status(item, current)
    users = await session.execute(
        select(User).where(User.id.in_([item.sender_id, item.receiver_id]))
    )
    user_map = {user.id: user for user in users.scalars().all()}
    sender = user_map.get(item.sender_id)
    receiver = user_map.get(item.receiver_id)
    return {
        "id": item.id,
        "coupleId": item.couple_id,
        "senderId": item.sender_id,
        "senderName": sender.nick_name if sender else None,
        "senderAvatar": sender.avatar_url if sender else None,
        "receiverId": item.receiver_id,
        "receiverName": receiver.nick_name if receiver else None,
        "feedType": item.feed_type,
        "feedTypeName": _type_name(item.feed_type),
        "content": item.content,
        "imageUrls": _decode_urls(item.image_urls),
        "message": item.message,
        "status": status,
        "statusName": _status_name(status),
        "expireTime": item.expire_time.isoformat(),
        "createTime": item.create_time.isoformat() if item.create_time else None,
        "receiveTime": item.receive_time.isoformat() if item.receive_time else None,
        "rejectReason": item.reject_reason,
    }


def _notification(
    user_id: int,
    title: str,
    content: str,
    feed_id: int,
    sender_id: int,
) -> Notification:
    return Notification(
        user_id=user_id,
        type=2,
        title=title,
        content=content,
        related_id=feed_id,
        related_type="feed",
        sender_id=sender_id,
        is_read=0,
    )


def _day_bounds() -> tuple[datetime, datetime]:
    current = date.today()
    return (
        datetime.combine(current, datetime.min.time()),
        datetime.combine(current + timedelta(days=1), datetime.min.time()),
    )


async def today(request: Request, session: AsyncSession, user_id: int) -> dict[str, object | None]:
    started = perf_counter()
    operation = "today"
    await _user(request, session, user_id, operation, started)
    start_of_day, end_of_day = _day_bounds()
    now = datetime.now()
    all_sent = await session.execute(
        select(Feed.feed_type).where(
            Feed.sender_id == user_id,
            Feed.create_time >= start_of_day,
            Feed.create_time < end_of_day,
        )
    )
    sent_types = [str(value) for value in all_sent.scalars().all()]
    active_sent_count = int(
        await session.scalar(
            select(func.count(Feed.id)).where(
                Feed.sender_id == user_id,
                Feed.status == 0,
                Feed.create_time >= start_of_day,
                Feed.create_time < end_of_day,
            )
        )
        or 0
    )
    pending = await session.scalar(
        select(Feed)
        .where(
            Feed.receiver_id == user_id,
            Feed.status == 0,
            Feed.expire_time > now,
        )
        .order_by(Feed.create_time.desc(), Feed.id.desc())
        .limit(1)
    )
    unique_sent_types = list(dict.fromkeys(sent_types))
    result: dict[str, object | None] = {
        "sentToday": active_sent_count > 0,
        "receivedToday": pending is not None,
        "pendingFeed": await _payload(session, pending, now) if pending else None,
        "sentCount": len(sent_types),
        "remainingCount": max(0, DAILY_LIMIT - len(sent_types)),
        "sentTypes": unique_sent_types,
        "availableTypes": [value for value in FEED_TYPES if value not in unique_sent_types],
    }
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )
    return result


async def send(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: SendFeedRequest,
) -> int:
    started = perf_counter()
    operation = "send"
    user = await _user(request, session, user_id, operation, started)
    partner = await _partner(request, session, user, operation, started)
    feed_type = payload.feed_type.strip()
    if not feed_type:
        await _fail(request, operation, started, 9001, "参数无效")

    redis = request.app.state.redis.raw
    lock_key = f"lock:feed:send:{user_id}:{date.today().isoformat()}"
    lock_value = secrets.token_urlsafe(16)
    if not await redis.set(lock_key, lock_value, ex=LOCK_TTL_SECONDS, nx=True):
        await _fail(request, operation, started, 9005, "操作过于频繁，请稍后重试")
    try:
        start_of_day, end_of_day = _day_bounds()
        same_type_count = int(
            await session.scalar(
                select(func.count(Feed.id)).where(
                    Feed.sender_id == user_id,
                    Feed.feed_type == feed_type,
                    Feed.create_time >= start_of_day,
                    Feed.create_time < end_of_day,
                )
            )
            or 0
        )
        if same_type_count > 0:
            await _fail(request, operation, started, 9006, "今日已发送过该类型的投喂")
        sent_count = int(
            await session.scalar(
                select(func.count(Feed.id)).where(
                    Feed.sender_id == user_id,
                    Feed.create_time >= start_of_day,
                    Feed.create_time < end_of_day,
                )
            )
            or 0
        )
        if sent_count >= DAILY_LIMIT:
            await _fail(request, operation, started, 9007, "今日投喂次数已达上限（3次）")

        now = datetime.now()
        item = Feed(
            couple_id=user.couple_id,
            sender_id=user_id,
            receiver_id=partner.id,
            feed_type=feed_type,
            content=payload.content,
            image_urls=_encode_urls(payload.image_urls),
            message=payload.message,
            status=0,
            expire_time=now + timedelta(hours=24),
            create_time=now,
        )
        session.add(item)
        await session.flush()
        session.add(
            _notification(
                partner.id,
                "收到投喂",
                f"你的伴侣给你送了一份{_type_name(feed_type)}，快去看看吧！",
                item.id,
                user_id,
            )
        )
        await session.commit()
    finally:
        await _release_lock(request, lock_key, lock_value, started)
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )
    return item.id


async def received(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "received"
    await _user(request, session, user_id, operation, started)
    result = await session.execute(
        select(Feed)
        .where(Feed.receiver_id == user_id)
        .order_by(Feed.create_time.desc(), Feed.id.desc())
    )
    now = datetime.now()
    items = [await _payload(session, item, now) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )
    return items


async def sent(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "sent"
    await _user(request, session, user_id, operation, started)
    result = await session.execute(
        select(Feed)
        .where(Feed.sender_id == user_id)
        .order_by(Feed.create_time.desc(), Feed.id.desc())
    )
    now = datetime.now()
    items = [await _payload(session, item, now) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )
    return items


async def accept(request: Request, session: AsyncSession, user_id: int, feed_id: int) -> None:
    started = perf_counter()
    operation = "accept"
    await _user(request, session, user_id, operation, started)
    item = await session.scalar(select(Feed).where(Feed.id == feed_id).with_for_update())
    if item is None:
        await _fail(request, operation, started, 6001, "投喂记录不存在")
    if item.receiver_id != user_id:
        await _fail(request, operation, started, 6004, "无法接受此投喂")
    now = datetime.now()
    if item.status != 0 or item.expire_time <= now:
        if item.status == 0:
            item.status = 3
            session.add(
                _notification(
                    item.sender_id,
                    "投喂已过期",
                    "你的投喂已过期，可以重新发起投喂。",
                    item.id,
                    item.receiver_id,
                )
            )
            await session.commit()
        await _fail(request, operation, started, 6003, "投喂已过期")
    item.status = 1
    item.receive_time = now
    session.add(
        _notification(
            item.sender_id,
            "投喂被接受",
            "你的投喂被接受了，快去看看TA的反应吧！",
            item.id,
            user_id,
        )
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )


async def reject(
    request: Request,
    session: AsyncSession,
    user_id: int,
    feed_id: int,
    reason: str | None,
) -> None:
    started = perf_counter()
    operation = "reject"
    await _user(request, session, user_id, operation, started)
    item = await session.scalar(select(Feed).where(Feed.id == feed_id).with_for_update())
    if item is None:
        await _fail(request, operation, started, 6001, "投喂记录不存在")
    if item.receiver_id != user_id:
        await _fail(request, operation, started, 6004, "无法接受此投喂")
    item.status = 2
    item.reject_reason = reason
    session.add(
        _notification(
            item.sender_id,
            "投喂被拒绝",
            "你的投喂被拒绝了。",
            item.id,
            user_id,
        )
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request.state.request_id, operation, "success", started),
    )


async def expire_due(session: AsyncSession, request_id: str = "scheduler") -> int:
    started = perf_counter()
    now = datetime.now()
    result = await session.execute(
        select(Feed)
        .where(Feed.status == 0, Feed.expire_time < now)
        .with_for_update(skip_locked=True)
    )
    items = list(result.scalars().all())
    for item in items:
        item.status = 3
        session.add(
            _notification(
                item.sender_id,
                "投喂已过期",
                "你的投喂已过期，可以重新发起投喂。",
                item.id,
                item.receiver_id,
            )
        )
    if items:
        await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request_id, "expire_due", "success", started),
    )
    return len(items)
