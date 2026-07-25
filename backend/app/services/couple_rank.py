from time import perf_counter
from typing import Never, TypedDict, cast

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import CoupleRank, User
from app.schemas.business import CoupleRankClaimRequest

logger = structlog.get_logger()


class RankConfig(TypedDict):
    rank: str
    name: str
    icon: str
    minScore: int
    maxScore: int
    description: str


RANK_CONFIGS: tuple[RankConfig, ...] = (
    {
        "rank": "bronze",
        "name": "青铜",
        "icon": "🥉",
        "minScore": 0,
        "maxScore": 100,
        "description": "初识阶段",
    },
    {
        "rank": "silver",
        "name": "白银",
        "icon": "🥈",
        "minScore": 100,
        "maxScore": 300,
        "description": "相识阶段",
    },
    {
        "rank": "gold",
        "name": "黄金",
        "icon": "🥇",
        "minScore": 300,
        "maxScore": 600,
        "description": "相知阶段",
    },
    {
        "rank": "platinum",
        "name": "铂金",
        "icon": "💎",
        "minScore": 600,
        "maxScore": 1000,
        "description": "相恋阶段",
    },
    {
        "rank": "diamond",
        "name": "钻石",
        "icon": "💍",
        "minScore": 1000,
        "maxScore": 1500,
        "description": "相爱阶段",
    },
    {
        "rank": "king",
        "name": "王者",
        "icon": "👑",
        "minScore": 1500,
        "maxScore": 2_147_483_647,
        "description": "相伴一生",
    },
)
RANK_BY_NAME: dict[str, RankConfig] = {item["rank"]: item for item in RANK_CONFIGS}


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "couple_rank",
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


async def _user(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = cast(
        User | None,
        await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0)),
    )
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


async def _couple_user(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = await _user(request, session, user_id, operation, started)
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return user


async def _get_or_create_rank(session: AsyncSession, couple_id: int) -> CoupleRank:
    rank = cast(
        CoupleRank | None,
        await session.scalar(select(CoupleRank).where(CoupleRank.couple_id == couple_id)),
    )
    if rank is not None:
        return rank

    candidate = CoupleRank(
        couple_id=couple_id,
        current_rank="bronze",
        rank_score=0,
        consecutive_interaction_days=0,
        temperature_score=60,
        demotion_warning=0,
    )
    session.add(candidate)
    try:
        await session.flush()
    except IntegrityError:
        # t_couple_rank.couple_id is unique. A concurrent first read may win the
        # insert; discard this transaction and read the committed winner.
        await session.rollback()
        rank = cast(
            CoupleRank | None,
            await session.scalar(select(CoupleRank).where(CoupleRank.couple_id == couple_id)),
        )
        if rank is None:
            raise
        return rank
    return candidate


def _rank_payload(item: CoupleRank) -> dict[str, object | None]:
    current = RANK_BY_NAME.get(item.current_rank, RANK_CONFIGS[0])
    current_min = int(current["minScore"])
    next_item = next(
        (candidate for candidate in RANK_CONFIGS if int(candidate["minScore"]) > current_min),
        None,
    )
    score = max(0, int(item.rank_score or 0))
    if next_item is None:
        next_score = None
        progress = 100
    else:
        next_score = int(next_item["minScore"])
        progress = min(100, max(0, round((score - current_min) * 100 / (next_score - current_min))))

    rank_list = []
    for config in RANK_CONFIGS:
        minimum = int(config["minScore"])
        rank_list.append(
            {
                "rank": config["rank"],
                "name": config["name"],
                "icon": config["icon"],
                "minScore": minimum,
                "maxScore": config["maxScore"],
                "description": config["description"],
                "unlocked": score >= minimum,
            }
        )
    temperature = max(0, min(100, int(item.temperature_score or 0)))
    temperature_level = (
        "火热"
        if temperature >= 90
        else "温暖"
        if temperature >= 70
        else "适中"
        if temperature >= 50
        else "微凉"
        if temperature >= 30
        else "冷淡"
    )
    return {
        "id": item.id,
        "currentRank": item.current_rank,
        "rankName": current["name"],
        "rankIcon": current["icon"],
        "rankScore": item.rank_score,
        "currentRankMinScore": current_min,
        "nextRankScore": next_score,
        "progressPercent": progress,
        "consecutiveInteractionDays": item.consecutive_interaction_days,
        "temperatureScore": item.temperature_score,
        "temperatureLevel": temperature_level,
        "promotionDate": item.promotion_date.isoformat() if item.promotion_date else None,
        "demotionWarning": bool(item.demotion_warning),
        "rankList": rank_list,
    }


def _reward_payload(item: CoupleRank) -> list[dict[str, object]]:
    score = max(0, int(item.rank_score or 0))
    return [
        {
            "rank": config["rank"],
            "rewardType": "skin",
            "rewardContent": f"{config['name']}专属头像框",
            "claimed": score >= int(config["minScore"]),
        }
        for config in RANK_CONFIGS
    ]


async def get_rank_info(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "info"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = cast(int, user.couple_id)
    rank = await _get_or_create_rank(session, couple_id)
    await session.commit()
    payload = _rank_payload(rank)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return payload


async def get_rank_list(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "rank_list"
    await _user(request, session, user_id, operation, started)
    rows = await session.execute(
        select(CoupleRank).order_by(CoupleRank.rank_score.desc(), CoupleRank.id.asc()).limit(limit)
    )
    result = [_rank_payload(item) for item in rows.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return result


async def get_rewards(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object]]:
    started = perf_counter()
    operation = "rewards"
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = cast(int, user.couple_id)
    rank = await _get_or_create_rank(session, couple_id)
    await session.commit()
    result = _reward_payload(rank)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return result


async def claim_reward(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: CoupleRankClaimRequest,
) -> None:
    started = perf_counter()
    operation = "claim"
    rank_name = payload.rank.strip().lower()
    config = RANK_BY_NAME.get(rank_name)
    if config is None:
        await _fail(request, operation, started, 9001, "段位参数无效")
    user = await _couple_user(request, session, user_id, operation, started)
    couple_id = cast(int, user.couple_id)
    rank = await _get_or_create_rank(session, couple_id)
    if int(rank.rank_score or 0) < config["minScore"]:
        await session.rollback()
        await _fail(request, operation, started, 8803, "尚未达到该段位")
    # No reward table exists in the Spring schema. Treat this operation as a
    # successful idempotent acknowledgement; repeated claims do not mutate data.
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
