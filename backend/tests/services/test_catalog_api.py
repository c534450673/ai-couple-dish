from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from packages.platform.catalog import Dish
from services.catalog.app import main as catalog_main

SECRET = "admin-test-secret-" + "x" * 64
AUTHORIZED_SOURCE = {
    "id": "81",
    "url": "https://example.test/source",
    "license": "CC-BY-4.0",
    "attribution": "Example Author",
    "reviewStatus": "approved",
}


class Session:
    def __init__(self, *, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        if self.commit_error:
            raise self.commit_error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class Store:
    def __init__(self, dishes: list[Dish] | None = None) -> None:
        self.dishes = dishes or []
        self.review_calls: list[tuple[str, int, bool]] = []
        self.publish_calls: list[str] = []

    async def list_cuisines(self, _session: Session) -> list[dict[str, object]]:
        return [{"id": 1, "slug": "chuan", "name": "川菜"}]

    async def list_dishes(
        self,
        _session: Session,
        *,
        cuisine: str | None,
        keyword: str | None,
        tag: str | None,
        spicy_level: int | None,
        allergen: str | None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Dish]:
        del cuisine, keyword, tag, spicy_level, allergen, page, page_size
        return self.dishes

    async def get_published_dish(self, _session: Session, dish_reference: str) -> Dish | None:
        return next(
            (
                dish
                for dish in self.dishes
                if dish.status == "published" and str(dish.id) == dish_reference
            ),
            None,
        )

    async def import_catalog(
        self, _session: Session, _rows: list[dict[str, object]], *, source_name: str
    ) -> dict[str, object]:
        return {"batchId": 1, "imported": 0, "failed": 0, "failures": [], "source": source_name}

    async def review_source(
        self, _session: Session, *, dish_reference: str, source_id: int, approved: bool
    ) -> dict[str, object]:
        self.review_calls.append((dish_reference, source_id, approved))
        return {"dishId": 301, "sourceId": source_id, "reviewStatus": "approved"}

    async def publish_dish(self, _session: Session, *, dish_reference: str) -> dict[str, object]:
        self.publish_calls.append(dish_reference)
        return {"id": 301, "dishId": 301, "slug": dish_reference, "status": "published"}


def _admin_token(**overrides: object) -> str:
    claims: dict[str, object] = {
        "sub": "admin",
        "role": "admin",
        "iss": "admin-service",
        "aud": "admin-web",
        "jti": "catalog-test",
        "iat": 1,
        "exp": 9_999_999_999,
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS512")


def _test_app(store: Store, session: Session):
    @asynccontextmanager
    async def provide_session() -> AsyncIterator[Session]:
        yield session

    return catalog_main.create_app(session_provider=provide_session, store=store)


def _legal_dish() -> Dish:
    return Dish(
        id=301,
        slug="legal-dish",
        name="授权测试菜品",
        cuisine="chuan",
        tags=("推荐",),
        spicy_level=1,
        status="published",
        sources=(AUTHORIZED_SOURCE,),
        unit_price=Decimal("26.80"),
    )


def test_catalog_api_uses_injected_persistent_store_not_module_catalog() -> None:
    app = _test_app(Store(), Session())

    assert not hasattr(app.state, "catalog")
    response = TestClient(app).get("/api/catalog/dishes", params={"cuisine": "chuan"})

    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "page": 1, "pageSize": 20, "total": 0}


def test_catalog_api_exposes_numeric_id_and_price_for_published_record() -> None:
    client = TestClient(_test_app(Store([_legal_dish()]), Session()))

    listed = client.get("/api/catalog/dishes").json()["data"]
    detail = client.get("/api/catalog/dishes/301")

    assert listed["total"] == 1
    assert listed["items"][0]["id"] == 301
    assert listed["items"][0]["unitPrice"] == "26.80"
    assert detail.status_code == 200
    assert detail.json()["data"]["sources"][0]["reviewStatus"] == "approved"


def test_catalog_api_hides_unknown_detail() -> None:
    response = TestClient(_test_app(Store(), Session())).get("/api/catalog/dishes/not-found")

    assert response.status_code == 404


def test_catalog_write_rejects_spoofed_role_and_user_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", SECRET)
    client = TestClient(_test_app(Store(), Session()))
    spoofed = client.post("/api/catalog/import", json=[], headers={"X-Admin-Role": "admin"})
    denied = client.post(
        "/api/catalog/dishes/chuan-dish-001/publish",
        headers={"Authorization": f"Bearer {_admin_token(iss='user')}"},
    )

    assert spoofed.status_code == 401
    assert denied.status_code == 403


def test_catalog_review_and_publish_commit_after_authorized_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", SECRET)
    store = Store()
    session = Session()
    client = TestClient(_test_app(store, session))
    headers = {"Authorization": f"Bearer {_admin_token()}"}

    reviewed = client.post(
        "/api/catalog/dishes/301/sources/81/review", headers=headers, json={"approved": True}
    )
    published = client.post("/api/catalog/dishes/legal-dish/publish", headers=headers)

    assert reviewed.status_code == 200
    assert published.status_code == 200
    assert store.review_calls == [("301", 81, True)]
    assert store.publish_calls == ["legal-dish"]
    assert session.committed is True
    assert session.rolled_back is False


def test_catalog_import_rolls_back_when_database_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", SECRET)
    session = Session(commit_error=IntegrityError("insert", {}, RuntimeError("database offline")))
    client = TestClient(_test_app(Store(), session))

    response = client.post(
        "/api/catalog/import", json=[], headers={"Authorization": f"Bearer {_admin_token()}"}
    )

    assert response.status_code == 503
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_catalog_runtime_connects_and_closes_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Database:
        def __init__(self, _url: str, *, pool_size: int, max_overflow: int) -> None:
            del pool_size, max_overflow
            self.session = object()

        async def connect(self) -> None:
            events.append("connected")

        async def close(self) -> None:
            events.append("closed")

    monkeypatch.setattr(catalog_main, "Database", Database)
    settings = SimpleNamespace(
        database_url="mysql+asyncmy://test",
        database_pool_size=1,
        database_max_overflow=0,
        log_level="INFO",
        service_name="catalog",
        release_sha="test",
    )
    app = catalog_main.create_app(settings=settings)

    async with app.router.lifespan_context(app):
        assert app.state.session_provider is not None

    assert events == ["connected", "closed"]
