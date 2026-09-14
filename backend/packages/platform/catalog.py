from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List


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


class Catalog:
    def __init__(self, dishes: list[Dish]) -> None:
        self._dishes = {dish.slug: dish for dish in dishes}

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
            if (include_draft or dish.status == "published")
            and (not cuisine or dish.cuisine == cuisine)
            and (not keyword or keyword.lower() in dish.name.lower())
            and (not tag or tag in dish.tags)
            and (spicy_level is None or dish.spicy_level == spicy_level)
            and (not allergen or allergen not in dish.allergens)
        ]

    def get(self, slug: str) -> Dish | None:
        return self._dishes.get(slug)

    def list_cuisines(self) -> List[str]:
        return sorted({dish.cuisine for dish in self._dishes.values()})

    def publish(self, slug: str) -> bool:
        dish = self._dishes.get(slug)
        if (
            dish is None
            or not dish.sources
            or any(
                not source.get("license")
                or not source.get("url")
                or source.get("reviewStatus", "pending") != "approved"
                for source in dish.sources
            )
        ):
            return False
        self._dishes[slug] = replace(dish, status="published")
        return True
