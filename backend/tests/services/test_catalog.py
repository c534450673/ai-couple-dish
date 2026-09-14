from decimal import Decimal
from typing import Any, cast

from packages.platform.catalog import Catalog, Dish
from services.catalog.app.services.catalog import SqlAlchemyCatalogStore, import_rows

AUTHORIZED_SOURCE = {
    "url": "https://example.test/source",
    "license": "CC-BY-4.0",
    "attribution": "Example Author",
    "reviewStatus": "approved",
}


def test_catalog_filters_and_only_published() -> None:
    catalog = Catalog(
        [
            Dish(
                slug="a",
                name="辣子鸡",
                cuisine="川菜",
                tags=("辣",),
                spicy_level=3,
                status="published",
                id=101,
                unit_price=Decimal("18.50"),
                sources=(AUTHORIZED_SOURCE,),
            ),
            Dish(slug="b", name="草稿", cuisine="粤菜", tags=(), spicy_level=0, status="draft"),
        ]
    )
    assert [d.slug for d in catalog.list(cuisine="川菜")] == ["a"]
    assert catalog.list(keyword="草稿") == []
    assert catalog.get_by_id(101) is not None


def test_catalog_requires_license_for_publish() -> None:
    catalog = Catalog(
        [
            Dish(
                slug="a",
                name="菜",
                cuisine="川菜",
                tags=(),
                spicy_level=1,
                status="draft",
                sources=(),
            )
        ]
    )
    assert catalog.publish("a") is False


def test_catalog_hides_dish_that_claims_published_without_a_legal_price_or_source() -> None:
    catalog = Catalog(
        [
            Dish(
                slug="unverified",
                name="未核验菜品",
                cuisine="川菜",
                tags=(),
                spicy_level=0,
                status="published",
                id=102,
                unit_price=Decimal("10.00"),
            ),
            Dish(
                slug="unpriced",
                name="未定价菜品",
                cuisine="川菜",
                tags=(),
                spicy_level=0,
                status="published",
                id=103,
                sources=(AUTHORIZED_SOURCE,),
            ),
        ]
    )

    assert catalog.list() == []
    assert catalog.publish("unverified") is False
    assert catalog.publish("unpriced") is False


def test_catalog_import_requires_numeric_id_and_price_and_forces_draft() -> None:
    imported = import_rows(
        [
            {
                "slug": "proper-dish",
                "name": "已授权待审菜品",
                "cuisine": "chuan",
                "dishId": 501,
                "price": "22.50",
                "status": "published",
                "sources": [AUTHORIZED_SOURCE],
            },
            {
                "slug": "missing-price",
                "name": "缺失价格",
                "cuisine": "chuan",
                "dishId": 502,
                "sources": [AUTHORIZED_SOURCE],
            },
            {
                "slug": "duplicate-id",
                "name": "重复 ID",
                "cuisine": "chuan",
                "dishId": 501,
                "price": "13.00",
                "sources": [AUTHORIZED_SOURCE],
            },
        ]
    )

    assert imported["imported"] == 1
    assert imported["failed"] == 2
    dish = imported["dishes"][0]
    assert dish["id"] == 501
    assert dish["unit_price"] == Decimal("22.50")
    assert dish["status"] == "draft"
    assert dish["sources"][0]["reviewStatus"] == "pending"


def test_sql_catalog_list_uses_bounded_offset_and_limit() -> None:
    import asyncio

    class Result:
        def all(self) -> list[object]:
            return []

    class Session:
        def __init__(self) -> None:
            self.count_statement: object | None = None
            self.page_statement: object | None = None

        async def scalar(self, statement: object) -> int:
            self.count_statement = statement
            return 37

        async def scalars(self, statement: object) -> Result:
            self.page_statement = statement
            return Result()

    session: Any = Session()

    page = asyncio.run(
        SqlAlchemyCatalogStore().list_dishes(
            session,
            cuisine=None,
            keyword=None,
            tag=None,
            spicy_level=None,
            allergen=None,
            page=3,
            page_size=7,
        )
    )

    assert page.total == 37
    assert session.page_statement is not None
    statement = cast(Any, session.page_statement)
    assert statement._limit_clause.value == 7
    assert statement._offset_clause.value == 14
