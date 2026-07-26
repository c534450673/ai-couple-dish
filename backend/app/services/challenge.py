"""打卡挑战 FastAPI shadow 服务。"""

from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Challenge, CheckinRecord, Couple, User
from app.schemas.business import ChallengeCheckinRequest, ChallengeCreateRequest

logger = structlog.get_logger()

_STATUS_NAMES = {0: "进行中", 1: "已完成", 2: "已失败", 3: "已取消"}


@dataclass(frozen=True)
class _ActiveCouple:
    id: int
    user_id: int
    user1_id: int
    user2_id: int

    @property
    def partner_id(self) -> int:
        return self.user2_id if self.user_id == self.user1_id else self.user1_id


def _log_fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "challenge",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _completed(request: Request, operation: str, result: str, started: float) -> None:
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, operation, result, started),
    )


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


async def _unexpected(
    request: Request,
    session: AsyncSession,
    operation: str,
    started: float,
) -> None:
    await session.rollback()
    await logger.aerror(
        "business_operation_failed",
        **_log_fields(request, operation, "error", started, "INTERNAL_ERROR"),
    )


async def _active_couple(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
    *,
    lock: bool,
) -> _ActiveCouple:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")

    statement = select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    if lock:
        statement = statement.with_for_update()
    couple = await session.scalar(statement)
    if (
        couple is None
        or couple.user2_id is None
        or user.id not in {couple.user1_id, couple.user2_id}
    ):
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return _ActiveCouple(
        id=couple.id,
        user_id=user.id,
        user1_id=couple.user1_id,
        user2_id=couple.user2_id,
    )


async def _scoped_challenge(
    request: Request,
    session: AsyncSession,
    context: _ActiveCouple,
    challenge_id: int,
    operation: str,
    started: float,
    *,
    lock: bool,
) -> Challenge:
    statement = select(Challenge).where(
        Challenge.id == challenge_id,
        Challenge.is_deleted == 0,
    )
    if lock:
        statement = statement.with_for_update()
    challenge = await session.scalar(statement)
    if challenge is None or challenge.couple_id != context.id:
        await _fail(request, operation, started, 9999, "无权访问该挑战")
    return challenge


async def _load_users(session: AsyncSession, user_ids: set[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    users = list((await session.scalars(select(User).where(User.id.in_(user_ids)))).all())
    return {user.id: user for user in users}


def _record_payload(record: CheckinRecord, user: User | None) -> dict[str, object | None]:
    return {
        "id": record.id,
        "challengeId": record.challenge_id,
        "userId": record.user_id,
        "userName": user.nick_name if user is not None else None,
        "userAvatar": user.avatar_url if user is not None else None,
        "checkinDate": record.checkin_date.isoformat(),
        "content": record.content,
        "imageUrl": record.image_url,
        "createTime": record.create_time.isoformat() if record.create_time else None,
    }


def _challenge_payload(
    challenge: Challenge,
    users: dict[int, User],
    *,
    records: list[dict[str, object | None]] | None,
    today_checked: bool | None,
) -> dict[str, object | None]:
    creator = users.get(challenge.creator_id)
    partner = users.get(challenge.partner_id)
    progress = min(100, challenge.current_days * 100 // challenge.target_days)
    return {
        "id": challenge.id,
        "challengeType": challenge.challenge_type,
        "title": challenge.title,
        "description": challenge.description,
        "targetDays": challenge.target_days,
        "currentDays": challenge.current_days,
        "status": challenge.status,
        "statusDesc": _STATUS_NAMES.get(challenge.status, "未知"),
        "startDate": challenge.start_date.isoformat(),
        "endDate": challenge.end_date.isoformat() if challenge.end_date else None,
        "reward": challenge.reward,
        "creatorId": challenge.creator_id,
        "partnerId": challenge.partner_id,
        "creatorName": creator.nick_name if creator is not None else None,
        "partnerName": partner.nick_name if partner is not None else None,
        "createTime": challenge.create_time.isoformat() if challenge.create_time else None,
        "checkinRecords": records,
        "todayChecked": today_checked,
        "progressPercent": progress,
    }


async def _count_progress(session: AsyncSession, challenge_id: int) -> int:
    count = await session.scalar(
        select(func.count(func.distinct(CheckinRecord.checkin_date))).where(
            CheckinRecord.challenge_id == challenge_id
        )
    )
    return int(count or 0)


async def create(
    request: Request,
    session: AsyncSession,
    user_id: int,
    body: ChallengeCreateRequest,
) -> int:
    started = perf_counter()
    operation = "create"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=True)
        challenge_type = body.challenge_type.strip()
        title = body.title.strip()
        if not challenge_type:
            await _fail(request, operation, started, 400, "挑战类型不能为空")
        if not title:
            await _fail(request, operation, started, 400, "挑战标题不能为空")
        challenge = Challenge(
            couple_id=context.id,
            creator_id=context.user_id,
            partner_id=context.partner_id,
            challenge_type=challenge_type,
            title=title,
            description=body.description,
            target_days=body.target_days,
            current_days=0,
            status=0,
            start_date=body.start_date or date.today(),
            reward=body.reward,
            is_deleted=0,
        )
        session.add(challenge)
        await session.flush()
        challenge_id = challenge.id
        await session.commit()
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)
    return challenge_id


async def accept(request: Request, session: AsyncSession, user_id: int, challenge_id: int) -> None:
    started = perf_counter()
    operation = "accept"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=True)
        challenge = await _scoped_challenge(
            request, session, context, challenge_id, operation, started, lock=True
        )
        if challenge.partner_id != user_id:
            await _fail(request, operation, started, 9999, "您不是该挑战的伙伴")
        if challenge.status != 0:
            await _fail(request, operation, started, 9999, "挑战状态不允许操作")

        # 现表没有 accepted 字段，pending/active 均映射为 0；接受只能是兼容 no-op。
        await session.commit()
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)


async def _partner_transition(
    request: Request,
    session: AsyncSession,
    user_id: int,
    challenge_id: int,
    operation: str,
) -> None:
    started = perf_counter()
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=True)
        challenge = await _scoped_challenge(
            request, session, context, challenge_id, operation, started, lock=True
        )
        if challenge.partner_id != user_id:
            await _fail(request, operation, started, 9999, "您不是该挑战的伙伴")
        if challenge.status != 0:
            await _fail(request, operation, started, 9999, "挑战状态不允许操作")

        # 现表没有 rejected actor；拒绝与创建者取消都只能持久化为终态 3。
        result = await session.execute(
            update(Challenge)
            .where(
                Challenge.id == challenge.id,
                Challenge.status == 0,
                Challenge.is_deleted == 0,
            )
            .values(status=3, update_time=func.now())
        )
        if getattr(result, "rowcount", 0) != 1:
            await _fail(request, operation, started, 9999, "挑战状态不允许操作")
        await session.commit()
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)


async def reject(request: Request, session: AsyncSession, user_id: int, challenge_id: int) -> None:
    await _partner_transition(request, session, user_id, challenge_id, "reject")


async def cancel(request: Request, session: AsyncSession, user_id: int, challenge_id: int) -> None:
    started = perf_counter()
    operation = "cancel"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=True)
        challenge = await _scoped_challenge(
            request, session, context, challenge_id, operation, started, lock=True
        )
        if challenge.creator_id != user_id:
            await _fail(request, operation, started, 9999, "只有创建者可以取消挑战")
        if challenge.status != 0:
            await _fail(request, operation, started, 9999, "挑战状态不允许取消")
        result = await session.execute(
            update(Challenge)
            .where(
                Challenge.id == challenge.id,
                Challenge.status == 0,
                Challenge.is_deleted == 0,
            )
            .values(status=3, update_time=func.now())
        )
        if getattr(result, "rowcount", 0) != 1:
            await _fail(request, operation, started, 9999, "挑战状态不允许取消")
        await session.commit()
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)


async def checkin(
    request: Request,
    session: AsyncSession,
    user_id: int,
    body: ChallengeCheckinRequest,
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "checkin"
    log_result = "success"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=True)
        challenge = await _scoped_challenge(
            request,
            session,
            context,
            body.challenge_id,
            operation,
            started,
            lock=True,
        )
        if user_id not in {challenge.creator_id, challenge.partner_id}:
            await _fail(request, operation, started, 9999, "您不是该挑战的参与者")
        if challenge.status != 0:
            await _fail(request, operation, started, 9999, "挑战状态不允许操作")
        today = date.today()
        if today < challenge.start_date:
            await _fail(request, operation, started, 9999, "挑战尚未开始")

        existing = await session.scalar(
            select(CheckinRecord)
            .where(
                CheckinRecord.challenge_id == challenge.id,
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date == today,
            )
            .order_by(CheckinRecord.id.asc())
            .limit(1)
            .with_for_update()
        )
        if existing is not None:
            users = await _load_users(session, {existing.user_id})
            payload = _record_payload(existing, users.get(existing.user_id))
            await session.commit()
            log_result = "idempotent"
        else:
            record = CheckinRecord(
                challenge_id=challenge.id,
                user_id=user_id,
                checkin_date=today,
                content=body.content,
                image_url=body.image_url,
            )
            session.add(record)
            await session.flush()
            progress = await _count_progress(session, challenge.id)
            complete = progress >= challenge.target_days
            values: dict[str, object] = {
                "current_days": progress,
                "status": 1 if complete else 0,
                "update_time": func.now(),
            }
            if complete:
                values["end_date"] = today
            result = await session.execute(
                update(Challenge)
                .where(
                    Challenge.id == challenge.id,
                    Challenge.status == 0,
                    Challenge.is_deleted == 0,
                )
                .values(**values)
            )
            if getattr(result, "rowcount", 0) != 1:
                await _fail(request, operation, started, 9999, "挑战状态不允许操作")
            await session.refresh(record)
            users = await _load_users(session, {record.user_id})
            payload = _record_payload(record, users.get(record.user_id))
            await session.commit()
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, log_result, started)
    return payload


async def detail(
    request: Request, session: AsyncSession, user_id: int, challenge_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=False)
        challenge = await _scoped_challenge(
            request, session, context, challenge_id, operation, started, lock=False
        )
        records = list(
            (
                await session.scalars(
                    select(CheckinRecord)
                    .where(CheckinRecord.challenge_id == challenge.id)
                    .order_by(CheckinRecord.checkin_date.desc(), CheckinRecord.id.desc())
                    .limit(20)
                )
            ).all()
        )
        today_checkin_count = await session.scalar(
            select(func.count(CheckinRecord.id)).where(
                CheckinRecord.challenge_id == challenge.id,
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date == date.today(),
            )
        )
        user_ids = {challenge.creator_id, challenge.partner_id}
        user_ids.update(record.user_id for record in records)
        users = await _load_users(session, user_ids)
        record_payloads = [_record_payload(record, users.get(record.user_id)) for record in records]
        payload = _challenge_payload(
            challenge,
            users,
            records=record_payloads,
            today_checked=bool(today_checkin_count),
        )
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)
    return payload


async def list_challenges(
    request: Request,
    session: AsyncSession,
    user_id: int,
    status: int | None,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "list"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=False)
        statement = select(Challenge).where(
            Challenge.couple_id == context.id,
            Challenge.is_deleted == 0,
        )
        if status is not None:
            statement = statement.where(Challenge.status == status)
        challenges = list(
            (
                await session.scalars(
                    statement.order_by(Challenge.create_time.desc(), Challenge.id.desc())
                )
            ).all()
        )
        user_ids = {
            owner_id
            for challenge in challenges
            for owner_id in (challenge.creator_id, challenge.partner_id)
        }
        users = await _load_users(session, user_ids)
        payload = [
            _challenge_payload(challenge, users, records=None, today_checked=None)
            for challenge in challenges
        ]
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)
    return payload


async def checkin_records(
    request: Request,
    session: AsyncSession,
    user_id: int,
    challenge_id: int,
    page_num: int,
    page_size: int,
) -> dict[str, object]:
    started = perf_counter()
    operation = "checkin_records"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=False)
        challenge = await _scoped_challenge(
            request, session, context, challenge_id, operation, started, lock=False
        )
        total = int(
            await session.scalar(
                select(func.count(CheckinRecord.id)).where(
                    CheckinRecord.challenge_id == challenge.id
                )
            )
            or 0
        )
        records = list(
            (
                await session.scalars(
                    select(CheckinRecord)
                    .where(CheckinRecord.challenge_id == challenge.id)
                    .order_by(CheckinRecord.checkin_date.desc(), CheckinRecord.id.desc())
                    .offset((page_num - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        users = await _load_users(session, {record.user_id for record in records})
        payload: dict[str, object] = {
            "records": [_record_payload(record, users.get(record.user_id)) for record in records],
            "total": total,
            "size": page_size,
            "current": page_num,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)
    return payload


async def pending(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "pending"
    try:
        context = await _active_couple(request, session, user_id, operation, started, lock=False)
        # Spring 兼容：accept 不改变 status，因此接受后仍保留在 pending 查询中。
        challenges = list(
            (
                await session.scalars(
                    select(Challenge)
                    .where(
                        Challenge.couple_id == context.id,
                        Challenge.partner_id == user_id,
                        Challenge.status == 0,
                        Challenge.is_deleted == 0,
                    )
                    .order_by(Challenge.create_time.desc(), Challenge.id.desc())
                )
            ).all()
        )
        user_ids = {
            owner_id
            for challenge in challenges
            for owner_id in (challenge.creator_id, challenge.partner_id)
        }
        users = await _load_users(session, user_ids)
        payload = [
            _challenge_payload(challenge, users, records=None, today_checked=None)
            for challenge in challenges
        ]
    except BusinessError:
        raise
    except Exception:
        await _unexpected(request, session, operation, started)
        raise
    await _completed(request, operation, "success", started)
    return payload
