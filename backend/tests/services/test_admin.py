import bcrypt
import pytest
from fastapi.testclient import TestClient

from services.admin.app.main import create_app

SECRET = "a" * 64


@pytest.fixture(autouse=True)
def admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt.hashpw(b"test", bcrypt.gensalt()).decode())


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
    assert response.status_code == 404


def test_login_fails_closed_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD_HASH")
    client = TestClient(create_app(secret=SECRET))
    assert (
        client.post("/api/admin/login", json={"username": "admin", "password": "test"}).status_code
        == 503
    )


def test_login_rejects_wrong_password() -> None:
    client = TestClient(create_app(secret=SECRET))
    assert (
        client.post("/api/admin/login", json={"username": "admin", "password": "wrong"}).status_code
        == 401
    )
