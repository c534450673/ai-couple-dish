import asyncio
import secrets
from datetime import date, datetime
from time import perf_counter
from typing import Never, cast
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import DailyTask, User, UserTaskProgress
from app.services.couple_tree import add_nutrient_in_transaction

logger = structlog.get_logger()
BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
LOCK_TTL_SECONDS = 15
LOCK_RETRY_COUNT = 60
LOCK_RETRY_SECONDS = 0.025
RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""
TASK_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        "taskType": "greeting",
        "taskTypeName": "问候",
        "taskName": "早安问候",
        "taskDescription": "发送早安问候给TA",
        "targetCount": 1,
        "rewardNutrient": 10,
    },
    {
        "taskType": "goodnight",
        "taskTypeName": "问候",
        "taskName": "晚安问候",
        "taskDescription": "发送晚安问候给TA",
        "targetCount": 1,
        "rewardNutrient": 10,
    },
    {
        "taskType": "feed",
        "taskTypeName": "互动",
        "taskName": "投喂TA",
        "taskDescription": "给TA发送一次投喂",
        "targetCount": 1,
        "rewardNutrient": 15,
    },
    {
        "taskType": "menu",
        "taskTypeName": "记录",
        "taskName": "添加菜单",
        "taskDescription": "添加一个新的餐厅或菜品",
        "targetCount": 1,
        "rewardNutrient": 20,
    },
)
TASK_STATUS_NAMES = {0: "进行中", 1: "已完成", 2: "已过期"}


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "daily_task",
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


def _couple_id(user: User) -> int:
    if user.couple_id is None:
        raise RuntimeError("validated couple user is missing couple_id")
    return user.couple_id


async def _acquire_lock(
    request: Request,
    key: str,
    operation: str,
    started: float,
) -> tuple[str, str]:
    value = secrets.token_urlsafe(24)
    for attempt in range(LOCK_RETRY_COUNT):
        try:
            acquired = await request.app.state.redis.raw.set(
                key, value, ex=LOCK_TTL_SECONDS, nx=True
            )
        except Exception:
            await logger.aerror(
                "dependency_operation_failed",
                **_fields(request, "acquire_lock", "error", started, "REDIS_LOCK_FAILED"),
            )
            await _fail(request, operation, started, 9001, "任务操作繁忙，请稍后重试")
        if acquired:
            return key, value
        if attempt < LOCK_RETRY_COUNT - 1:
            await asyncio.sleep(LOCK_RETRY_SECONDS)
    await _fail(request, operation, started, 9001, "任务操作繁忙，请稍后重试")


async def _release_lock(request: Request, key: str, value: str, started: float) -> None:
    try:
        await request.app.state.redis.raw.eval(RELEASE_LOCK_SCRIPT, 1, key, value)
    except Exception:
        await logger.aerror(
            "dependency_operation_failed",
            **_fields(request, "release_lock", "error", started, "REDIS_LOCK_RELEASE_FAILED"),
        )


async def _ensure_today_tasks(
    request: Request,
    session: AsyncSession,
    couple_id: int,
    operation: str,
    started: float,
) -> None:
    current_date = _today()
    key = f"daily_task:generate:{couple_id}:{current_date.isoformat()}"
    lock_key, lock_value = await _acquire_lock(request, key, operation, started)
    try:
        # Reset a snapshot opened before waiting for the generation lock.
        await session.rollback()
        existing = await session.scalar(
            select(func.count(DailyTask.id)).where(
                DailyTask.couple_id == couple_id,
                DailyTask.task_date == current_date,
                DailyTask.is_deleted == 0,
            )
        )
        if int(existing or 0) == 0:
            for template in TASK_TEMPLATES:
                session.add(
                    DailyTask(
                        couple_id=couple_id,
                        task_date=current_date,
                        task_type=str(template["taskType"]),
                        task_name=str(template["taskName"]),
                        task_description=str(template["taskDescription"]),
                        target_count=cast(int, template["targetCount"]),
                        reward_nutrient=cast(int, template["rewardNutrient"]),
                        status=0,
                        is_deleted=0,
                    )
                )
            await session.commit()
    finally:
        await _release_lock(request, lock_key, lock_value, started)


async def _task_for_user(
    request: Request,
    session: AsyncSession,
    user: User,
    task_id: int,
    operation: str,
    started: float,
) -> DailyTask:
    task = await session.scalar(
        select(DailyTask).where(DailyTask.id == task_id, DailyTask.is_deleted == 0)
    )
    if task is None:
        await _fail(request, operation, started, 8801, "任务不存在")
    if task.couple_id != _couple_id(user):
        await _fail(request, operation, started, 3002, "无权操作此任务")
    return task


async def _progress_for(
    session: AsyncSession, task_id: int, user_id: int
) -> UserTaskProgress | None:
    return cast(
        UserTaskProgress | None,
        await session.scalar(
            select(UserTaskProgress).where(
                UserTaskProgress.task_id == task_id,
                UserTaskProgress.user_id == user_id,
            )
        ),
    )


async def _partner_id(session: AsyncSession, user: User) -> int | None:
    partner = await session.scalar(
        select(User.id).where(
            User.couple_id == _couple_id(user), User.id != user.id, User.is_deleted == 0
        )
    )
    return int(partner) if partner is not None else None


def _progress_payload(user: User | None, item: UserTaskProgress | None) -> dict[str, object | None]:
    return {
        "userId": user.id if user else None,
        "userName": user.nick_name if user else None,
        "userAvatar": user.avatar_url if user else None,
        "currentCount": item.current_count if item else 0,
        "isCompleted": bool(item and item.is_completed),
        "completeTime": item.complete_time.isoformat() if item and item.complete_time else None,
    }


async def _payload(
    session: AsyncSession, task: DailyTask, user_id: int
) -> dict[str, object | None]:
    users_result = await session.execute(
        select(User).where(User.couple_id == task.couple_id, User.is_deleted == 0)
    )
    users = {user.id: user for user in users_result.scalars().all()}
    mine = await _progress_for(session, task.id, user_id)
    partner_id = next((item for item in users if item != user_id), None)
    partner = users.get(partner_id) if partner_id is not None else None
    partner_progress = await _progress_for(session, task.id, partner_id) if partner_id else None
    return {
        "id": task.id,
        "taskDate": task.task_date.isoformat(),
        "taskType": task.task_type,
        "taskTypeName": next(
            (
                str(item["taskTypeName"])
                for item in TASK_TEMPLATES
                if item["taskType"] == task.task_type
            ),
            task.task_type,
        ),
        "taskName": task.task_name,
        "taskDescription": task.task_description,
        "targetCount": task.target_count,
        "rewardNutrient": task.reward_nutrient,
        "status": task.status,
        "statusName": TASK_STATUS_NAMES.get(task.status, "未知"),
        "myProgress": _progress_payload(users.get(user_id), mine),
        "partnerProgress": _progress_payload(partner, partner_progress),
        "rewardClaimed": bool(mine and mine.is_reward_claimed),
        "createTime": task.create_time.isoformat() if task.create_time else None,
    }


async def today(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "today"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    await _ensure_today_tasks(request, session, couple_id, operation, started)
    rows = await session.execute(
        select(DailyTask)
        .where(
            DailyTask.couple_id == couple_id,
            DailyTask.task_date == _today(),
            DailyTask.is_deleted == 0,
        )
        .order_by(DailyTask.create_time.asc(), DailyTask.id.asc())
    )
    result = [await _payload(session, task, user_id) for task in rows.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def detail(
    request: Request, session: AsyncSession, user_id: int, task_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "detail"
    user = await _couple_user(request, session, user_id, operation, started)
    task = await _task_for_user(request, session, user, task_id, operation, started)
    result = await _payload(session, task, user_id)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result


async def update_progress(
    request: Request,
    session: AsyncSession,
    user_id: int,
    task_id: int,
    count: int,
) -> None:
    started = perf_counter()
    operation = "progress"
    user = await _couple_user(request, session, user_id, operation, started)
    task = await _task_for_user(request, session, user, task_id, operation, started)
    if task.task_date < _today() or task.status == 2:
        await _fail(request, operation, started, 8802, "任务已过期")
    key = f"daily_task:progress:{task_id}:{user_id}"
    lock_key, lock_value = await _acquire_lock(request, key, operation, started)
    try:
        await session.rollback()
        user = await _couple_user(request, session, user_id, operation, started)
        task = await _task_for_user(request, session, user, task_id, operation, started)
        if task.task_date < _today() or task.status == 2:
            await _fail(request, operation, started, 8802, "任务已过期")
        item = await _progress_for(session, task_id, user_id)
        if item is None:
            item = UserTaskProgress(
                task_id=task_id,
                user_id=user_id,
                current_count=count,
                is_completed=0,
                is_reward_claimed=0,
            )
            session.add(item)
            await session.flush()
        else:
            item.current_count += count
        if item.current_count >= task.target_count:
            item.is_completed = 1
            item.complete_time = item.complete_time or datetime.now(BUSINESS_TIMEZONE).replace(
                tzinfo=None
            )
        partner_id = await _partner_id(session, user)
        if partner_id is not None:
            partner_item = await _progress_for(session, task_id, partner_id)
            if item.is_completed and partner_item and partner_item.is_completed:
                task.status = 1
        await session.commit()
    finally:
        await _release_lock(request, lock_key, lock_value, started)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def claim(
    request: Request,
    session: AsyncSession,
    user_id: int,
    task_id: int,
) -> None:
    started = perf_counter()
    operation = "claim"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    key = f"daily_task:claim:{couple_id}"
    lock_key, lock_value = await _acquire_lock(request, key, operation, started)
    try:
        await session.rollback()
        user = await _couple_user(request, session, user_id, operation, started)
        task = await _task_for_user(request, session, user, task_id, operation, started)
        if task.status != 1:
            await _fail(request, operation, started, 8803, "任务尚未完成")
        item = await _progress_for(session, task_id, user_id)
        if item is None or not item.is_completed:
            await _fail(request, operation, started, 8803, "任务尚未完成")
        if item.is_reward_claimed:
            await _fail(request, operation, started, 8804, "奖励已领取")
        await add_nutrient_in_transaction(
            session,
            _couple_id(user),
            user_id,
            task.reward_nutrient,
            "daily_task",
            None,
        )
        item.is_reward_claimed = 1
        item.reward_claim_time = datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)
        await session.commit()
    finally:
        await _release_lock(request, lock_key, lock_value, started)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def today_stats(request: Request, session: AsyncSession, user_id: int) -> dict[str, int]:
    started = perf_counter()
    operation = "today_stats"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    await _ensure_today_tasks(request, session, couple_id, operation, started)
    rows = await session.execute(
        select(DailyTask).where(
            DailyTask.couple_id == couple_id,
            DailyTask.task_date == _today(),
            DailyTask.is_deleted == 0,
        )
    )
    tasks = rows.scalars().all()
    completed = sum(1 for item in tasks if item.status == 1)
    earned = 0
    for task in tasks:
        item = await _progress_for(session, task.id, user_id)
        if item and item.is_reward_claimed:
            earned += task.reward_nutrient
    result = {
        "totalTasks": len(tasks),
        "completedTasks": completed,
        "inProgressTasks": sum(1 for item in tasks if item.status == 0),
        "totalRewardNutrient": sum(item.reward_nutrient for item in tasks),
        "earnedNutrient": earned,
    }
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return result
