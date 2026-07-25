from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import CoupleRankClaimRequest
from app.services import couple_rank as couple_rank_service

router = APIRouter(prefix="/coupleRank", tags=["情侣段位模块"])


@router.get("/info")
async def info(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_rank_service.get_rank_info(request, session, user_id),
    }


@router.get("/rankList")
async def rank_list(
    request: Request,
    limit: int = Query(default=100, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_rank_service.get_rank_list(request, session, user_id, limit),
    }


@router.get("/rewards")
async def rewards(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_rank_service.get_rewards(request, session, user_id),
    }


@router.post("/claim/{rank}")
async def claim(
    request: Request,
    rank: str = Path(min_length=1, max_length=32),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_rank_service.claim_reward(
        request, session, user_id, CoupleRankClaimRequest(rank=rank)
    )
    return {"code": 200, "message": "奖励领取成功", "data": None}
