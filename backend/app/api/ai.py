from collections.abc import AsyncIterator
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.core.errors import BusinessError
from app.db.session import get_session
from app.schemas.business import AiChatRequest, AiConfirmRequest, AiGenerateRequest
from app.services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["AI 助手"])
logger = structlog.get_logger()


async def _safe_stream(
    request: Request, session: AsyncSession, user_id: int, payload: AiChatRequest
) -> AsyncIterator[str]:
    try:
        async for event in ai_service.chat_stream(
            request, session, user_id, payload.message, payload.session_id
        ):
            yield event
    except BusinessError as error:
        await logger.awarning(
            "ai_stream_failed",
            module="ai",
            operation="chat_stream",
            result="error",
            errorCode=str(error.code),
        )
        yield ai_service._sse(
            "error", {"code": "AI_SERVICE_UNAVAILABLE", "message": "AI 流式响应失败"}
        )
    except Exception as error:
        await logger.aerror(
            "ai_stream_failed",
            module="ai",
            operation="chat_stream",
            result="error",
            errorCode=type(error).__name__,
        )
        yield ai_service._sse(
            "error", {"code": "AI_SERVICE_UNAVAILABLE", "message": "AI 流式响应失败"}
        )


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    payload: AiChatRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return StreamingResponse(
        _safe_stream(request, session, user_id, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/confirm")
async def confirm(
    request: Request,
    payload: AiConfirmRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await ai_service.confirm(request, session, user_id, payload.session_id),
    }


@router.post("/chat/reject")
async def reject(
    request: Request,
    payload: AiConfirmRequest,
    user_id: int = Depends(current_user_id),
) -> dict[str, Any]:
    await ai_service.reject(request, user_id, payload.session_id)
    return {"code": 200, "message": "已取消", "data": None}


@router.post("/generate")
async def generate(
    request: Request,
    payload: AiGenerateRequest,
    user_id: int = Depends(current_user_id),
) -> dict[str, Any]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await ai_service.generate(request, user_id, payload),
    }
