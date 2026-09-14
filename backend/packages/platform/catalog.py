from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dish:
    slug: str
    name: str
    cuisine: str
    tags: tuple[str, ...]
    spicy_level: int
    status: str = "draft"
    sources: tuple[dict[str, str], ...] = field(default_factory=tuple)


class Catalog:
    def __init__(self, dishes: list[Dish]) -> None:
        self._dishes = {dish.slug: dish for dish in dishes}

    def list(
        self,
        *,
        cuisine: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
    ) -> list[Dish]:
        return [
            dish
            for dish in self._dishes.values()
            if dish.status == "published"
            and (not cuisine or dish.cuisine == cuisine)
            and (not keyword or keyword in dish.name)
            and (not tag or tag in dish.tags)
        ]

    def publish(self, slug: str) -> bool:
        dish = self._dishes.get(slug)
        if (
            dish is None
            or not dish.sources
            or any(not source.get("license") for source in dish.sources)
        ):
            return False
        self._dishes[slug] = Dish(**{**dish.__dict__, "status": "published"})
        return True
