from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import BindCoupleRequest, GenerateCodeRequest, UnbindRequest
from app.services import couple as couple_service

router = APIRouter(prefix="/couple", tags=["情侣模块"])


@router.post("/generateCode")
async def generate_code(
    request: Request,
    payload: GenerateCodeRequest | None = None,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    code = await couple_service.generate_code(request, session, user_id, payload)
    return {"code": 200, "message": "情侣码生成成功", "data": code}


@router.post("/bind")
async def bind(
    request: Request,
    payload: BindCoupleRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "绑定成功",
        "data": await couple_service.bind(request, session, user_id, payload),
    }


@router.get("/info")
async def info(
    user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.get_info(session, user_id),
    }


@router.get("/home")
async def home(
    user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.get_home(session, user_id),
    }


@router.post("/unbind/apply")
async def apply_unbind(
    request: Request,
    payload: UnbindRequest | None = None,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_service.apply_unbind(request, session, user_id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/unbind/confirm")
async def confirm_unbind(
    request: Request,
    couple_id: int = Query(..., alias="coupleId"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_service.confirm_unbind(request, session, user_id, couple_id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/unbind/reject")
async def reject_unbind(
    request: Request,
    couple_id: int = Query(..., alias="coupleId"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_service.reject_unbind(request, session, user_id, couple_id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/validateCode")
async def validate_code(
    request: Request,
    couple_code: str = Query(..., alias="coupleCode"),
    user_id: int = Depends(current_user_id),
) -> dict[str, object]:
    del user_id
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.validate_code(request, couple_code),
    }


@router.get("/loveTimer")
async def love_timer(
    user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.love_timer(session, user_id),
    }


@router.get("/recoverable")
async def recoverable(
    user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.recoverable(session, user_id),
    }


@router.post("/recover")
async def recover(
    request: Request,
    record_id: int = Query(..., alias="recordId"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "数据恢复成功",
        "data": await couple_service.recover(request, session, user_id, record_id),
    }


@router.get("/codeInfo")
async def code_info(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_service.code_info(request, session, user_id),
    }


@router.post("/refreshCode")
async def refresh_code(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "情侣码已刷新",
        "data": await couple_service.refresh_code(request, session, user_id),
    }
