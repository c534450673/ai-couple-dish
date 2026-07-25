from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import NoteRequest, NoteUpdateRequest
from app.services import note as note_service

router = APIRouter(prefix="/note", tags=["笔记模块"])


@router.get("/list")
async def list_notes(
    request: Request,
    anniversary_id: int | None = Query(default=None, alias="anniversaryId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await note_service.list_notes(request, session, user_id, anniversary_id),
    }


@router.get("/detail/{id}")
async def detail(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await note_service.detail(request, session, user_id, id),
    }


@router.post("/add")
async def add(
    request: Request,
    payload: NoteRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "笔记添加成功",
        "data": await note_service.add(request, session, user_id, payload),
    }


@router.put("/update/{id}")
async def update(
    request: Request,
    id: int,
    payload: NoteUpdateRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await note_service.update_note(request, session, user_id, id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await note_service.delete_note(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/like/{id}")
async def like(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await note_service.like(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/unlike/{id}")
async def unlike(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await note_service.unlike(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/comment/{id}")
async def comment(
    request: Request,
    id: int,
    content: str = Query(..., min_length=1, max_length=5000),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await note_service.comment(request, session, user_id, id, content)
    return {"code": 200, "message": "操作成功", "data": None}
