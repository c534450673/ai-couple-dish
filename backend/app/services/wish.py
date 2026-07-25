from datetime import date, datetime
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import User, Wish
from app.schemas.business import WishCreateRequest, WishUpdateRequest

logger = structlog.get_logger()


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "wish",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_log_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _find_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
    return result.scalar_one_or_none()


async def _require_user(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = await _find_user(session, user_id)
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


def _type_name(value: str) -> str:
    return {"restaurant": "餐厅", "dish": "菜品", "recipe": "食谱"}.get(value, "其他")


def _priority_name(value: int) -> str:
    return {1: "低", 2: "中", 3: "高"}.get(value, "中")


def _status_name(value: int) -> str:
    return {0: "待实现", 1: "进行中", 2: "已实现", 3: "已过期"}.get(value, "待实现")


async def _payload(session: AsyncSession, item: Wish) -> dict[str, object | None]:
    creator = await session.scalar(select(User).where(User.id == item.creator_id))
    in_progress_days = (
        max(0, (datetime.now() - item.in_progress_time).days)
        if item.in_progress_time is not None
        else None
    )
    return {
        "id": item.id,
        "coupleId": item.couple_id,
        "creatorId": item.creator_id,
        "creatorName": creator.nick_name if creator else None,
        "creatorAvatar": creator.avatar_url if creator else None,
        "wishType": item.wish_type,
        "wishTypeName": _type_name(item.wish_type),
        "title": item.title,
        "description": item.description,
        "imageUrl": item.image_url,
        "priority": item.priority,
        "priorityName": _priority_name(item.priority),
        "status": item.status,
        "statusName": _status_name(item.status),
        "targetDate": item.target_date.isoformat() if item.target_date else None,
        "achievedDate": item.achieved_date.isoformat() if item.achieved_date else None,
        "createTime": item.create_time.isoformat() if item.create_time else None,
        "viewerId": item.viewer_id,
        "viewTime": item.view_time.isoformat() if item.view_time else None,
        "inProgressTime": item.in_progress_time.isoformat() if item.in_progress_time else None,
        "viewed": item.viewer_id is not None,
        "inProgressDays": in_progress_days,
    }


async def _item_for_user(
    request: Request,
    session: AsyncSession,
    user: User,
    wish_id: int,
    operation: str,
    started: float,
    *,
    lock: bool = False,
) -> Wish:
    statement = select(Wish).where(Wish.id == wish_id, Wish.is_deleted == 0)
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        await _fail(request, operation, started, 8501, "心愿不存在")
    if user.couple_id is None or item.couple_id != user.couple_id:
        await _fail(request, operation, started, 8502, "无权操作此心愿")
    return item


async def list_wishes(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "list"
    user = await _find_user(session, user_id)
    if user is None or user.couple_id is None:
        await logger.ainfo(
            "business_operation_completed", **_log_fields(request, operation, "empty", started)
        )
        return []
    result = await session.execute(
        select(Wish)
        .where(Wish.couple_id == user.couple_id, Wish.is_deleted == 0)
        .order_by(Wish.create_time.desc(), Wish.id.desc())
    )
    items = [await _payload(session, item) for item in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return items


async def detail(
    request: Request, session: AsyncSession, user_id: int, wish_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    user = await _require_user(request, session, user_id, operation, started)
    item = await _item_for_user(request, session, user, wish_id, operation, started)
    result = await _payload(session, item)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return result


async def add(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: WishCreateRequest,
) -> int:
    started = perf_counter()
    operation = "add"
    user = await _require_user(request, session, user_id, operation, started)
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    wish_type = payload.wish_type.strip()
    title = payload.title.strip()
    if not wish_type or not title:
        await _fail(request, operation, started, 9001, "参数无效")
    item = Wish(
        couple_id=user.couple_id,
        creator_id=user_id,
        wish_type=wish_type,
        title=title,
        description=payload.description,
        image_url=payload.image_url,
        priority=payload.priority or 2,
        status=0,
        is_deleted=0,
    )
    session.add(item)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return item.id


async def update_wish(
    request: Request,
    session: AsyncSession,
    user_id: int,
    wish_id: int,
    payload: WishUpdateRequest,
) -> None:
    started = perf_counter()
    operation = "update"
    user = await _require_user(request, session, user_id, operation, started)
    item = await _item_for_user(request, session, user, wish_id, operation, started, lock=True)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            await _fail(request, operation, started, 9001, "参数无效")
        item.title = title
    if payload.description is not None:
        item.description = payload.description
    if payload.image_url is not None:
        item.image_url = payload.image_url
    if payload.priority is not None:
        item.priority = payload.priority
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )


async def delete_wish(request: Request, session: AsyncSession, user_id: int, wish_id: int) -> None:
    started = perf_counter()
    operation = "delete"
    user = await _require_user(request, session, user_id, operation, started)
    item = await _item_for_user(request, session, user, wish_id, operation, started, lock=True)
    item.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )


async def fulfill(request: Request, session: AsyncSession, user_id: int, wish_id: int) -> None:
    started = perf_counter()
    operation = "fulfill"
    user = await _require_user(request, session, user_id, operation, started)
    item = await _item_for_user(request, session, user, wish_id, operation, started, lock=True)
    item.status = 2
    item.achieved_date = date.today()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )


async def unfulfill(request: Request, session: AsyncSession, user_id: int, wish_id: int) -> None:
    started = perf_counter()
    operation = "unfulfill"
    user = await _require_user(request, session, user_id, operation, started)
    item = await _item_for_user(request, session, user, wish_id, operation, started, lock=True)
    if item.status != 2:
        await _fail(request, operation, started, 9001, "只有已实现的心愿才能撤销")
    item.status = 1
    item.achieved_date = None
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
