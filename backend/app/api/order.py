from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import CreateOrderRequest
from app.services import order as service

router = APIRouter(prefix="/order", tags=["订单模块"])


@router.post("/create")
async def create(
    request: Request,
    payload: CreateOrderRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.create(request, session, user_id, payload),
    }


@router.post("/cancel/{orderId}")
async def cancel(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.cancel(request, session, user_id, order_id)
    return {"code": 200, "message": "取消成功", "data": None}


@router.post("/accept/{orderId}")
async def accept(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.accept(request, session, user_id, order_id)
    return {"code": 200, "message": "接单成功", "data": None}


@router.post("/start-cooking/{orderId}")
async def start_cooking(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.start_cooking(request, session, user_id, order_id)
    return {"code": 200, "message": "开始制作", "data": None}


@router.post("/finish-cooking/{orderId}")
async def finish_cooking(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.finish_cooking(request, session, user_id, order_id)
    return {"code": 200, "message": "制作完成", "data": None}


@router.post("/complete/{orderId}")
async def complete(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.complete(request, session, user_id, order_id)
    return {"code": 200, "message": "订单完成", "data": None}


@router.post("/refund/{orderId}")
async def refund(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    reason: str | None = Query(default=None, max_length=512),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.refund(request, session, user_id, order_id, reason)
    return {"code": 200, "message": "退款申请已提交", "data": None}


@router.post("/confirm-refund/{orderId}")
async def confirm_refund(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await service.confirm_refund(request, session, user_id, order_id)
    return {"code": 200, "message": "已确认退款", "data": None}


@router.get("/detail/{orderId}")
async def detail(
    request: Request,
    order_id: int = Path(alias="orderId", ge=1),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.detail(request, session, user_id, order_id),
    }


async def _page_params(
    status: int | None = Query(default=None, ge=0, le=6),
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
) -> tuple[int | None, int, int]:
    return status, page_num, page_size


@router.get("/my-buy")
async def my_buy(
    request: Request,
    params: tuple[int | None, int, int] = Depends(_page_params),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    status, page_num, page_size = params
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.my_buy(request, session, user_id, status, page_num, page_size),
    }


@router.get("/my-sell")
async def my_sell(
    request: Request,
    params: tuple[int | None, int, int] = Depends(_page_params),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    status, page_num, page_size = params
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.my_sell(request, session, user_id, status, page_num, page_size),
    }


@router.get("/couple")
async def couple(
    request: Request,
    params: tuple[int | None, int, int] = Depends(_page_params),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    status, page_num, page_size = params
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.couple_orders(request, session, user_id, status, page_num, page_size),
    }


@router.get("/pending-count")
async def pending_count(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await service.pending_count(request, session, user_id),
    }
