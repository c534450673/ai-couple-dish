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
