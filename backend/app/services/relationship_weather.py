"""关系气象站 FastAPI shadow 服务。"""

from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Never
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, CoupleMenu, DailyGreeting, RelationshipWeather, User

logger = structlog.get_logger()
BUSINESS_ZONE = ZoneInfo("Asia/Shanghai")

WEATHER_CONFIGS: tuple[tuple[str, str, str, str, int, int], ...] = (
    ("sunny", "晴天", "☀️", "关系很好，继续保持！", 80, 100),
    ("cloudy", "多云", "⛅", "关系稳定，可以多一些互动", 60, 79),
    ("rainy", "小雨", "🌧️", "需要多一些关心和互动", 40, 59),
    ("stormy", "暴风雨", "⛈️", "关系需要紧急关注！", 0, 39),
)


def _today() -> date:
    return datetime.now(BUSINESS_ZONE).date()


def _fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "relationship_weather",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(
    request: Request, operation: str, started: float, code: int, message: str
) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _couple_context(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
    *,
    lock: bool,
) -> Couple:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    statement = select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    if lock:
        statement = statement.with_for_update()
    couple = await session.scalar(statement)
    if couple is None or user.id not in {couple.user1_id, couple.user2_id}:
        await _fail(request, operation, started, 2006, "未绑定情侣关系")
    return couple


async def _get_or_create(
    session: AsyncSession, couple_id: int
) -> tuple[RelationshipWeather, bool]:
    weather = await session.scalar(
        select(RelationshipWeather)
        .where(RelationshipWeather.couple_id == couple_id)
        .order_by(RelationshipWeather.create_time.desc(), RelationshipWeather.id.desc())
        .limit(1)
        .with_for_update()
    )
    if weather is not None:
        return weather, False
    weather = RelationshipWeather(
        couple_id=couple_id,
        weather_level="sunny",
        interaction_score=60,
        days_since_last_interaction=0,
        temperature_score=60,
        alert_sent=0,
    )
    session.add(weather)
    await session.flush()
    await session.refresh(weather)
    return weather, True


def _weather_config(score: int) -> tuple[str, str, str, str, int, int]:
    for config in WEATHER_CONFIGS:
        if config[4] <= score <= config[5]:
            return config
    return WEATHER_CONFIGS[1]


def _weather_payload(weather: RelationshipWeather) -> dict[str, object | None]:
    config = next(
        (item for item in WEATHER_CONFIGS if item[0] == weather.weather_level),
        WEATHER_CONFIGS[1],
    )
    return {
        "id": weather.id,
        "weatherLevel": weather.weather_level,
        "weatherLevelName": config[1],
        "weatherIcon": config[2],
        "weatherDescription": config[3],
        "interactionScore": weather.interaction_score,
        "daysSinceLastInteraction": weather.days_since_last_interaction,
        "temperatureScore": weather.temperature_score,
        "hasAlert": weather.alert_sent == 1,
        "alertType": weather.alert_type,
        "alertMessage": "你们的关系需要一些关注，快去互动吧~" if weather.alert_sent == 1 else None,
        "createTime": weather.create_time.isoformat() if weather.create_time else None,
        "interactions": None,
        "suggestions": None,
    }


async def current(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "current"
    couple = await _couple_context(
        request, session, user_id, operation, started, lock=True
    )
    weather, created = await _get_or_create(session, couple.id)
    week_ago = _today() - timedelta(days=7)
    greeting_count = int(
        (
            await session.scalar(
                select(func.count(DailyGreeting.id)).where(
                    DailyGreeting.couple_id == couple.id,
                    DailyGreeting.is_deleted == 0,
                    DailyGreeting.greeting_date >= week_ago,
                )
            )
        )
        or 0
    )
    menu_count = int(
        (
            await session.scalar(
                select(func.count(CoupleMenu.id)).where(
                    CoupleMenu.couple_id == couple.id,
                    CoupleMenu.is_deleted == 0,
                    CoupleMenu.eaten_date.is_not(None),
                    CoupleMenu.eaten_date >= week_ago,
                )
            )
        )
        or 0
    )
    score = min(100, max(0, 40 + greeting_count * 3 + menu_count * 5))
    weather.interaction_score = score
    weather.weather_level = _weather_config(score)[0]
    weather.days_since_last_interaction = 0
    result = _weather_payload(weather)
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "created" if created else "success", started),
    )
    return result


async def interactions(
    request: Request, session: AsyncSession, user_id: int, limit: int
) -> list[dict[str, object]]:
    started = perf_counter()
    operation = "interactions"
    couple = await _couple_context(
        request, session, user_id, operation, started, lock=False
    )
    greeting_rows = await session.scalars(
        select(DailyGreeting)
        .where(DailyGreeting.couple_id == couple.id, DailyGreeting.is_deleted == 0)
        .order_by(DailyGreeting.create_time.desc(), DailyGreeting.id.desc())
        .limit(limit)
    )
    menu_rows = await session.scalars(
        select(CoupleMenu)
        .where(
            CoupleMenu.couple_id == couple.id,
            CoupleMenu.is_deleted == 0,
            CoupleMenu.eaten_date.is_not(None),
        )
        .order_by(CoupleMenu.create_time.desc(), CoupleMenu.id.desc())
        .limit(5)
    )
    records: list[dict[str, object]] = [
        {
            "type": "greeting",
            "description": "早安问候" if item.greeting_type == 1 else "晚安问候",
            "time": item.create_time.isoformat(),
            "score": 5,
        }
        for item in greeting_rows.all()
    ]
    records.extend(
        {
            "type": "date",
            "description": f"约会: {item.restaurant_name}",
            "time": item.create_time.isoformat(),
            "score": 10,
        }
        for item in menu_rows.all()
    )
    records.sort(key=lambda item: str(item["time"]), reverse=True)
    await logger.ainfo(
        "business_operation_completed", **_fields(request, operation, "success", started)
    )
    return records


async def suggestions(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, str]]:
    started = perf_counter()
    operation = "suggestions"
    couple = await _couple_context(
        request, session, user_id, operation, started, lock=True
    )
    weather, created = await _get_or_create(session, couple.id)
    result: list[dict[str, str]] = []
    if weather.interaction_score < 80:
        result.append(
            {
                "type": "interaction",
                "title": "增加互动",
                "description": "多和TA互动，提升关系温度",
                "action": "发送一个早安或晚安问候吧",
            }
        )
    if weather.days_since_last_interaction > 1:
        result.append(
            {
                "type": "date",
                "title": "安排约会",
                "description": "已经好几天没有互动了",
                "action": "计划一次约会吧",
            }
        )
    if not result:
        result.append(
            {
                "type": "maintain",
                "title": "继续保持",
                "description": "你们的关系很好，继续保持！",
                "action": "可以尝试一个新的约会地点",
            }
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "created" if created else "success", started),
    )
    return result


async def forecast(
    request: Request, session: AsyncSession, user_id: int
) -> list[dict[str, object]]:
    started = perf_counter()
    operation = "forecast"
    couple = await _couple_context(
        request, session, user_id, operation, started, lock=True
    )
    weather, created = await _get_or_create(session, couple.id)
    current_date = _today()
    result: list[dict[str, object]] = []
    for offset in range(7):
        score = min(100, weather.interaction_score + offset * 5)
        config = _weather_config(score)
        result.append(
            {
                "date": (current_date + timedelta(days=offset)).isoformat(),
                "weatherLevel": config[0],
                "weatherIcon": config[2],
                "predictedScore": score,
            }
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, "created" if created else "success", started),
    )
    return result
