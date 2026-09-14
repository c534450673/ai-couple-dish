from __future__ import annotations

import builtins
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Dish:
    slug: str
    name: str
    cuisine: str
    tags: tuple[str, ...]
    spicy_level: int
    status: str = "draft"
    sources: tuple[dict[str, str], ...] = field(default_factory=tuple)
    allergens: tuple[str, ...] = field(default_factory=tuple)
    image_url: str | None = None
    id: int | None = None
    unit_price: Decimal | None = None


class Catalog:
    def __init__(self, dishes: list[Dish]) -> None:
        self._dishes = {dish.slug: dish for dish in dishes}
        self._dishes_by_id: dict[int, Dish] = {}
        for dish in dishes:
            if dish.id is None:
                continue
            if dish.id in self._dishes_by_id:
                raise ValueError(f"重复的菜品 ID: {dish.id}")
            self._dishes_by_id[dish.id] = dish

    def list(
        self,
        *,
        cuisine: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
        spicy_level: int | None = None,
        allergen: str | None = None,
        include_draft: bool = False,
    ) -> list[Dish]:
        return [
            dish
            for dish in self._dishes.values()
            if (include_draft or self.is_published(dish))
            and (not cuisine or dish.cuisine == cuisine)
            and (not keyword or keyword.lower() in dish.name.lower())
            and (not tag or tag in dish.tags)
            and (spicy_level is None or dish.spicy_level == spicy_level)
            and (not allergen or allergen not in dish.allergens)
        ]

    def get(self, slug: str) -> Dish | None:
        return self._dishes.get(slug)

    def get_by_id(self, dish_id: int) -> Dish | None:
        return self._dishes_by_id.get(dish_id)

    def list_cuisines(self) -> builtins.list[str]:
        return sorted({dish.cuisine for dish in self._dishes.values()})

    @staticmethod
    def _source_is_authorized(source: dict[str, str]) -> bool:
        if (
            not source.get("license")
            or not source.get("url")
            or not source.get("attribution")
            or source.get("reviewStatus", "pending") != "approved"
        ):
            return False
        expires_at = source.get("licenseExpiresAt")
        if not expires_at:
            return True
        try:
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            return False
        return parsed.astimezone(UTC) > datetime.now(UTC)

    def is_publishable(self, dish: Dish) -> bool:
        return (
            dish.id is not None
            and dish.id > 0
            and bool(dish.name.strip())
            and dish.unit_price is not None
            and dish.unit_price.is_finite()
            and dish.unit_price >= Decimal("0")
            and bool(dish.sources)
            and all(self._source_is_authorized(source) for source in dish.sources)
        )

    def is_published(self, dish: Dish) -> bool:
        return dish.status == "published" and self.is_publishable(dish)

    def publish(self, slug: str) -> bool:
        dish = self._dishes.get(slug)
        if dish is None or not self.is_publishable(dish):
            return False
        self._dishes[slug] = replace(dish, status="published")
        if dish.id is not None:
            self._dishes_by_id[dish.id] = self._dishes[slug]
        return True
