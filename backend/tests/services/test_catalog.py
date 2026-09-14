from packages.platform.catalog import Catalog, Dish


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
            ),
            Dish(slug="b", name="草稿", cuisine="粤菜", tags=(), spicy_level=0, status="draft"),
        ]
    )
    assert [d.slug for d in catalog.list(cuisine="川菜")] == ["a"]
    assert catalog.list(keyword="草稿") == []


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
