from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import ChallengeCheckinRequest, ChallengeCreateRequest
from app.services import challenge as service

router = APIRouter(prefix="/challenge", tags=["打卡挑战模块"])


@router.post("/create")
async def create(
    request: Request,
    body: ChallengeCreateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.create(request, session, user_id, body),
    }


@router.post("/accept/{challengeId}")
async def accept(
    request: Request,
    challenge_id: int = Path(alias="challengeId", gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.accept(request, session, user_id, challenge_id)
    return {"code": 200, "message": "接受成功", "data": None}


@router.post("/reject/{challengeId}")
async def reject(
    request: Request,
    challenge_id: int = Path(alias="challengeId", gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.reject(request, session, user_id, challenge_id)
    return {"code": 200, "message": "已拒绝", "data": None}


@router.post("/cancel/{challengeId}")
async def cancel(
    request: Request,
    challenge_id: int = Path(alias="challengeId", gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.cancel(request, session, user_id, challenge_id)
    return {"code": 200, "message": "已取消", "data": None}


@router.post("/checkin")
async def checkin(
    request: Request,
    body: ChallengeCheckinRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.checkin(request, session, user_id, body),
    }


@router.get("/detail/{challengeId}")
async def detail(
    request: Request,
    challenge_id: int = Path(alias="challengeId", gt=0),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.detail(request, session, user_id, challenge_id),
    }


@router.get("/list")
async def list_challenges(
    request: Request,
    status: int | None = Query(default=None, ge=0, le=3),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.list_challenges(request, session, user_id, status),
    }


@router.get("/checkin-records/{challengeId}")
async def checkin_records(
    request: Request,
    challenge_id: int = Path(alias="challengeId", gt=0),
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.checkin_records(
            request, session, user_id, challenge_id, page_num, page_size
        ),
    }


@router.get("/pending")
async def pending(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.pending(request, session, user_id),
    }
