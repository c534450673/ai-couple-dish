from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import WaterTreeRequest
from app.services import couple_tree as couple_tree_service

router = APIRouter(prefix="/coupleTree", tags=["情侣爱心树模块"])


@router.get("/info")
async def info(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_tree_service.get_info(request, session, user_id),
    }


@router.post("/water")
async def water(
    request: Request,
    payload: WaterTreeRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_tree_service.water(request, session, user_id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/nutrientLogs")
async def nutrient_logs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_tree_service.nutrient_logs(request, session, user_id, limit),
    }


@router.get("/skins")
async def skins(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await couple_tree_service.skins(request, session, user_id),
    }


@router.post("/skin/change")
async def change_skin(
    request: Request,
    skin_id: str = Query(min_length=1, max_length=64, alias="skinId"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await couple_tree_service.change_skin(request, session, user_id, skin_id)
    return {"code": 200, "message": "操作成功", "data": None}
