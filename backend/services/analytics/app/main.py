"""事件接收和只读报表 API。"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import Database
from packages.platform.service import create_service_app

logger = structlog.get_logger()
SessionProvider = Callable[[], AbstractAsyncContextManager[AsyncSession]]
_UPSERT_SQL = {
    "daily": text(
        """
        INSERT INTO analytics_daily (period, period_type, metrics_json, updated_at)
        VALUES (:period, :period_type, :metrics_json, :updated_at)
        ON DUPLICATE KEY UPDATE metrics_json = VALUES(metrics_json),
                                updated_at = VALUES(updated_at)
        """
    ),
    "hourly": text(
        """
        INSERT INTO analytics_hourly (period, period_type, metrics_json, updated_at)
        VALUES (:period, :period_type, :metrics_json, :updated_at)
        ON DUPLICATE KEY UPDATE metrics_json = VALUES(metrics_json),
                                updated_at = VALUES(updated_at)
        """
    ),
}
_SELECT_SQL = {
    "daily": text("SELECT metrics_json FROM analytics_daily WHERE period = :period"),
    "hourly": text("SELECT metrics_json FROM analytics_hourly WHERE period = :period"),
}
_HYDRATE_SQL = {
    "daily": text("SELECT period, metrics_json FROM analytics_daily"),
    "hourly": text("SELECT period, metrics_json FROM analytics_hourly"),
}
_LOCK_SQL = {
    "daily": text(
        "SELECT metrics_json FROM analytics_daily "
        "WHERE period = :period FOR UPDATE"
    ),
    "hourly": text(
        "SELECT metrics_json FROM analytics_hourly "
        "WHERE period = :period FOR UPDATE"
    ),
}


class Event(BaseModel):
    event_id: str | None = Field(default=None, alias="eventId", min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    occurred_at: datetime = Field(alias="occurredAt")
    user_id: int | None = Field(default=None, alias="userId", ge=1)
    couple_id: int | None = Field(default=None, alias="coupleId", ge=1)
    mode: str = Field(default="couple", pattern="^(couple|single)$")
    duration_ms: int | None = Field(default=None, alias="durationMs", ge=0, le=86_400_000)

    model_config = {"populate_by_name": True}


def _bucket(value: datetime) -> tuple[str, str]:
    value = value.astimezone(UTC)
    return value.date().isoformat(), value.strftime("%Y-%m-%dT%H:00:00Z")


def consume_event(aggregates: dict[str, dict[str, dict[str, Any]]], event: Event) -> None:
    """将一个事件应用到日/小时聚合，供 outbox consumer 和 HTTP 接收端共用。"""
    day, hour = _bucket(event.occurred_at)
    for period, key in (("daily", day), ("hourly", hour)):
        row = aggregates[period].setdefault(
            key, {"date": key, "events": {}, "single": 0, "total": 0, "durations": {}}
        )
        row["events"][event.name] = row["events"].get(event.name, 0) + 1
        row["total"] += 1
        if event.mode == "single":
            row["single"] += 1
        if event.duration_ms is not None:
            duration = row["durations"].setdefault(event.name, {"total": 0, "count": 0})
            duration["total"] += event.duration_ms
            duration["count"] += 1


def _report(row: dict[str, Any], period: str) -> dict[str, Any]:
    counts = row.get("events", {})
    views = counts.get("dish_viewed", 0)
    durations = {
        name: values["total"] / values["count"]
        for name, values in row.get("durations", {}).items()
        if values["count"]
    }
    return {
        "period": period,
        "views": views,
        "cartAdds": counts.get("cart_item_added", 0),
        "orders": counts.get("order_created", 0),
        "completed": counts.get("order_completed", 0),
        "cancelled": counts.get("order_cancelled", 0),
        "conversionRate": round(counts.get("order_created", 0) / views * 100, 2) if views else 0,
        "singleModeRatio": round(row.get("single", 0) / row["total"] * 100, 2)
        if row.get("total")
        else 0,
        "averageDurationMs": durations,
        "eventCounts": counts,
    }


def _aggregate_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize the in-memory aggregate with a stable JSON shape for MySQL."""
    return {
        "date": row.get("date"),
        "events": row.get("events", {}),
        "single": row.get("single", 0),
        "total": row.get("total", 0),
        "durations": row.get("durations", {}),
    }


def create_app(
    *,
    session_provider: SessionProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings
    if active_settings is None:
        try:
            active_settings = get_settings()
        except ValidationError:
            if os.getenv("APP_ENV") in {"prod", "staging"}:
                raise
    app = create_service_app("analytics", settings=active_settings)
    aggregates: dict[str, dict[str, dict[str, Any]]] = {"daily": {}, "hourly": {}}
    seen: set[str] = set()
    app.state.aggregates = aggregates

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if session_provider is not None:
            application.state.session_provider = session_provider
            await hydrate_from_database()
            yield
            return
        if active_settings is None:
            application.state.session_provider = None
            yield
            return
        database = Database(
            active_settings.database_url,
            pool_size=active_settings.database_pool_size,
            max_overflow=active_settings.database_max_overflow,
        )
        application.state.session_provider = database.session
        await database.connect()
        await logger.ainfo(
            "analytics_dependencies_connected",
            module="analytics",
            operation="startup",
            result="success",
            dependencies=["database"],
        )
        try:
            await hydrate_from_database()
            yield
        finally:
            await database.close()
            await logger.ainfo(
                "analytics_dependencies_closed",
                module="analytics",
                operation="shutdown",
                result="success",
                dependencies=["database"],
            )

    app.router.lifespan_context = lifespan
    app.state.session_provider = session_provider

    async def hydrate_from_database() -> None:
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return
        try:
            async with provider() as session:
                for period in ("daily", "hourly"):
                    # Period 只允许来自固定白名单，使用预构造 SQL 避免动态表名进入查询。
                    result = await session.execute(_HYDRATE_SQL[period])
                    for row in result.mappings().all():
                        try:
                            metrics = json.loads(row["metrics_json"])
                            if not isinstance(metrics, dict):
                                raise ValueError("聚合数据必须为对象")
                            aggregates[period][str(row["period"])] = metrics
                        except (TypeError, ValueError, json.JSONDecodeError):
                            await logger.awarning(
                                "analytics_aggregate_invalid",
                                module="analytics",
                                operation="startup.hydrate",
                                result="skipped",
                                period=period,
                            )
            await logger.ainfo(
                "analytics_aggregates_hydrated",
                module="analytics",
                operation="startup.hydrate",
                result="success",
                dailyCount=len(aggregates["daily"]),
                hourlyCount=len(aggregates["hourly"]),
            )
        except Exception as error:
            await logger.aerror(
                "analytics_persistence_read_failed",
                module="analytics",
                operation="startup.hydrate",
                result="error",
                errorCode=type(error).__name__,
            )
            raise

    async def persist_event(event_id: str, event: Event) -> bool:
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return False
        day, hour = _bucket(event.occurred_at)
        row_values: dict[str, Any] = {
            "id": event_id,
            "event_name": event.name,
            "occurred_at": event.occurred_at.astimezone(UTC).replace(tzinfo=None),
            "user_id": event.user_id,
            "couple_id": event.couple_id,
            "mode": event.mode,
            "duration_ms": event.duration_ms,
        }
        try:
            async with provider() as session:
                insert_result = await session.execute(
                    text(
                        """
                        INSERT IGNORE INTO analytics_event
                          (id, event_name, occurred_at, user_id, couple_id, mode, duration_ms)
                        VALUES (:id, :event_name, :occurred_at, :user_id, :couple_id, :mode,
                                :duration_ms)
                        """
                    ),
                    row_values,
                )
                # 唯一主键由数据库原子地完成去重，避免 check-then-insert 竞态。
                rowcount = getattr(insert_result, "rowcount", 1)
                if rowcount == 0:
                    await session.rollback()
                    await logger.ainfo(
                        "analytics_event_deduplicated",
                        module="analytics",
                        operation="event.persist",
                        result="duplicate",
                        eventId=event_id,
                    )
                    return False
                # 在同一事务内锁定聚合行，并基于数据库最新快照合并，避免并发覆盖。
                for period, key in (("daily", day), ("hourly", hour)):
                    current = await session.execute(_LOCK_SQL[period], {"period": key})
                    existing = current.mappings().first()
                    if existing:
                        try:
                            aggregates[period][key] = json.loads(existing["metrics_json"])
                        except (TypeError, json.JSONDecodeError):
                            aggregates[period].pop(key, None)
                    aggregates.setdefault(period, {}).setdefault(
                        key, {"date": key, "events": {}, "single": 0, "total": 0, "durations": {}}
                    )
                consume_event(aggregates, event)
                metrics = {
                    period: _aggregate_metrics(aggregates[period][key])
                    for period, key in (("daily", day), ("hourly", hour))
                }
                for period, key in (("daily", day), ("hourly", hour)):
                    period_type = "day" if period == "daily" else "hour"
                    await session.execute(
                        _UPSERT_SQL[period],
                        {
                            "period": key,
                            "period_type": period_type,
                            "metrics_json": json.dumps(metrics[period], ensure_ascii=False),
                            "updated_at": datetime.now(UTC).replace(tzinfo=None),
                        },
                    )
                await session.commit()
        except Exception as error:
            await logger.aerror(
                "analytics_persistence_failed",
                module="analytics",
                operation="event.persist",
                result="error",
                errorCode=type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "统计服务暂不可用", "data": None},
            ) from error
        return True

    async def load_period(period: str, key: str) -> dict[str, Any] | None:
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is None:
            return None
        try:
            async with provider() as session:
                result = await session.execute(
                    _SELECT_SQL[period],
                    {"period": key},
                )
                row = result.mappings().first()
        except Exception as error:
            await logger.aerror(
                "analytics_persistence_read_failed",
                module="analytics",
                operation="report.read",
                result="error",
                errorCode=type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "统计服务暂不可用", "data": None},
            ) from error
        if not row:
            return None
        try:
            metrics = json.loads(row["metrics_json"])
            return metrics if isinstance(metrics, dict) else None
        except (TypeError, json.JSONDecodeError):
            return None

    @app.post("/api/analytics/events", status_code=202)
    async def ingest(event: Event) -> dict[str, Any]:
        # 客户端可提供稳定 eventId；否则将所有影响聚合结果的字段纳入指纹，
        # 避免同一时间同一用户上报不同 duration 时被错误去重。
        event_identity = (
            f"{event.name}:{event.occurred_at.isoformat()}:{event.user_id}:"
            f"{event.couple_id}:{event.mode}:{event.duration_ms}"
        )
        event_id = event.event_id or (
            event_identity
            if len(event_identity) <= 128
            else sha256(event_identity.encode("utf-8")).hexdigest()
        )
        duplicate = event_id in seen
        if not duplicate and getattr(app.state, "session_provider", None) is not None:
            duplicate = not await persist_event(event_id, event)
        elif not duplicate:
            consume_event(aggregates, event)
        if not duplicate:
            seen.add(event_id)
        logger.info(
            "analytics_event_consumed",
            module="analytics",
            operation=event.name,
            result="duplicate" if duplicate else "accepted",
        )
        return {"code": 202, "message": "已接收", "data": {"deduplicated": duplicate}}

    @app.get("/api/analytics/reports/daily")
    async def daily(date: str) -> dict[str, Any]:
        try:
            datetime.fromisoformat(date)
        except ValueError as error:
            raise HTTPException(
                status_code=400, detail={"code": 400, "message": "日期格式错误", "data": None}
            ) from error
        persisted = await load_period("daily", date)
        row = persisted or aggregates["daily"].get(
            date, {"events": {}, "single": 0, "total": 0, "durations": {}}
        )
        return {"code": 200, "message": "操作成功", "data": _report(row, date)}

    @app.get("/api/analytics/reports/hourly")
    async def hourly(date: str) -> dict[str, Any]:
        rows = [
            _report(row, key) for key, row in aggregates["hourly"].items() if key.startswith(date)
        ]
        provider: SessionProvider | None = getattr(app.state, "session_provider", None)
        if provider is not None:
            try:
                async with provider() as session:
                    result = await session.execute(
                        text(
                            "SELECT period, metrics_json FROM analytics_hourly "
                            "WHERE period LIKE :prefix ORDER BY period"
                        ),
                        {"prefix": f"{date}%"},
                    )
                    rows = []
                    for row in result.mappings().all():
                        try:
                            metrics = json.loads(row["metrics_json"])
                            if not isinstance(metrics, dict):
                                raise ValueError("聚合数据必须为对象")
                            rows.append(_report(metrics, row["period"]))
                        except (TypeError, ValueError, json.JSONDecodeError):
                            await logger.awarning(
                                "analytics_aggregate_invalid",
                                module="analytics",
                                operation="report.hourly",
                                result="skipped",
                                period=str(row.get("period", "")),
                            )
            except Exception as error:
                await logger.aerror(
                    "analytics_persistence_read_failed",
                    module="analytics",
                    operation="report.hourly",
                    result="error",
                    errorCode=type(error).__name__,
                )
                raise HTTPException(
                    status_code=503,
                    detail={"code": 503, "message": "统计服务暂不可用", "data": None},
                ) from error
        rows.sort(key=lambda item: item["period"])
        return {"code": 200, "message": "操作成功", "data": {"items": rows, "total": len(rows)}}

    return app


app = create_app()
