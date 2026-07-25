from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Never, cast

import structlog
from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import CoupleTree, TreeNutrientLog, User
from app.schemas.business import WaterTreeRequest

logger = structlog.get_logger()

LEVEL_NUTRIENTS: tuple[int, ...] = (
    0,
    100,
    300,
    600,
    1000,
    1500,
    2100,
    2800,
    3600,
    4500,
    5500,
    6600,
    7800,
    9100,
    10500,
)
LEVEL_NAMES: tuple[str, ...] = (
    "幼苗",
    "小树",
    "成长树",
    "茁壮树",
    "茂盛树",
    "开花树",
    "结果树",
    "智慧树",
    "幸福树",
    "永恒树",
    "传奇树",
    "神话树",
    "圣树",
    "神树",
    "世界树",
)
SKINS: tuple[dict[str, object], ...] = (
    {
        "skinId": "default",
        "skinName": "默认",
        "previewUrl": "/skins/default.png",
        "requiredLevel": 1,
    },
    {
        "skinId": "spring",
        "skinName": "春日樱花",
        "previewUrl": "/skins/spring.png",
        "requiredLevel": 3,
    },
    {
        "skinId": "summer",
        "skinName": "夏日清凉",
        "previewUrl": "/skins/summer.png",
        "requiredLevel": 5,
    },
    {
        "skinId": "autumn",
        "skinName": "秋日金桂",
        "previewUrl": "/skins/autumn.png",
        "requiredLevel": 7,
    },
    {
        "skinId": "winter",
        "skinName": "冬日雪松",
        "previewUrl": "/skins/winter.png",
        "requiredLevel": 10,
    },
)
SKIN_BY_ID = {str(item["skinId"]): item for item in SKINS}
ACTION_NAMES = {
    "manual_water": "手动浇水",
    "daily_task": "每日任务",
    "greeting": "早安晚安打卡",
    "anniversary": "纪念日奖励",
    "feed": "投喂奖励",
    "wish_achieved": "心愿实现",
}


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "couple_tree",
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


async def _get_or_create_tree(session: AsyncSession, couple_id: int) -> CoupleTree:
    tree = await session.scalar(
        select(CoupleTree).where(CoupleTree.couple_id == couple_id, CoupleTree.is_deleted == 0)
    )
    if tree is not None:
        return tree
    tree = CoupleTree(
        couple_id=couple_id,
        level=1,
        total_nutrient=0,
        current_level_nutrient=0,
        skin_id="default",
        is_deleted=0,
    )
    session.add(tree)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        tree = await session.scalar(
            select(CoupleTree)
            .where(CoupleTree.couple_id == couple_id, CoupleTree.is_deleted == 0)
            .execution_options(populate_existing=True)
        )
        if tree is None:
            raise
        await session.refresh(tree)
    return tree


def _level(total_nutrient: int) -> int:
    for index in range(len(LEVEL_NUTRIENTS) - 1, -1, -1):
        if total_nutrient >= LEVEL_NUTRIENTS[index]:
            return index + 1
    return 1


def _skins(level: int) -> list[dict[str, object]]:
    return [{**skin, "unlocked": level >= int(cast(int, skin["requiredLevel"]))} for skin in SKINS]


async def _today_nutrient(session: AsyncSession, couple_id: int) -> int:
    start = datetime.combine(date.today(), datetime.min.time())
    end = start + timedelta(days=1)
    result = await session.execute(
        select(TreeNutrientLog.nutrient_amount).where(
            TreeNutrientLog.couple_id == couple_id,
            TreeNutrientLog.create_time >= start,
            TreeNutrientLog.create_time < end,
        )
    )
    return sum(int(value) for value in result.scalars().all())


def _tree_payload(
    tree: CoupleTree, available_skins: list[dict[str, object]], today: int
) -> dict[str, object]:
    level = max(1, min(tree.level, len(LEVEL_NUTRIENTS)))
    current_base = LEVEL_NUTRIENTS[level - 1]
    next_base = LEVEL_NUTRIENTS[min(level, len(LEVEL_NUTRIENTS) - 1)]
    needed = next_base - current_base
    progress = (
        100
        if needed <= 0
        else min(100, max(0, round((tree.total_nutrient - current_base) * 100 / needed)))
    )
    return {
        "id": tree.id,
        "level": level,
        "levelName": LEVEL_NAMES[level - 1],
        "totalNutrient": tree.total_nutrient,
        "currentLevelNutrient": tree.current_level_nutrient,
        "nextLevelNutrient": needed,
        "progressPercent": progress,
        "skinId": tree.skin_id,
        "availableSkins": available_skins,
        "todayNutrient": today,
        "createTime": tree.create_time.isoformat() if tree.create_time else None,
    }


async def get_info(request: Request, session: AsyncSession, user_id: int) -> dict[str, object]:
    started = perf_counter()
    operation = "info"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    tree = await _get_or_create_tree(session, couple_id)
    await session.commit()
    await session.refresh(tree)
    payload = _tree_payload(tree, _skins(tree.level), await _today_nutrient(session, couple_id))
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def water(
    request: Request, session: AsyncSession, user_id: int, payload: WaterTreeRequest
) -> None:
    started = perf_counter()
    operation = "water"
    user = await _couple_user(request, session, user_id, operation, started)
    amount = payload.nutrient_amount if payload.nutrient_amount is not None else 10
    source_action = (payload.source_action or "manual_water").strip() or "manual_water"
    couple_id = _couple_id(user)
    await add_nutrient_in_transaction(
        session,
        couple_id,
        user_id,
        amount,
        source_action,
        payload.remark,
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )


async def add_nutrient_in_transaction(
    session: AsyncSession,
    couple_id: int,
    user_id: int,
    amount: int,
    source_action: str,
    remark: str | None,
) -> None:
    """Add tree nutrient without committing, for transaction-coupled rewards."""
    tree = await _get_or_create_tree(session, couple_id)
    await session.execute(
        update(CoupleTree)
        .where(CoupleTree.id == tree.id)
        .values(
            total_nutrient=CoupleTree.total_nutrient + amount,
            current_level_nutrient=CoupleTree.current_level_nutrient + amount,
        )
    )
    fresh_tree = await session.scalar(
        select(CoupleTree).where(CoupleTree.id == tree.id).execution_options(populate_existing=True)
    )
    if fresh_tree is None:
        raise BusinessError(8701, "爱心树不存在")
    next_level = _level(int(fresh_tree.total_nutrient))
    current_base = LEVEL_NUTRIENTS[next_level - 1]
    await session.execute(
        update(CoupleTree)
        .where(CoupleTree.id == fresh_tree.id)
        .values(
            level=next_level,
            current_level_nutrient=int(fresh_tree.total_nutrient) - current_base,
        )
    )
    session.add(
        TreeNutrientLog(
            couple_id=couple_id,
            user_id=user_id,
            nutrient_amount=amount,
            source_action=source_action,
            remark=remark,
        )
    )


async def nutrient_logs(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "nutrient_logs"
    user = await _couple_user(request, session, user_id, operation, started)
    result = await session.execute(
        select(TreeNutrientLog)
        .where(TreeNutrientLog.couple_id == user.couple_id)
        .order_by(TreeNutrientLog.create_time.desc(), TreeNutrientLog.id.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    user_ids = {item.user_id for item in logs}
    users = {}
    if user_ids:
        users = {
            item.id: item
            for item in (await session.execute(select(User).where(User.id.in_(user_ids))))
            .scalars()
            .all()
        }
    payload: list[dict[str, object | None]] = [
        {
            "id": item.id,
            "userId": item.user_id,
            "userName": users[item.user_id].nick_name if item.user_id in users else None,
            "userAvatar": users[item.user_id].avatar_url if item.user_id in users else None,
            "nutrientAmount": item.nutrient_amount,
            "sourceAction": item.source_action,
            "sourceActionName": ACTION_NAMES.get(item.source_action, item.source_action),
            "remark": item.remark,
            "createTime": item.create_time.isoformat() if item.create_time else None,
        }
        for item in logs
    ]
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def skins(request: Request, session: AsyncSession, user_id: int) -> list[dict[str, object]]:
    started = perf_counter()
    operation = "skins"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    tree = await _get_or_create_tree(session, couple_id)
    await session.commit()
    payload = _skins(tree.level)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return payload


async def change_skin(request: Request, session: AsyncSession, user_id: int, skin_id: str) -> None:
    started = perf_counter()
    operation = "change_skin"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = _couple_id(user)
    tree = await _get_or_create_tree(session, couple_id)
    skin = SKIN_BY_ID.get(skin_id.strip())
    if skin is None:
        await session.rollback()
        await _fail(request, operation, started, 9001, "该皮肤尚未解锁")
    required_level = int(cast(int, skin["requiredLevel"]))
    if tree.level < required_level:
        await session.rollback()
        await _fail(request, operation, started, 9001, "该皮肤尚未解锁")
    tree.skin_id = str(skin["skinId"])
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
