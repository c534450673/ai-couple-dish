from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, Any]:
    """返回进程存活状态，不访问外部依赖。"""
    return {"code": 200, "message": "操作成功", "data": {"status": "UP"}}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """仅以聚合状态报告就绪情况，避免暴露依赖实现细节。"""
    check: Callable[[], Awaitable[dict[str, bool]]] = request.app.state.readiness
    states = await check()
    is_ready = all(states.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "code": 200 if is_ready else 503,
            "message": "操作成功" if is_ready else "服务暂不可用",
            "data": {"status": "UP" if is_ready else "DOWN"},
        },
    )
