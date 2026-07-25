import secrets
from datetime import date, datetime, timedelta
from time import perf_counter

import structlog
from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, CoupleUnbindRecord, Notification, User
from app.schemas.business import BindCoupleRequest, GenerateCodeRequest, UnbindRequest

logger = structlog.get_logger()
COUPLE_CODE_TTL_SECONDS = 7 * 24 * 60 * 60
UNBIND_RETENTION_DAYS = 30


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "couple",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _user(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
    user = result.scalar_one_or_none()
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


async def _couple(session: AsyncSession, couple_id: int) -> Couple | None:
    result = await session.execute(select(Couple).where(Couple.id == couple_id))
    return result.scalar_one_or_none()


def _partner_id(couple: Couple, user_id: int) -> int:
    if couple.user1_id == user_id and couple.user2_id is not None:
        return couple.user2_id
    if couple.user2_id == user_id:
        return couple.user1_id
    raise BusinessError(2006, "未绑定情侣关系")


async def _partner_payload(
    session: AsyncSession, couple: Couple, user_id: int
) -> dict[str, object | None]:
    partner_id = _partner_id(couple, user_id)
    partner = await _user(session, partner_id)
    return {
        "id": partner.id,
        "nickName": partner.nick_name,
        "avatarUrl": partner.avatar_url,
        "gender": partner.gender,
    }


async def couple_payload(
    session: AsyncSession, couple: Couple, user_id: int, *, include_partner: bool = True
) -> dict[str, object | None]:
    partner = await _partner_payload(session, couple, user_id) if include_partner else None
    return {
        "id": couple.id,
        "coupleCode": couple.couple_code,
        "user1Id": couple.user1_id,
        "user2Id": couple.user2_id,
        "startDate": couple.start_date.isoformat() if couple.start_date else None,
        "loveDays": couple.love_days,
        "coupleNickname": couple.couple_nickname,
        "status": couple.status,
        "partner": partner,
        "recoverableDays": None,
        "unbindRecordId": None,
    }


async def generate_code(
    request: Request, session: AsyncSession, user_id: int, payload: GenerateCodeRequest | None
) -> str:
    started = perf_counter()
    user = await _user(session, user_id)
    if user.couple_id is not None:
        raise BusinessError(2002, "已经绑定过情侣关系")
    redis = request.app.state.redis.raw
    reverse_key = f"couple:code:user:{user_id}"
    existing = await redis.get(reverse_key)
    if existing and await redis.exists(f"couple:code:{existing}"):
        await logger.ainfo(
            "business_operation_completed",
            **_log_fields(request, "generate_code", "reused", started),
        )
        return str(existing)
    code = secrets.token_hex(4).upper()
    start_date = (
        payload.love_start_date if payload and payload.love_start_date else date.today()
    ).isoformat()
    cache_key = f"couple:code:{code}"
    await redis.hset(cache_key, mapping={"userId": str(user_id), "loveStartDate": start_date})
    await redis.expire(cache_key, COUPLE_CODE_TTL_SECONDS)
    await redis.set(reverse_key, code, ex=COUPLE_CODE_TTL_SECONDS)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "generate_code", "success", started)
    )
    return code


async def refresh_code(request: Request, session: AsyncSession, user_id: int) -> str:
    user = await _user(session, user_id)
    if user.couple_id is not None:
        raise BusinessError(2002, "已经绑定过情侣关系")
    redis = request.app.state.redis.raw
    reverse_key = f"couple:code:user:{user_id}"
    old_code = await redis.get(reverse_key)
    if old_code:
        await redis.delete(f"couple:code:{old_code}", reverse_key)
    return await generate_code(request, session, user_id, GenerateCodeRequest())


async def validate_code(request: Request, code: str) -> bool:
    normalized = code.strip().upper()
    if not normalized or len(normalized) > 32:
        return False
    return bool(await request.app.state.redis.raw.exists(f"couple:code:{normalized}"))


async def code_info(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object] | None:
    user = await _user(session, user_id)
    if user.couple_id is not None:
        raise BusinessError(2002, "已经绑定过情侣关系")
    redis = request.app.state.redis.raw
    code = await redis.get(f"couple:code:user:{user_id}")
    if not code:
        return None
    cache_key = f"couple:code:{code}"
    values = await redis.hgetall(cache_key)
    if not values:
        return None
    ttl = max(0, int(await redis.ttl(cache_key)))
    now_ms = int(datetime.now().timestamp() * 1000)
    created_ms = now_ms - (COUPLE_CODE_TTL_SECONDS - ttl) * 1000
    remaining_days, rest = divmod(ttl, 86400)
    remaining_hours, rest = divmod(rest, 3600)
    remaining_minutes = rest // 60
    expired = ttl <= 0
    return {
        "coupleCode": code,
        "createTime": created_ms,
        "expireTime": now_ms + ttl * 1000,
        "remainingSeconds": ttl,
        "remainingDays": remaining_days,
        "remainingHours": remaining_hours,
        "remainingMinutes": remaining_minutes,
        "expiringSoon": not expired and ttl < 86400,
        "expired": expired,
        "status": "expired" if expired else ("expiring" if ttl < 86400 else "valid"),
        "creatorId": user.id,
        "creatorNickName": user.nick_name,
        "creatorAvatar": user.avatar_url,
    }


async def bind(
    request: Request, session: AsyncSession, user_id: int, payload: BindCoupleRequest
) -> dict[str, object | None]:
    started = perf_counter()
    redis = request.app.state.redis.raw
    code = payload.couple_code.strip().upper()
    lock_key = f"lock:bind:couple:{code}"
    lock_value = secrets.token_urlsafe(16)
    if not await redis.set(lock_key, lock_value, ex=10, nx=True):
        raise BusinessError(2005, "绑定冲突，请刷新重试")
    try:
        user = await _user(session, user_id)
        if user.couple_id is not None:
            raise BusinessError(2002, "已经绑定过情侣关系")
        values = await redis.hgetall(f"couple:code:{code}")
        if not values:
            raise BusinessError(2003, "情侣码无效或已过期")
        sender_id = int(values.get("userId", "0"))
        if sender_id == user_id:
            raise BusinessError(2005, "绑定冲突，请刷新重试")
        sender = await _user(session, sender_id)
        if sender.couple_id is not None:
            raise BusinessError(2002, "已经绑定过情侣关系")
        start_date = date.fromisoformat(values.get("loveStartDate", date.today().isoformat()))
        couple = Couple(
            couple_code=code,
            user1_id=sender_id,
            user2_id=user_id,
            start_date=start_date,
            love_days=max(0, (date.today() - start_date).days),
            couple_nickname=f"{sender.nick_name or 'TA'}&{user.nick_name or 'TA'}",
            status=1,
        )
        session.add(couple)
        await session.flush()
        sender.couple_id = couple.id
        sender.love_start_date = datetime.combine(start_date, datetime.min.time())
        user.couple_id = couple.id
        user.love_start_date = datetime.combine(start_date, datetime.min.time())
        session.add(
            Notification(
                user_id=sender_id,
                type=2,
                title="🎉 绑定成功",
                content="你们已经成为情侣啦，快去记录你们的美食之旅吧！",
                related_id=couple.id,
                related_type="couple",
                sender_id=user_id,
                is_read=0,
            )
        )
        await session.commit()
        await redis.delete(f"couple:code:{code}", f"couple:code:user:{sender_id}")
        await logger.ainfo(
            "business_operation_completed", **_log_fields(request, "bind", "success", started)
        )
        return await couple_payload(session, couple, user_id)
    except BusinessError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        await logger.aerror(
            "business_operation_failed",
            **_log_fields(request, "bind", "error", started, "COUPLE_BIND_FAILED"),
        )
        raise
    finally:
        if await redis.get(lock_key) == lock_value:
            await redis.delete(lock_key)


async def get_info(session: AsyncSession, user_id: int) -> dict[str, object | None] | None:
    user = await _user(session, user_id)
    if user.couple_id is None:
        return None
    couple = await _couple(session, user.couple_id)
    if couple is None or couple.status not in {1, 3}:
        return None
    return await couple_payload(session, couple, user_id)


async def get_home(session: AsyncSession, user_id: int) -> dict[str, object | None]:
    user = await _user(session, user_id)
    result: dict[str, object | None] = {
        "myInfo": {
            "id": user.id,
            "nickName": user.nick_name,
            "avatarUrl": user.avatar_url,
        },
        "partnerInfo": None,
        "loveDays": None,
        "acquaintanceDays": None,
        "nextAnniversary": None,
        "stats": {
            "menuCount": 0,
            "noteCount": 0,
            "photoCount": 0,
            "feedCount": 0,
            "wishAchievedCount": 0,
        },
        "todayFeed": None,
        "recentActivities": [],
    }
    if user.couple_id is not None:
        couple = await _couple(session, user.couple_id)
        if couple and couple.status == 1:
            result["partnerInfo"] = await _partner_payload(session, couple, user_id)
            result["loveDays"] = couple.love_days
    return result


async def love_timer(session: AsyncSession, user_id: int) -> dict[str, object | None]:
    info = await get_info(session, user_id)
    return {
        "loveDays": info["loveDays"] if info else None,
        "acquaintanceDays": None,
        "nextAnniversary": None,
    }


async def apply_unbind(
    request: Request, session: AsyncSession, user_id: int, payload: UnbindRequest | None
) -> None:
    started = perf_counter()
    user = await _user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    couple = await _couple(session, user.couple_id)
    if couple is None or couple.status != 1:
        raise BusinessError(2001, "情侣关系不存在")
    couple.status = 3
    couple.unbind_applicant_id = user_id
    couple.unbind_apply_time = datetime.now()
    partner_id = _partner_id(couple, user_id)
    session.add(
        Notification(
            user_id=partner_id,
            type=2,
            title="💔 申请解绑",
            content="你的伴侣申请了解绑，请确认",
            related_id=couple.id,
            related_type="couple",
            sender_id=user_id,
            is_read=0,
        )
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "apply_unbind", "success", started)
    )


async def confirm_unbind(
    request: Request, session: AsyncSession, user_id: int, couple_id: int
) -> None:
    started = perf_counter()
    user = await _user(session, user_id)
    couple = await _couple(session, couple_id)
    if couple is None or user.couple_id != couple_id or couple.status != 3:
        raise BusinessError(2006, "未绑定情侣关系")
    if couple.user2_id is None:
        raise BusinessError(2001, "情侣关系不存在")
    now = datetime.now()
    session.add(
        CoupleUnbindRecord(
            couple_id=couple.id,
            user1_id=couple.user1_id,
            user2_id=couple.user2_id,
            applicant_id=couple.unbind_applicant_id or user_id,
            love_start_date=datetime.combine(couple.start_date, datetime.min.time())
            if couple.start_date
            else None,
            love_days=couple.love_days,
            couple_nickname=couple.couple_nickname,
            unbind_time=now,
            data_expire_time=now + timedelta(days=UNBIND_RETENTION_DAYS),
            status=0,
        )
    )
    first = await _user(session, couple.user1_id)
    second = await _user(session, couple.user2_id)
    first.couple_id = None
    second.couple_id = None
    couple.status = 2
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "confirm_unbind", "success", started)
    )


async def reject_unbind(
    request: Request, session: AsyncSession, user_id: int, couple_id: int
) -> None:
    started = perf_counter()
    user = await _user(session, user_id)
    couple = await _couple(session, couple_id)
    if couple is None or user.couple_id != couple_id or couple.status != 3:
        raise BusinessError(2006, "未绑定情侣关系")
    if couple.unbind_applicant_id == user_id:
        raise BusinessError(2007, "需要双方确认才能解绑")
    couple.status = 1
    couple.unbind_applicant_id = None
    couple.unbind_apply_time = None
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "reject_unbind", "success", started)
    )


async def recoverable(session: AsyncSession, user_id: int) -> dict[str, object | None] | None:
    now = datetime.now()
    result = await session.execute(
        select(CoupleUnbindRecord)
        .where(
            or_(CoupleUnbindRecord.user1_id == user_id, CoupleUnbindRecord.user2_id == user_id),
            CoupleUnbindRecord.status == 0,
            CoupleUnbindRecord.data_expire_time > now,
        )
        .order_by(CoupleUnbindRecord.unbind_time.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    partner_id = record.user2_id if record.user1_id == user_id else record.user1_id
    partner = await _user(session, partner_id)
    return {
        "id": record.couple_id,
        "coupleCode": None,
        "user1Id": record.user1_id,
        "user2Id": record.user2_id,
        "startDate": record.love_start_date.date().isoformat() if record.love_start_date else None,
        "loveDays": record.love_days,
        "coupleNickname": record.couple_nickname,
        "status": 2,
        "partner": {
            "id": partner.id,
            "nickName": partner.nick_name,
            "avatarUrl": partner.avatar_url,
            "gender": partner.gender,
        },
        "recoverableDays": max(0, (record.data_expire_time - now).days),
        "unbindRecordId": record.id,
    }


async def recover(
    request: Request, session: AsyncSession, user_id: int, record_id: int
) -> dict[str, object | None]:
    user = await _user(session, user_id)
    if user.couple_id is not None:
        raise BusinessError(2002, "已经绑定过情侣关系")
    result = await session.execute(
        select(CoupleUnbindRecord).where(
            CoupleUnbindRecord.id == record_id,
            CoupleUnbindRecord.status == 0,
            CoupleUnbindRecord.data_expire_time > datetime.now(),
            or_(CoupleUnbindRecord.user1_id == user_id, CoupleUnbindRecord.user2_id == user_id),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise BusinessError(2001, "情侣关系不存在")
    partner_id = record.user2_id if record.user1_id == user_id else record.user1_id
    partner = await _user(session, partner_id)
    if partner.couple_id is not None:
        raise BusinessError(2002, "已经绑定过情侣关系")
    start_date = record.love_start_date.date() if record.love_start_date else date.today()
    couple = Couple(
        couple_code=None,
        user1_id=record.user1_id,
        user2_id=record.user2_id,
        start_date=start_date,
        love_days=record.love_days,
        couple_nickname=record.couple_nickname,
        status=1,
    )
    session.add(couple)
    await session.flush()
    user.couple_id = couple.id
    partner.couple_id = couple.id
    record.status = 1
    await session.commit()
    return await couple_payload(session, couple, user_id)
