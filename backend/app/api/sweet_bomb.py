from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import sweet_bomb as service

router = APIRouter(prefix="/sweetBomb", tags=["随机甜蜜炸弹模块"])


@router.post("/generate")
async def generate(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "甜蜜炸弹已发送",
        "data": await service.generate(request, session, user_id),
    }


@router.get("/unread")
async def unread(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.unread(request, session, user_id),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.detail(request, session, user_id, id),
    }


@router.post("/read/{id}")
async def mark_read(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.mark_read(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/answer/{id}")
async def answer(
    request: Request,
    id: int,
    answer_content: str = Query(alias="answerContent"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.answer(request, session, user_id, id, answer_content)
    return {"code": 200, "message": "回答已发送", "data": None}


@router.get("/history")
async def history(
    request: Request,
    limit: int = Query(default=20),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.history(request, session, user_id, limit),
    }


@router.get("/unread/count")
async def unread_count(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.unread_count(request, session, user_id),
    }
