from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import DeepQaSubmitRequest
from app.services import deep_qa as service

router = APIRouter(prefix="/deepQa", tags=["情侣深度问答模块"])


@router.get("/current")
async def current(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.current(request, session, user_id),
    }


@router.get("/week/{weekNumber}")
async def week(
    request: Request,
    week_number: int = Path(alias="weekNumber", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.week(request, session, user_id, week_number),
    }


@router.post("/submit")
async def submit(
    request: Request,
    body: DeepQaSubmitRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.submit(request, session, user_id, body.question_id, body.answer_text)
    return {"code": 200, "message": "答案提交成功", "data": None}


@router.post("/reveal/{questionId}")
async def reveal(
    request: Request,
    question_id: int = Path(alias="questionId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.reveal(request, session, user_id, question_id),
    }


@router.get("/progress")
async def progress(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.progress(request, session, user_id),
    }


@router.get("/history")
async def history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.history(request, session, user_id, limit),
    }


@router.post("/skip")
async def skip(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.skip(request, session, user_id)
    return {"code": 200, "message": "操作成功", "data": None}
