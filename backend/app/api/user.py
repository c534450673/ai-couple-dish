from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims, current_token_claims, current_user_id
from app.db.session import get_session
from app.schemas.business import PhoneLoginRequest, UpdateUserRequest, WechatLoginRequest
from app.services import user as user_service

router = APIRouter(prefix="/user", tags=["用户模块"])


@router.post("/login")
async def wechat_login(
    request: Request,
    payload: WechatLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await user_service.wechat_login(request, session, payload),
    }


@router.post("/register")
async def register(
    request: Request,
    payload: PhoneLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await user_service.register_by_phone(request, session, payload),
    }


@router.post("/sendCode")
async def send_code(request: Request, phone: str = Query(...)) -> dict[str, object | None]:
    await user_service.send_verify_code(request, phone)
    return {"code": 200, "message": "验证码发送成功", "data": None}


@router.post("/phoneLogin")
async def phone_login(
    request: Request,
    payload: PhoneLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await user_service.phone_login(request, session, payload),
    }


@router.get("/info")
async def info(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await user_service.get_user_info(request, session, user_id),
    }


@router.put("/update")
async def update(
    request: Request,
    payload: UpdateUserRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await user_service.update_user_info(request, session, user_id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/logout")
async def logout(
    request: Request,
    claims: TokenClaims = Depends(current_token_claims),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await user_service.logout(request, session, claims.user_id, claims)
    return {"code": 200, "message": "操作成功", "data": None}
