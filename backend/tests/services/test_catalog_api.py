from fastapi.testclient import TestClient

from services.catalog.app.main import app


def test_catalog_api_lists_published_dishes_and_filters() -> None:
    response = TestClient(app).get(
        "/api/catalog/dishes", params={"cuisine": "chuan", "pageSize": 2}
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] > 0
    assert len(payload["items"]) == 2
    assert all(item["cuisine"] == "chuan" for item in payload["items"])


def test_catalog_api_hides_unknown_detail() -> None:
    response = TestClient(app).get("/api/catalog/dishes/not-found")
    assert response.status_code == 404
