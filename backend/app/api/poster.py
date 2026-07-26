from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.poster import PosterGenerateRequest
from app.services import poster as poster_service

router = APIRouter(prefix="/poster", tags=["海报模块"])


@router.get("/templates")
async def templates(
    request: Request,
    poster_type: str | None = Query(None, alias="posterType"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    data = await poster_service.get_templates(request, session, user_id, poster_type)
    return {"code": 200, "message": "操作成功", "data": data}


@router.post("/generate")
async def generate(
    request: Request,
    payload: PosterGenerateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    data = await poster_service.generate(request, session, user_id, payload)
    return {"code": 200, "message": "海报生成成功", "data": data}


@router.get("/list")
async def list_posters(
    request: Request,
    poster_type: str | None = Query(None, alias="posterType"),
    limit: int = Query(20),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    data = await poster_service.list_posters(request, session, user_id, poster_type, limit)
    return {"code": 200, "message": "操作成功", "data": data}


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    data = await poster_service.detail(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": data}


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await poster_service.delete(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/share/{id}")
async def share(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    data = await poster_service.share(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": data}
