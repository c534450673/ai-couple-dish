from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from services.analytics.app.main import create_app


def test_analytics_consumes_events_and_reports() -> None:
    client = TestClient(create_app())
    for event in ("dish_viewed", "cart_item_added", "order_created"):
        response = client.post(
            "/api/analytics/events", json={"name": event, "occurred_at": "2026-09-14T10:00:00Z"}
        )
        assert response.status_code == 202
    report = client.get("/api/analytics/reports/daily?date=2026-09-14")
    assert report.json()["data"]["views"] == 1
    assert report.json()["data"]["orders"] == 1


def test_analytics_event_identity_includes_duration_and_accepts_client_event_id() -> None:
    client = TestClient(create_app())
    base = {"name": "dish_viewed", "occurred_at": "2026-09-14T10:00:00Z"}
    first = client.post("/api/analytics/events", json={**base, "durationMs": 100})
    second = client.post("/api/analytics/events", json={**base, "durationMs": 200})
    assert first.json()["data"]["deduplicated"] is False
    assert second.json()["data"]["deduplicated"] is False

    duplicate = client.post(
        "/api/analytics/events",
        json={**base, "eventId": "client-event-1", "durationMs": 100},
    )
    replay = client.post(
        "/api/analytics/events",
        json={**base, "eventId": "client-event-1", "durationMs": 100},
    )
    assert duplicate.json()["data"]["deduplicated"] is False
    assert replay.json()["data"]["deduplicated"] is True


class _PersistentSession:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.committed = False

    async def execute(self, statement: object, params: object | None = None) -> object:
        self.statements.append(str(statement))

        class Result:
            def mappings(self) -> "Result":
                return self

            def all(self) -> list[dict[str, object]]:
                return []

            def first(self) -> None:
                return None

        return Result()

    async def commit(self) -> None:
        self.committed = True


def test_analytics_writes_events_and_aggregates_to_database() -> None:
    session = _PersistentSession()

    @asynccontextmanager
    async def provider():
        yield session

    client = TestClient(create_app(session_provider=provider))
    response = client.post(
        "/api/analytics/events",
        json={"name": "dish_viewed", "occurred_at": "2026-09-14T10:00:00Z"},
    )
    assert response.status_code == 202
    assert any("analytics_event" in statement for statement in session.statements)
    assert any("analytics_daily" in statement for statement in session.statements)
    assert any("analytics_hourly" in statement for statement in session.statements)
    assert session.committed
