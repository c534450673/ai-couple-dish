import json
import math
from datetime import datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import CoupleMenu, User
from app.schemas.business import MenuRequest

logger = structlog.get_logger()


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "menu",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


async def _couple_id(session: AsyncSession, user_id: int) -> int:
    user = await _user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    return user.couple_id


def _decode_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [item.strip() for item in value.split(",") if item.strip()]
    return decoded if isinstance(decoded, list) else []


def _encode_list(value: list[Any] | None) -> str | None:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value else None


def _number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    lat_delta = math.radians(lat2 - lat1)
    lng_delta = math.radians(lng2 - lng1)
    value = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(lng_delta / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _radius_degrees(zoom_level: int) -> float:
    if zoom_level < 10:
        return 20.0
    return {
        10: 10.0,
        11: 5.0,
        12: 2.0,
        13: 1.0,
        14: 0.5,
        15: 0.2,
        16: 0.1,
        17: 0.05,
        18: 0.02,
        19: 0.01,
    }.get(zoom_level, 0.005)


def _status_name(status: int | None) -> str:
    return {0: "想去", 1: "去过", 2: "种草"}.get(status or 0, "共同地点")


async def _payload(
    session: AsyncSession, item: CoupleMenu, *, distance: float | None = None
) -> dict[str, object | None]:
    creator = await session.scalar(select(User).where(User.id == item.creator_id))
    photo_urls = _decode_list(item.photo_urls)
    return {
        "id": item.id,
        "coupleId": item.couple_id,
        "creatorId": item.creator_id,
        "creatorName": creator.nick_name if creator else None,
        "creatorAvatar": creator.avatar_url if creator else None,
        "restaurantName": item.restaurant_name,
        "dishName": item.dish_name,
        "dishCategory": item.dish_category,
        "price": _number(item.price),
        "location": item.location,
        "latitude": _number(item.latitude),
        "longitude": _number(item.longitude),
        "note": item.note,
        "rating": item.rating,
        "eaterIds": [int(value) for value in _decode_list(item.eater_ids) if str(value).isdigit()],
        "eaterNames": None,
        "eatenDate": item.eaten_date.isoformat() if item.eaten_date else None,
        "status": item.status,
        "statusName": _status_name(item.status),
        "likeCount": item.like_count,
        "isFavorite": bool(item.is_favorite),
        "photoUrls": photo_urls,
        "photoCount": item.photo_count or len(photo_urls),
        "anniversaryId": item.anniversary_id,
        "createTime": item.create_time.isoformat() if item.create_time else None,
        "isLiked": False,
        "distance": distance,
    }


async def list_menus(
    request: Request,
    session: AsyncSession,
    user_id: int,
    *,
    status: int | None = None,
    keyword: str | None = None,
    dish_category: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    min_rating: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, object]:
    started = perf_counter()
    if page < 1 or page_size < 1 or page_size > 100:
        raise BusinessError(9001, "参数无效")
    couple_id = await _couple_id(session, user_id)
    conditions = [CoupleMenu.couple_id == couple_id, CoupleMenu.is_deleted == 0]
    if status is not None:
        conditions.append(CoupleMenu.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        conditions.append(
            or_(CoupleMenu.restaurant_name.like(pattern), CoupleMenu.dish_name.like(pattern))
        )
    if dish_category:
        conditions.append(CoupleMenu.dish_category == dish_category)
    if min_price is not None:
        conditions.append(CoupleMenu.price >= min_price)
    if max_price is not None:
        conditions.append(CoupleMenu.price <= max_price)
    if min_rating is not None:
        conditions.append(CoupleMenu.rating >= min_rating)

    total = int((await session.scalar(select(func.count(CoupleMenu.id)).where(*conditions))) or 0)
    order_column = {
        "rating": CoupleMenu.rating,
        "likeCount": CoupleMenu.like_count,
        "time": CoupleMenu.create_time,
    }.get(sort_by or "time", CoupleMenu.create_time)
    order_clause = (
        order_column.asc() if (sort_order or "desc").lower() == "asc" else order_column.desc()
    )
    result = await session.execute(
        select(CoupleMenu)
        .where(*conditions)
        .order_by(order_clause, CoupleMenu.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [await _payload(session, item) for item in result.scalars().all()]
    total_pages = math.ceil(total / page_size) if total else 0
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "list", "success", started),
    )
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": total_pages,
        "list": items,
        "hasMore": page < total_pages,
    }


async def get_detail(
    request: Request, session: AsyncSession, user_id: int, menu_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    item = await session.scalar(
        select(CoupleMenu).where(CoupleMenu.id == menu_id, CoupleMenu.is_deleted == 0)
    )
    if item is None:
        raise BusinessError(3001, "菜单不存在")
    if item.couple_id != couple_id:
        raise BusinessError(3002, "无权访问该菜单")
    result = await _payload(session, item)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "detail", "success", started)
    )
    return result


async def add(request: Request, session: AsyncSession, user_id: int, payload: MenuRequest) -> int:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    item = CoupleMenu(
        couple_id=couple_id,
        creator_id=user_id,
        restaurant_name=payload.restaurant_name.strip(),
        dish_name=payload.dish_name,
        dish_category=payload.dish_category,
        price=payload.price,
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
        note=payload.note,
        rating=payload.rating,
        eater_ids=_encode_list(payload.eater_ids),
        eaten_date=payload.eaten_date,
        status=payload.status if payload.status is not None else 0,
        photo_urls=_encode_list(payload.photo_urls),
        photo_count=len(payload.photo_urls or []),
        anniversary_id=payload.anniversary_id,
        is_deleted=0,
    )
    session.add(item)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "add", "success", started)
    )
    return item.id


async def _owned_item(session: AsyncSession, user_id: int, menu_id: int) -> CoupleMenu:
    couple_id = await _couple_id(session, user_id)
    item = await session.scalar(select(CoupleMenu).where(CoupleMenu.id == menu_id))
    if item is None or item.is_deleted:
        raise BusinessError(3001, "菜单不存在")
    if item.couple_id != couple_id:
        raise BusinessError(3002, "无权操作该菜单")
    return item


def _apply_payload(item: CoupleMenu, payload: MenuRequest) -> None:
    item.restaurant_name = payload.restaurant_name.strip()
    item.dish_name = payload.dish_name
    item.dish_category = payload.dish_category
    item.price = payload.price
    item.location = payload.location
    item.latitude = payload.latitude
    item.longitude = payload.longitude
    item.note = payload.note
    item.rating = payload.rating
    if payload.eater_ids is not None:
        item.eater_ids = _encode_list(payload.eater_ids)
    item.eaten_date = payload.eaten_date
    if payload.status is not None:
        item.status = payload.status
    if payload.photo_urls is not None:
        item.photo_urls = _encode_list(payload.photo_urls)
        item.photo_count = len(payload.photo_urls)
    if payload.anniversary_id is not None:
        item.anniversary_id = payload.anniversary_id


async def update_menu(
    request: Request, session: AsyncSession, user_id: int, menu_id: int, payload: MenuRequest
) -> None:
    started = perf_counter()
    item = await _owned_item(session, user_id, menu_id)
    _apply_payload(item, payload)
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "update", "success", started)
    )


async def delete_menu(request: Request, session: AsyncSession, user_id: int, menu_id: int) -> None:
    started = perf_counter()
    item = await _owned_item(session, user_id, menu_id)
    item.is_deleted = 1
    item.delete_time = datetime.now()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "delete", "success", started)
    )


async def recover_menu(request: Request, session: AsyncSession, user_id: int, menu_id: int) -> None:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    item = await session.scalar(select(CoupleMenu).where(CoupleMenu.id == menu_id))
    if item is None:
        raise BusinessError(3001, "菜单不存在")
    if item.couple_id != couple_id:
        raise BusinessError(3002, "无权操作该菜单")
    item.is_deleted = 0
    item.delete_time = None
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "recover", "success", started)
    )


async def _change_counter(
    request: Request,
    session: AsyncSession,
    user_id: int,
    menu_id: int,
    operation: str,
    increment: int,
) -> None:
    started = perf_counter()
    item = await _owned_item(session, user_id, menu_id)
    conditions = [CoupleMenu.id == item.id, CoupleMenu.is_deleted == 0]
    if increment < 0:
        conditions.append(CoupleMenu.like_count > 0)
    await session.execute(
        update(CoupleMenu).where(*conditions).values(like_count=CoupleMenu.like_count + increment)
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )


async def like(request: Request, session: AsyncSession, user_id: int, menu_id: int) -> None:
    await _change_counter(request, session, user_id, menu_id, "like", 1)


async def unlike(request: Request, session: AsyncSession, user_id: int, menu_id: int) -> None:
    await _change_counter(request, session, user_id, menu_id, "unlike", -1)


async def set_favorite(
    request: Request, session: AsyncSession, user_id: int, menu_id: int, favorite: bool
) -> None:
    started = perf_counter()
    item = await _owned_item(session, user_id, menu_id)
    item.is_favorite = 1 if favorite else 0
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "favorite" if favorite else "unfavorite", "success", started),
    )


async def stats(request: Request, session: AsyncSession, user_id: int) -> dict[str, int]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    common = [CoupleMenu.couple_id == couple_id, CoupleMenu.is_deleted == 0]
    total = int((await session.scalar(select(func.count(CoupleMenu.id)).where(*common))) or 0)
    want = int(
        (
            await session.scalar(
                select(func.count(CoupleMenu.id)).where(*common, CoupleMenu.status == 0)
            )
        )
        or 0
    )
    visited = int(
        (
            await session.scalar(
                select(func.count(CoupleMenu.id)).where(*common, CoupleMenu.status == 1)
            )
        )
        or 0
    )
    seeded = int(
        (
            await session.scalar(
                select(func.count(CoupleMenu.id)).where(*common, CoupleMenu.status == 2)
            )
        )
        or 0
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "stats", "success", started)
    )
    return {
        "totalCount": total,
        "wantToGoCount": want,
        "visitedCount": visited,
        "seededCount": seeded,
    }


async def _map_items(
    session: AsyncSession,
    couple_id: int,
    center_lat: Decimal | None = None,
    center_lng: Decimal | None = None,
    radius_meters: int | None = None,
    radius_degrees: float | None = None,
) -> list[dict[str, object | None]]:
    result = await session.execute(
        select(CoupleMenu)
        .where(CoupleMenu.couple_id == couple_id, CoupleMenu.is_deleted == 0)
        .order_by(CoupleMenu.create_time.desc(), CoupleMenu.id.desc())
    )
    items: list[dict[str, object | None]] = []
    for item in result.scalars().all():
        if item.latitude is None or item.longitude is None:
            continue
        distance: float | None = None
        if center_lat is not None and center_lng is not None:
            lat_delta = abs(float(item.latitude) - float(center_lat))
            lng_delta = abs(float(item.longitude) - float(center_lng))
            if radius_degrees is not None and (
                lat_delta > radius_degrees or lng_delta > radius_degrees
            ):
                continue
            distance = _distance_meters(
                float(center_lat),
                float(center_lng),
                float(item.latitude),
                float(item.longitude),
            )
            if radius_meters is not None and distance > radius_meters:
                continue
        items.append(await _payload(session, item, distance=distance))
    return items


async def nearby(
    request: Request,
    session: AsyncSession,
    user_id: int,
    latitude: Decimal,
    longitude: Decimal,
    radius_meters: int,
    status: int | None,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    items = await _map_items(session, couple_id, latitude, longitude, radius_meters)
    if status is not None:
        items = [item for item in items if item["status"] == status]
    items.sort(key=lambda item: item["distance"] if isinstance(item["distance"], float) else 0.0)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "nearby", "success", started)
    )
    return items


async def map_items(
    request: Request,
    session: AsyncSession,
    user_id: int,
    center_lat: Decimal | None,
    center_lng: Decimal | None,
    zoom_level: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    radius_degrees = (
        _radius_degrees(zoom_level) if center_lat is not None and center_lng is not None else None
    )
    items = await _map_items(
        session,
        couple_id,
        center_lat,
        center_lng,
        radius_degrees=radius_degrees,
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "map", "success", started)
    )
    return items
