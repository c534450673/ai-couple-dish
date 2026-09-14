from fastapi.testclient import TestClient

from services.admin.app.main import create_app

SECRET = "a" * 64


def test_admin_login_uses_separate_issuer_and_audience() -> None:
    client = TestClient(create_app(secret=SECRET))
    result = client.post("/api/admin/login", json={"username": "admin", "password": "test"})
    assert result.status_code == 200
    token = result.json()["data"]["token"]
    import jwt

    claims = jwt.decode(
        token, SECRET, algorithms=["HS512"], audience="admin-web", issuer="admin-service"
    )
    assert claims["role"] == "admin"


def test_admin_writes_require_token_and_create_audit() -> None:
    client = TestClient(create_app(secret=SECRET))
    denied = client.post("/api/admin/catalog/review", json={"slug": "x", "approved": True})
    assert denied.status_code == 401
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    response = client.post(
        "/api/admin/catalog/review",
        json={"slug": "x", "approved": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    audits = client.get("/api/admin/audit", headers={"Authorization": f"Bearer {token}"})
    assert audits.json()["data"]["items"]


def test_admin_user_phone_is_masked() -> None:
    client = TestClient(create_app(secret=SECRET))
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    response = client.get("/api/admin/users/1", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["data"]["phone"] == "138****8000"
