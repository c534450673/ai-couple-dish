import json
import secrets
from datetime import datetime
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import (
    Anniversary,
    Couple,
    CoupleMenu,
    Notification,
    SweetBomb,
    TimeCapsule,
    User,
)

logger = structlog.get_logger()

_BOMB_TYPES = ("memory", "data", "question", "festival")
_TYPE_NAMES = {
    "memory": "回忆时光机",
    "data": "恋爱数据站",
    "question": "心动问答",
    "festival": "节日提醒",
}
_QUESTIONS = (
    "如果可以重新选择，你还会选择和TA在一起吗？",
    "TA做的最让你感动的事情是什么？",
    "你最想和TA一起去哪里旅行？",
    "你觉得TA最可爱的地方是什么？",
    "你最想对TA说的一句话是什么？",
    "你们的第一次约会是什么样的？",
    "TA的哪个习惯让你觉得最温暖？",
    "如果给你一天时间，你最想和TA做什么？",
)


def _fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "sweet_bomb",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed", **_fields(request, operation, "rejected", started, str(code))
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
    if couple is None or couple.status != 1 or user.id not in {couple.user1_id, couple.user2_id}:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user, couple


async def _bomb_for_couple(
    request: Request,
    session: AsyncSession,
    couple_id: int,
    bomb_id: int,
    operation: str,
    started: float,
) -> SweetBomb:
    bomb = await session.scalar(select(SweetBomb).where(SweetBomb.id == bomb_id))
    if bomb is None:
        await _fail(request, operation, started, 9001, "炸弹不存在")
    if bomb.couple_id != couple_id:
        await _fail(request, operation, started, 3002, "无权操作此炸弹")
    return bomb


async def _partner_id(
    request: Request,
    session: AsyncSession,
    user: User,
    couple: Couple,
    operation: str,
    started: float,
) -> int:
    partner_id = couple.user2_id if couple.user1_id == user.id else couple.user1_id
    if partner_id is None or partner_id == user.id:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    partner = await session.scalar(select(User).where(User.id == partner_id, User.is_deleted == 0))
    if partner is None or partner.couple_id != couple.id:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return partner.id


def _content(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _payload(bomb: SweetBomb) -> dict[str, object | None]:
    return {
        "id": bomb.id,
        "bombType": bomb.bomb_type,
        "bombTypeName": _TYPE_NAMES.get(bomb.bomb_type, bomb.bomb_type),
        "content": _content(bomb.content),
        "sentTime": bomb.sent_time.isoformat() if bomb.sent_time else None,
        "isRead": bool(bomb.is_read),
        "isAnswered": bool(bomb.is_answered),
        "answerContent": bomb.answer_content,
        "answerTime": bomb.answer_time.isoformat() if bomb.answer_time else None,
        "createTime": bomb.create_time.isoformat() if bomb.create_time else None,
    }


async def _generated_content(
    session: AsyncSession, couple_id: int, bomb_type: str
) -> dict[str, object]:
    if bomb_type == "memory":
        anniversaries = list(
            (
                await session.execute(
                    select(Anniversary)
                    .where(Anniversary.couple_id == couple_id, Anniversary.is_deleted == 0)
                    .order_by(Anniversary.id.asc())
                    .limit(3)
                )
            ).scalars()
        )
        memory: dict[str, object] = {"memoryType": "anniversary"}
        if anniversaries:
            item = secrets.choice(anniversaries)
            memory["memoryContent"] = f"{item.name} - {item.anniversary_date.isoformat()}"
        return {
            "title": "回忆时光机 💫",
            "description": "还记得这些美好时刻吗？",
            "memoryData": memory,
        }
    if bomb_type == "data":
        menu_count = await session.scalar(
            select(func.count(CoupleMenu.id)).where(
                CoupleMenu.couple_id == couple_id,
                CoupleMenu.is_deleted == 0,
            )
        )
        anniversary_count = await session.scalar(
            select(func.count(Anniversary.id)).where(
                Anniversary.couple_id == couple_id,
                Anniversary.is_deleted == 0,
            )
        )
        capsule_count = await session.scalar(
            select(func.count(TimeCapsule.id)).where(
                TimeCapsule.couple_id == couple_id,
                TimeCapsule.is_deleted == 0,
            )
        )
        return {
            "title": "恋爱数据站 📊",
            "description": "来看看你们的恋爱数据吧~",
            "statsData": {
                "totalDates": int(menu_count or 0),
                "totalAnniversaries": int(anniversary_count or 0),
                "totalCapsules": int(capsule_count or 0),
            },
        }
    if bomb_type == "question":
        return {
            "title": "心动问答 💕",
            "description": "回答这个问题，让TA更了解你~",
            "question": secrets.choice(_QUESTIONS),
        }
    return {
        "title": "节日小提醒 🎉",
        "description": "快来看看今天是什么特别的日子~",
        "extraInfo": {"festivalType": "daily_reminder"},
    }


async def generate(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "generate"
    user, couple = await _couple_context(request, session, user_id, operation, started)
    partner_id = await _partner_id(request, session, user, couple, operation, started)
    bomb_type = secrets.choice(_BOMB_TYPES)
    try:
        now = datetime.now()
        bomb = SweetBomb(
            couple_id=couple.id,
            bomb_type=bomb_type,
            content=json.dumps(
                await _generated_content(session, couple.id, bomb_type), ensure_ascii=False
            ),
            sent_time=now,
            is_read=0,
            is_answered=0,
            create_time=now,
        )
        session.add(bomb)
        await session.flush()
        session.add(
            Notification(
                user_id=partner_id,
                type=2,
                title="💣 甜蜜炸弹",
                content="你收到了一个甜蜜炸弹，快来看看吧~",
                related_id=bomb.id,
                related_type="sweet_bomb",
                sender_id=user.id,
                is_read=0,
            )
        )
        await session.commit()
    except BusinessError:
        raise
    except Exception:
        await session.rollback()
        await logger.aerror(
            "business_operation_failed",
            **_fields(request, operation, "error", started, "WRITE_FAILED"),
        )
        raise
    result = _payload(bomb)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def unread(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "unread"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    result = await session.execute(
        select(SweetBomb)
        .where(SweetBomb.couple_id == couple.id, SweetBomb.is_read == 0)
        .order_by(SweetBomb.sent_time.desc(), SweetBomb.id.desc())
    )
    payload = [_payload(bomb) for bomb in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def detail(
    request: Request, session: AsyncSession, user_id: int, bomb_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    bomb = await _bomb_for_couple(request, session, couple.id, bomb_id, operation, started)
    result = _payload(bomb)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def mark_read(request: Request, session: AsyncSession, user_id: int, bomb_id: int) -> None:
    started = perf_counter()
    operation = "read"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    await _bomb_for_couple(request, session, couple.id, bomb_id, operation, started)
    try:
        await session.execute(
            update(SweetBomb)
            .where(
                SweetBomb.id == bomb_id,
                SweetBomb.couple_id == couple.id,
                SweetBomb.is_read == 0,
            )
            .values(is_read=1)
        )
        await session.commit()
    except Exception:
        await session.rollback()
        await logger.aerror(
            "business_operation_failed",
            **_fields(request, operation, "error", started, "WRITE_FAILED"),
        )
        raise
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def answer(
    request: Request, session: AsyncSession, user_id: int, bomb_id: int, answer_content: str
) -> None:
    started = perf_counter()
    operation = "answer"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    bomb = await _bomb_for_couple(request, session, couple.id, bomb_id, operation, started)
    if bomb.bomb_type != "question":
        await _fail(request, operation, started, 400, "此炸弹不需要回答")
    try:
        await session.execute(
            update(SweetBomb)
            .where(
                SweetBomb.id == bomb_id,
                SweetBomb.couple_id == couple.id,
                SweetBomb.is_answered == 0,
            )
            .values(is_answered=1, answer_content=answer_content, answer_time=datetime.now())
        )
        await session.commit()
    except Exception:
        await session.rollback()
        await logger.aerror(
            "business_operation_failed",
            **_fields(request, operation, "error", started, "WRITE_FAILED"),
        )
        raise
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def history(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "history"
    _, couple = await _couple_context(request, session, user_id, operation, started)
    result = await session.execute(
        select(SweetBomb)
        .where(SweetBomb.couple_id == couple.id)
        .order_by(SweetBomb.sent_time.desc(), SweetBomb.id.desc())
        .limit(limit)
    )
    payload = [_payload(bomb) for bomb in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def unread_count(request: Request, session: AsyncSession, user_id: int) -> int:
    started = perf_counter()
    operation = "unread_count"
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "empty", started)
        )
        return 0
    couple = await session.scalar(
        select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    )
    if couple is None or couple.status != 1 or user.id not in {couple.user1_id, couple.user2_id}:
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "empty", started)
        )
        return 0
    count = await session.scalar(
        select(func.count(SweetBomb.id)).where(
            SweetBomb.couple_id == couple.id, SweetBomb.is_read == 0
        )
    )
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return int(count or 0)
