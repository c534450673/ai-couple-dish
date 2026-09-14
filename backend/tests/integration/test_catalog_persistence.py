"""MySQL 集成测试：目录主数据、授权审核和发布必须同库持久化。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import CatalogCuisine, CatalogDish, CatalogDishSource, CatalogImportBatch
from services.catalog.app.main import create_app

SECRET = "catalog-integration-admin-" + "x" * 64


def _admin_token() -> str:
    return jwt.encode(
        {
            "sub": "catalog-admin",
            "role": "admin",
            "iss": "admin-service",
            "aud": "admin-web",
            "jti": "catalog-integration",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        SECRET,
        algorithm="HS512",
    )


@pytest.fixture
async def catalog_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    tables = [
        CatalogCuisine.__table__,
        CatalogDish.__table__,
        CatalogDishSource.__table__,
        CatalogImportBatch.__table__,
    ]
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: CatalogCuisine.metadata.create_all(sync, tables=tables)
            )
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: CatalogCuisine.metadata.drop_all(sync, tables=tables)
            )
        await engine.dispose()


@pytest.mark.integration
async def test_catalog_import_review_publish_and_read_are_persisted_in_mysql(
    catalog_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", SECRET)
    sessions = async_sessionmaker(catalog_engine, expire_on_commit=False)

    @asynccontextmanager
    async def provide_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app = create_app(session_provider=provide_session)
    headers = {"Authorization": f"Bearer {_admin_token()}"}
    rows = [
        {
            "id": 901,
            "slug": "mysql-legal-dish",
            "name": "MySQL 授权菜品",
            "cuisine": "chuan",
            "cuisineName": "川菜",
            "tags": ["推荐"],
            "allergens": [],
            "spicyLevel": 2,
            "price": "42.50",
            "sources": [
                {
                    "url": "https://license.example.test/mysql-legal-dish",
                    "license": "CC-BY-4.0",
                    "attribution": "Author",
                    "reviewStatus": "pending",
                }
            ],
        }
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://catalog") as client:
        imported = await client.post("/api/catalog/import", headers=headers, json=rows)
        assert imported.status_code == 200, imported.text
        assert imported.json()["data"]["imported"] == 1
        # 未审核的来源不能借由 status 字段或导入请求直接上架。
        blocked = await client.post("/api/catalog/dishes/901/publish", headers=headers)
        assert blocked.status_code == 422

        async with sessions() as session:
            record = await session.scalar(select(CatalogDish).where(CatalogDish.id == 901))
            source = await session.scalar(
                select(CatalogDishSource).where(CatalogDishSource.dish_id == 901)
            )
            cuisine = await session.scalar(
                select(CatalogCuisine).where(CatalogCuisine.slug == "chuan")
            )
        assert record is not None
        assert source is not None
        assert cuisine is not None
        assert record.status == "draft"
        assert record.unit_price == Decimal("42.50")
        assert source.source_url == "https://license.example.test/mysql-legal-dish"
        assert source.review_status == "pending"

        reviewed = await client.post(
            f"/api/catalog/dishes/901/sources/{source.id}/review",
            headers=headers,
            json={"approved": True},
        )
        assert reviewed.status_code == 200, reviewed.text
        published = await client.post("/api/catalog/dishes/901/publish", headers=headers)
        assert published.status_code == 200, published.text
        listed = await client.get("/api/catalog/dishes", params={"cuisine": "chuan"})
        assert listed.status_code == 200, listed.text
        assert listed.json()["data"]["items"][0]["id"] == 901
        assert listed.json()["data"]["items"][0]["unitPrice"] == "42.50"

    async with sessions() as session:
        record = await session.scalar(select(CatalogDish).where(CatalogDish.id == 901))
        source = await session.scalar(
            select(CatalogDishSource).where(CatalogDishSource.dish_id == 901)
        )
    assert record is not None and record.status == "published"
    assert source is not None and source.review_status == "approved"
