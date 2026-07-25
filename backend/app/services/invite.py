"""Invite referral shadow service.

This module intentionally keeps all seven Spring invite endpoints authenticated.
The couple binding code under ``/couple`` is a separate contract and is not used here.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from secrets import choice
from string import ascii_uppercase, digits
from time import perf_counter
from typing import Never
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import User, UserInviteCode, UserReferral

logger = structlog.get_logger()
BUSINESS_ZONE = ZoneInfo("Asia/Shanghai")
REGISTER_REWARD = Decimal("5.00")
INVITE_LINK_PREFIX = "https://aicoupledish.com/invite/"
CODE_ALPHABET = ascii_uppercase + digits
ZERO_AMOUNT = Decimal("0.00")


def _now() -> datetime:
    return datetime.now(BUSINESS_ZONE).replace(tzinfo=None)


def _fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "invite",
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


async def _user_for_update(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = await session.scalar(
        select(User).where(User.id == user_id, User.is_deleted == 0).with_for_update()
    )
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


def _candidate(length: int = 6) -> str:
    return "".join(choice(CODE_ALPHABET) for _ in range(length))


def _money(value: Decimal) -> float:
    return float(value)


async def _code_payload(session: AsyncSession, item: UserInviteCode) -> dict[str, object | None]:
    referrals = (
        await session.scalars(select(UserReferral).where(UserReferral.inviter_id == item.user_id))
    ).all()
    bound_count = sum(referral.bind_couple_time is not None for referral in referrals)
    pending_reward = sum(
        (
            (referral.reward_amount or ZERO_AMOUNT)
            for referral in referrals
            if referral.reward_status == 0
        ),
        start=ZERO_AMOUNT,
    )
    return {
        "id": item.id,
        "inviteCode": item.invite_code,
        "inviteCount": item.invite_count,
        "boundCount": bound_count,
        "rewardAmount": _money(item.reward_amount or ZERO_AMOUNT),
        "pendingRewardAmount": _money(pending_reward),
        "inviteLink": INVITE_LINK_PREFIX + item.invite_code,
        "qrcodeUrl": f"/qrcode/{item.invite_code}.png",
        "createTime": item.create_time.isoformat() if item.create_time else None,
    }


async def _create_code_with_retry(session: AsyncSession, user_id: int) -> UserInviteCode:
    for length, attempts in ((6, 10), (8, 10)):
        for _ in range(attempts):
            item = UserInviteCode(
                user_id=user_id,
                invite_code=_candidate(length),
                invite_count=0,
                reward_amount=ZERO_AMOUNT,
            )
            try:
                async with session.begin_nested():
                    session.add(item)
                    await session.flush()
            except IntegrityError:
                existing = await session.scalar(
                    select(UserInviteCode).where(UserInviteCode.user_id == user_id)
                )
                if existing is not None:
                    return existing
                continue
            return item
    raise RuntimeError("invite code generation exhausted")


async def code(request: Request, session: AsyncSession, user_id: int) -> dict[str, object | None]:
    started = perf_counter()
    operation = "code"
    await _user_for_update(request, session, user_id, operation, started)
    item = await session.scalar(select(UserInviteCode).where(UserInviteCode.user_id == user_id))
    if item is None:
        try:
            item = await _create_code_with_retry(session, user_id)
        except RuntimeError:
            await session.rollback()
            await _fail(request, operation, started, 9999, "邀请码生成失败，请稍后重试")
    await session.refresh(item)
    payload = await _code_payload(session, item)
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def use(request: Request, session: AsyncSession, user_id: int, invite_code: str) -> None:
    started = perf_counter()
    operation = "use"
    if not invite_code.strip():
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "noop_empty", started)
        )
        return
    user = await _user_for_update(request, session, user_id, operation, started)
    existing = await session.scalar(
        select(UserReferral).where(UserReferral.invitee_id == user.id).with_for_update()
    )
    if existing is not None:
        await session.commit()
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, "noop_existing", started)
        )
        return
    code_item = await session.scalar(
        select(UserInviteCode).where(UserInviteCode.invite_code == invite_code).with_for_update()
    )
    if code_item is None or code_item.user_id == user.id:
        await session.commit()
        result = "noop_invalid" if code_item is None else "noop_self"
        await logger.ainfo(
            "business_operation_completed", **_fields(request, operation, result, started)
        )
        return
    referral = UserReferral(
        inviter_id=code_item.user_id,
        invitee_id=user.id,
        invite_code=invite_code,
        register_time=_now(),
        reward_status=0,
        reward_amount=REGISTER_REWARD,
    )
    session.add(referral)
    await session.execute(
        update(UserInviteCode)
        .where(UserInviteCode.id == code_item.id)
        .values(invite_count=UserInviteCode.invite_count + 1)
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def _referral_payloads(
    session: AsyncSession, referrals: Iterable[UserReferral]
) -> list[dict[str, object | None]]:
    rows = list(referrals)
    ids = {item.invitee_id for item in rows}
    users: dict[int, User] = {}
    if ids:
        users = {
            user.id: user
            for user in (
                await session.scalars(select(User).where(User.id.in_(ids), User.is_deleted == 0))
            ).all()
        }
    payloads: list[dict[str, object | None]] = []
    for item in rows:
        invitee = users.get(item.invitee_id)
        payloads.append(
            {
                "id": item.id,
                "inviteeId": item.invitee_id,
                "inviteeName": invitee.nick_name if invitee else None,
                "inviteeAvatar": invitee.avatar_url if invitee else None,
                "inviteCode": item.invite_code,
                "registerTime": item.register_time.isoformat() if item.register_time else None,
                "hasBoundCouple": item.bind_couple_time is not None,
                "bindCoupleTime": item.bind_couple_time.isoformat()
                if item.bind_couple_time
                else None,
                "rewardStatus": item.reward_status,
                "rewardStatusName": "已发放" if item.reward_status == 1 else "待发放",
                "rewardAmount": _money(item.reward_amount or ZERO_AMOUNT),
                "rewardTime": item.reward_time.isoformat() if item.reward_time else None,
            }
        )
    return payloads


async def referrals(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "referrals"
    if limit < 1 or limit > 100:
        await _fail(request, operation, started, 9001, "参数无效")
    rows = await session.scalars(
        select(UserReferral)
        .where(UserReferral.inviter_id == user_id)
        .order_by(UserReferral.register_time.desc(), UserReferral.id.desc())
        .limit(limit)
    )
    payload = await _referral_payloads(session, rows.all())
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def stats(request: Request, session: AsyncSession, user_id: int) -> dict[str, object | None]:
    started = perf_counter()
    operation = "stats"
    rows = (
        await session.scalars(select(UserReferral).where(UserReferral.inviter_id == user_id))
    ).all()
    total = len(rows)
    bound = sum(item.bind_couple_time is not None for item in rows)
    total_reward = sum(((item.reward_amount or ZERO_AMOUNT) for item in rows), start=ZERO_AMOUNT)
    claimed = sum(
        ((item.reward_amount or ZERO_AMOUNT) for item in rows if item.reward_status == 1),
        start=ZERO_AMOUNT,
    )
    week_start = (_now() - timedelta(days=_now().weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    month_start = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    weekly = sum(item.register_time >= week_start for item in rows)
    monthly = sum(item.register_time >= month_start for item in rows)
    payload: dict[str, object | None] = {
        "totalInvites": total,
        "boundCoupleCount": bound,
        "pendingBindCount": total - bound,
        "totalRewardAmount": _money(total_reward),
        "claimedRewardAmount": _money(claimed),
        "pendingRewardAmount": _money(total_reward - claimed),
        "weeklyNewInvites": weekly,
        "monthlyNewInvites": monthly,
        "rankList": [],
    }
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def rank(
    request: Request, session: AsyncSession, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "rank"
    if limit < 1 or limit > 100:
        await _fail(request, operation, started, 9001, "参数无效")
    rows = (
        await session.scalars(
            select(UserInviteCode)
            .order_by(UserInviteCode.invite_count.desc(), UserInviteCode.user_id.asc())
            .limit(limit)
        )
    ).all()
    ids = {item.user_id for item in rows}
    users = (
        {
            user.id: user
            for user in (
                await session.scalars(select(User).where(User.id.in_(ids), User.is_deleted == 0))
            ).all()
        }
        if ids
        else {}
    )
    payload: list[dict[str, object | None]] = []
    for index, item in enumerate(rows, start=1):
        user = users.get(item.user_id)
        payload.append(
            {
                "rank": index,
                "userId": item.user_id,
                "userName": user.nick_name if user else None,
                "userAvatar": user.avatar_url if user else None,
                "inviteCount": item.invite_count,
                "rewardAmount": _money(item.reward_amount or ZERO_AMOUNT),
            }
        )
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def validate(request: Request, session: AsyncSession, invite_code: str) -> bool:
    started = perf_counter()
    operation = "validate"
    valid = bool(
        invite_code.strip()
        and await session.scalar(
            select(func.count(UserInviteCode.id)).where(UserInviteCode.invite_code == invite_code)
        )
    )
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "valid" if valid else "invalid", started),
    )
    return valid


async def info(
    request: Request, session: AsyncSession, invite_code: str
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "info"
    item = await session.scalar(
        select(UserInviteCode).where(UserInviteCode.invite_code == invite_code)
    )
    if item is None:
        await _fail(request, operation, started, 404, "邀请码不存在")
    payload: dict[str, object | None] = {
        "id": None,
        "inviteCode": item.invite_code,
        "inviteCount": item.invite_count,
        "boundCount": None,
        "rewardAmount": _money(item.reward_amount or ZERO_AMOUNT),
        "pendingRewardAmount": None,
        "inviteLink": None,
        "qrcodeUrl": None,
        "createTime": item.create_time.isoformat() if item.create_time else None,
    }
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload
