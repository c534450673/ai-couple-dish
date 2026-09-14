"""事件接收和只读报表 API。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from packages.platform.service import create_service_app

logger = structlog.get_logger()


class Event(BaseModel):
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


def create_app() -> FastAPI:
    app = create_service_app("analytics")
    aggregates: dict[str, dict[str, dict[str, Any]]] = {"daily": {}, "hourly": {}}
    seen: set[str] = set()
    app.state.aggregates = aggregates

    @app.post("/api/analytics/events", status_code=202)
    async def ingest(event: Event) -> dict[str, Any]:
        event_id = f"{event.name}:{event.occurred_at.isoformat()}:{event.user_id}:{event.couple_id}"
        duplicate = event_id in seen
        if not duplicate:
            seen.add(event_id)
            consume_event(aggregates, event)
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
        row = aggregates["daily"].get(
            date, {"events": {}, "single": 0, "total": 0, "durations": {}}
        )
        return {"code": 200, "message": "操作成功", "data": _report(row, date)}

    @app.get("/api/analytics/reports/hourly")
    async def hourly(date: str) -> dict[str, Any]:
        rows = [
            _report(row, key) for key, row in aggregates["hourly"].items() if key.startswith(date)
        ]
        rows.sort(key=lambda item: item["period"])
        return {"code": 200, "message": "操作成功", "data": {"items": rows, "total": len(rows)}}

    return app


app = create_app()
