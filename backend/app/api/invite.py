from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import invite as service

router = APIRouter(prefix="/invite", tags=["邀请返利模块"])


@router.get("/code")
async def code(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.code(request, session, user_id),
    }


@router.post("/use")
async def use(
    request: Request,
    invite_code: str = Query(alias="inviteCode", max_length=16),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.use(request, session, user_id, invite_code)
    return {"code": 200, "message": "邀请码使用成功", "data": None}


@router.get("/referrals")
async def referrals(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.referrals(request, session, user_id, limit),
    }


@router.get("/stats")
async def stats(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.stats(request, session, user_id),
    }


@router.get("/rank")
async def rank(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    del user_id
    return {"code": 200, "message": "操作成功", "data": await service.rank(request, session, limit)}


@router.get("/validate")
async def validate(
    request: Request,
    invite_code: str = Query(alias="inviteCode", max_length=16),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    del user_id
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.validate(request, session, invite_code),
    }


@router.get("/info/{inviteCode}")
async def info(
    request: Request,
    inviteCode: str,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    del user_id
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.info(request, session, inviteCode),
    }
