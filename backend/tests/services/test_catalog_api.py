import jwt
from fastapi.testclient import TestClient

from services.catalog.app.main import app


def test_catalog_api_does_not_publish_unverified_sample_dishes() -> None:
    response = TestClient(app).get(
        "/api/catalog/dishes", params={"cuisine": "chuan", "pageSize": 2}
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 0
    assert payload["items"] == []


def test_catalog_api_hides_unknown_detail() -> None:
    response = TestClient(app).get("/api/catalog/dishes/not-found")
    assert response.status_code == 404


def test_catalog_write_rejects_spoofed_role_and_user_token(monkeypatch) -> None:
    secret = "admin-test-secret-" + "x" * 64
    monkeypatch.setenv("ADMIN_JWT_SECRET", secret)
    client = TestClient(app)
    spoofed = client.post(
        "/api/catalog/import", json=[], headers={"X-Admin-Role": "admin"}
    )
    user_token = jwt.encode(
        {
            "sub": "7", "role": "admin", "iss": "user", "aud": "admin-web",
            "jti": "1", "iat": 1, "exp": 9999999999,
        },
        secret,
        algorithm="HS512",
    )
    denied = client.post(
        "/api/catalog/dishes/chuan-dish-001/publish",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert spoofed.status_code == 401
    assert denied.status_code == 403
