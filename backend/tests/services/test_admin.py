from contextlib import asynccontextmanager
from typing import Any

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


class _PersistentSession:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.committed = False
        self.session_present = True

    async def execute(self, statement: object, params: object | None = None) -> object:
        statement_text = str(statement)
        self.statements.append(statement_text)

        class Result:
            def mappings(self) -> "Result":
                return self

            def all(self) -> list[dict[str, object]]:
                if "FROM admin_user" in statement_text:
                    return [{"id": 1, "status": "active"}]
                if "FROM admin_session" in statement_text and self_session.session_present:
                    return [
                        {
                            "revoked_at": None,
                            "expires_at": None,
                            "status": "active",
                            "admin_user_id": 1,
                        }
                    ]
                if "catalog_dish_source" in statement_text:
                    return [{"dish_id": 1, "source_id": 1}]
                return []

        self_session = self
        return Result()

    async def commit(self) -> None:
        self.committed = True

class _CatalogStore:
    def __init__(self) -> None:
        self.review_calls: list[tuple[str, int, bool]] = []
        self.publish_calls: list[str] = []
        self.import_calls: list[tuple[list[dict[str, Any]], str]] = []

    async def review_source(
        self, _session: object, *, dish_reference: str, source_id: int, approved: bool
    ) -> dict[str, object]:
        self.review_calls.append((dish_reference, source_id, approved))
        return {"dishId": 1, "sourceId": source_id, "reviewStatus": "approved"}

    async def publish_dish(self, _session: object, *, dish_reference: str) -> dict[str, object]:
        self.publish_calls.append(dish_reference)
        return {"dishId": 1, "slug": dish_reference, "status": "published"}

    async def import_catalog(
        self, _session: object, rows: list[dict[str, object]], *, source_name: str
    ) -> dict[str, object]:
        self.import_calls.append((rows, source_name))
        return {"batchId": 1, "imported": len(rows), "failed": 0, "failures": []}


def test_admin_audit_uses_configured_database_session() -> None:
    session = _PersistentSession()

    @asynccontextmanager
    async def provider():
        yield session

    client = TestClient(
        create_app(secret=SECRET, session_provider=provider, catalog_store=_CatalogStore())
    )
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    response = client.post(
        "/api/admin/catalog/review",
        json={"slug": "persistent", "sourceId": 1, "approved": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert any("admin_audit_log" in statement for statement in session.statements)
    assert session.committed


def test_admin_catalog_writes_delegate_to_persistent_catalog_store() -> None:
    session = _PersistentSession()
    catalog = _CatalogStore()

    @asynccontextmanager
    async def provider():
        yield session

    client = TestClient(
        create_app(secret=SECRET, session_provider=provider, catalog_store=catalog)  # type: ignore[arg-type]
    )
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    imported = client.post(
        "/api/admin/catalog/import",
        headers=headers,
        json={"source": "feed", "rows": [{"slug": "dish"}]},
    )
    reviewed = client.post(
        "/api/admin/catalog/review",
        headers=headers,
        json={"slug": "persistent", "sourceId": 1, "approved": True},
    )
    published = client.post("/api/admin/catalog/persistent/publish", headers=headers)

    assert imported.status_code == 200
    assert reviewed.status_code == 200
    assert published.status_code == 200
    assert catalog.import_calls == [([{"slug": "dish"}], "feed")]
    assert catalog.review_calls == [("persistent", 1, True)]
    assert catalog.publish_calls == ["persistent"]


def test_admin_logout_revokes_database_session_and_rejects_reuse() -> None:
    session = _PersistentSession()

    @asynccontextmanager
    async def provider():
        yield session

    client = TestClient(create_app(secret=SECRET, session_provider=provider))
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    result = client.post("/api/admin/logout", headers=headers)
    reused = client.get("/api/admin/audit", headers=headers)

    assert result.status_code == 200
    assert result.json()["data"] == {"revoked": True}
    assert reused.status_code == 403
    assert any("UPDATE admin_session SET revoked_at" in item for item in session.statements)


def test_admin_rejects_jwt_without_persisted_session() -> None:
    session = _PersistentSession()

    @asynccontextmanager
    async def provider():
        yield session

    client = TestClient(create_app(secret=SECRET, session_provider=provider))
    token = client.post("/api/admin/login", json={"username": "admin", "password": "test"}).json()[
        "data"
    ]["token"]
    session.session_present = False

    response = client.get(
        "/api/admin/audit", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json()["message"] == "管理员会话已失效"
