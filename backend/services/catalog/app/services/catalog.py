"""目录查询与导入服务。"""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from packages.platform.catalog import Catalog, Dish

logger = logging.getLogger("catalog.service")


def load_catalog(data_dir: Path | None = None) -> tuple[Catalog, list[dict[str, str]]]:
    root = data_dir or Path(__file__).resolve().parents[4] / "data" / "catalog"
    cuisine_rows = json.loads((root / "cuisines.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "dishes.json").read_text(encoding="utf-8"))
    dishes: list[Dish] = []
    failures: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        try:
            sources = tuple(
                {
                    "url": str(source.get("url") or source.get("sourceUrl") or ""),
                    "license": str(source.get("license") or source.get("licenseName") or ""),
                    "attribution": str(source.get("attribution") or ""),
                    "reviewStatus": str(source.get("reviewStatus") or "pending"),
                    "collectedAt": str(source.get("collectedAt") or ""),
                }
                for source in row.get("sources", [])
            )
            dishes.append(
                Dish(
                    slug=str(row["slug"]),
                    name=str(row["name"]),
                    cuisine=str(row["cuisine"]),
                    tags=tuple(str(tag) for tag in row.get("tags", [])),
                    spicy_level=int(row.get("spicyLevel", 0)),
                    status=str(row.get("status", "draft")),
                    sources=sources,
                    allergens=tuple(str(x) for x in row.get("allergens", [])),
                    image_url=row.get("imageUrl"),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            failures.append({"row": str(index), "reason": str(error)})
    logger.info(
        "catalog_loaded count=%d cuisine_count=%d failure_count=%d",
        len(dishes),
        len(cuisine_rows),
        len(failures),
    )
    return Catalog(dishes), failures


def import_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """校验并返回导入结果；不在此处静默丢弃失败行。"""
    valid: list[Dish] = []
    failures: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line, row in enumerate(rows, start=1):
        slug = row.get("slug")
        sources = row.get("sources") or []
        if not isinstance(slug, str) or not slug or slug in seen:
            failures.append({"line": line, "reason": "slug 缺失或重复"})
            continue
        if not isinstance(sources, list) or any(
            not item.get("url") or not item.get("license") or not item.get("attribution")
            for item in sources
            if isinstance(item, dict)
        ):
            failures.append({"line": line, "reason": "来源必须包含 url/license/attribution"})
            continue
        seen.add(slug)
        valid.append(
            Dish(
                slug=slug,
                name=str(row.get("name", "")),
                cuisine=str(row.get("cuisine", "")),
                tags=tuple(row.get("tags", [])),
                spicy_level=int(row.get("spicyLevel", 0)),
                status=str(row.get("status", "draft")),
                sources=tuple(sources),
                allergens=tuple(row.get("allergens", [])),
            )
        )
    logger.info("catalog_import_completed imported=%d failed=%d", len(valid), len(failures))
    return {
        "imported": len(valid),
        "failed": len(failures),
        "failures": failures,
        "dishes": [asdict(dish) for dish in valid],
    }
