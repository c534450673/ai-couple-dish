from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import MenuRequest
from app.services import menu as menu_service

router = APIRouter(prefix="/menu", tags=["菜单模块"])


@router.get("/list")
async def list_menus(
    request: Request,
    status: int | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=128),
    dish_category: str | None = Query(default=None, alias="dishCategory", max_length=64),
    min_price: Decimal | None = Query(default=None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    min_rating: int | None = Query(default=None, alias="minRating", ge=1, le=5),
    sort_by: str | None = Query(default=None, alias="sortBy"),
    sort_order: str | None = Query(default=None, alias="sortOrder"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await menu_service.list_menus(
            request,
            session,
            user_id,
            status=status,
            keyword=keyword,
            dish_category=dish_category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        ),
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
        "data": await menu_service.get_detail(request, session, user_id, id),
    }


@router.post("/add")
async def add(
    request: Request,
    payload: MenuRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "菜单添加成功",
        "data": await menu_service.add(request, session, user_id, payload),
    }


@router.put("/update/{id}")
async def update(
    request: Request,
    id: int,
    payload: MenuRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.update_menu(request, session, user_id, id, payload)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/delete/{id}")
async def delete(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.delete_menu(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/recover/{id}")
async def recover(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.recover_menu(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/like/{id}")
async def like(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.like(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/unlike/{id}")
async def unlike(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.unlike(request, session, user_id, id)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/favorite/{id}")
async def favorite(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.set_favorite(request, session, user_id, id, True)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/unfavorite/{id}")
async def unfavorite(
    request: Request,
    id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await menu_service.set_favorite(request, session, user_id, id, False)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/stats")
async def stats(
    request: Request,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await menu_service.stats(request, session, user_id),
    }


@router.get("/nearby")
async def nearby(
    request: Request,
    latitude: Decimal = Query(..., ge=-90, le=90),
    longitude: Decimal = Query(..., ge=-180, le=180),
    radius_meters: int = Query(default=5000, alias="radiusMeters", ge=1, le=100_000),
    status: int | None = Query(default=None, ge=0, le=2),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await menu_service.nearby(
            request, session, user_id, latitude, longitude, radius_meters, status
        ),
    }


@router.get("/map")
async def map_items(
    request: Request,
    center_lat: Decimal | None = Query(default=None, alias="centerLat", ge=-90, le=90),
    center_lng: Decimal | None = Query(default=None, alias="centerLng", ge=-180, le=180),
    zoom_level: int = Query(default=10, alias="zoomLevel", ge=1, le=22),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await menu_service.map_items(
            request, session, user_id, center_lat, center_lng, zoom_level
        ),
    }
