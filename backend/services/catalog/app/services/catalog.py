"""SQLAlchemy 驱动的菜品目录、授权资料和导入服务。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import structlog
from sqlalchemy import Select, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import CatalogCuisine, CatalogDish, CatalogDishSource, CatalogImportBatch
from packages.platform.catalog import Dish

if TYPE_CHECKING:
    from packages.platform.catalog import Catalog

logger = structlog.get_logger()
_SOURCE_STATUSES = frozenset({"pending", "approved", "rejected"})


class CatalogNotFoundError(ValueError):
    """请求的菜品或授权来源不存在。"""


class CatalogNotPublishableError(ValueError):
    """菜品缺少必要价格或有效授权资料，不能对用户可见。"""


@dataclass(frozen=True)
class ImportPlan:
    dishes: tuple[Dish, ...]
    cuisine_names: dict[str, str]
    failures: list[dict[str, object]]


@dataclass(frozen=True)
class CatalogDishPage:
    items: list[Dish]
    total: int


class CatalogStore(Protocol):
    """目录 HTTP 层使用的窄持久化接口。"""

    async def list_cuisines(self, session: AsyncSession) -> list[dict[str, object]]: ...

    async def list_dishes(
        self,
        session: AsyncSession,
        *,
        cuisine: str | None,
        keyword: str | None,
        tag: str | None,
        spicy_level: int | None,
        allergen: str | None,
        page: int = 1,
        page_size: int = 20,
    ) -> CatalogDishPage | list[Dish]: ...

    async def get_published_dish(
        self, session: AsyncSession, dish_reference: str
    ) -> Dish | None: ...

    async def import_catalog(
        self, session: AsyncSession, rows: list[dict[str, object]], *, source_name: str
    ) -> dict[str, object]: ...

    async def review_source(
        self, session: AsyncSession, *, dish_reference: str, source_id: int, approved: bool
    ) -> dict[str, object]: ...

    async def publish_dish(
        self, session: AsyncSession, *, dish_reference: str
    ) -> dict[str, object]: ...


def _optional_dish_id(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("菜品 ID 必须为正整数")
    try:
        dish_id = int(value)
    except ValueError as error:
        raise ValueError("菜品 ID 必须为正整数") from error
    if dish_id < 1:
        raise ValueError("菜品 ID 必须为正整数")
    return dish_id


def _optional_price(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("菜品价格无效") from error
    exponent = price.as_tuple().exponent
    if not price.is_finite() or price < 0 or (isinstance(exponent, int) and exponent < -2):
        raise ValueError("菜品价格无效")
    if price > Decimal("99999999.99"):
        raise ValueError("菜品价格无效")
    return price.quantize(Decimal("0.01"))


def _date_value(value: object, *, field: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} 格式无效")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} 格式无效") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} 必须包含时区")
    return parsed.astimezone(UTC).replace(tzinfo=None)


def _required_text(value: object, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 格式无效")
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise ValueError(f"{field} 格式无效")
    return normalized


def _text_list(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} 必须为列表")
    return tuple(_required_text(item, field=field, max_length=64) for item in value)


def _sources(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("来源必须为非空列表")
    normalized: list[dict[str, object]] = []
    source_urls: set[str] = set()
    for source in value:
        if not isinstance(source, dict):
            raise ValueError("来源格式无效")
        url = _required_text(
            source.get("url") or source.get("sourceUrl"), field="来源 URL", max_length=1024
        )
        if url in source_urls:
            raise ValueError("来源 URL 重复")
        source_urls.add(url)
        supplied_review_status = str(source.get("reviewStatus") or "pending")
        if supplied_review_status not in _SOURCE_STATUSES:
            raise ValueError("来源审核状态无效")
        normalized.append(
            {
                "url": url,
                "license": _required_text(
                    source.get("license") or source.get("licenseName"),
                    field="来源授权",
                    max_length=128,
                ),
                "attribution": _required_text(
                    source.get("attribution"), field="来源署名", max_length=512
                ),
                # 导入人声明的状态不能替代本服务的管理员审核。
                "reviewStatus": "pending",
                "collectedAt": _date_value(source.get("collectedAt"), field="采集时间"),
                "licenseExpiresAt": _date_value(
                    source.get("licenseExpiresAt"), field="授权到期时间"
                ),
            }
        )
    return tuple(normalized)


def _cuisine_name(row: dict[str, object], cuisine_slug: str) -> str:
    provided = row.get("cuisineName")
    return (
        _required_text(provided, field="菜系名称", max_length=128)
        if provided is not None
        else cuisine_slug
    )


def load_catalog(data_dir: Path | None = None) -> tuple[Catalog, list[dict[str, str]]]:
    """读取离线 JSON 草稿，供校验工具使用，不参与在线请求。

    JSON 中的菜品不会被自动写入数据库；即便其中声明 ``published``，缺少数字 ID、价格或
    审核来源时，领域模型也会将其视为不可见。这使离线数据集可以继续作为待核验工作台。
    """
    from packages.platform.catalog import Catalog

    root = data_dir or Path(__file__).resolve().parents[4] / "data" / "catalog"
    cuisine_rows = json.loads((root / "cuisines.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "dishes.json").read_text(encoding="utf-8"))
    dishes: list[Dish] = []
    failures: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, dict):
                raise ValueError("菜品行必须为对象")
            raw_sources = row.get("sources")
            if raw_sources is None or not isinstance(raw_sources, list):
                raise ValueError("来源必须为列表")
            normalized_sources = tuple(
                {
                    "url": str(source.get("url") or source.get("sourceUrl") or ""),
                    "license": str(source.get("license") or source.get("licenseName") or ""),
                    "attribution": str(source.get("attribution") or ""),
                    "reviewStatus": str(source.get("reviewStatus") or "pending"),
                    "collectedAt": str(source.get("collectedAt") or ""),
                    "licenseExpiresAt": str(source.get("licenseExpiresAt") or ""),
                }
                for source in raw_sources
                if isinstance(source, dict)
            )
            dishes.append(
                Dish(
                    slug=str(row["slug"]),
                    name=str(row["name"]),
                    cuisine=str(row["cuisine"]),
                    tags=tuple(str(tag) for tag in row.get("tags", [])),
                    spicy_level=int(row.get("spicyLevel", 0)),
                    status=str(row.get("status", "draft")),
                    sources=normalized_sources,
                    allergens=tuple(str(value) for value in row.get("allergens", [])),
                    image_url=row.get("imageUrl"),
                    id=_optional_dish_id(row.get("id", row.get("dishId"))),
                    unit_price=_optional_price(row.get("unitPrice", row.get("price"))),
                )
            )
        except (InvalidOperation, KeyError, TypeError, ValueError) as error:
            failures.append({"row": str(index), "reason": str(error)})
    catalog = Catalog(dishes)
    logger.info(
        "catalog_offline_loaded",
        module="catalog",
        operation="load_offline",
        result="success",
        dishCount=len(dishes),
        cuisineCount=len(cuisine_rows),
        publicDishCount=len(catalog.list()),
        failureCount=len(failures),
    )
    return catalog, failures


def _build_import_plan(rows: list[dict[str, object]]) -> ImportPlan:
    valid: list[Dish] = []
    failures: list[dict[str, object]] = []
    cuisine_names: dict[str, str] = {}
    seen_slugs: set[str] = set()
    seen_ids: set[int] = set()
    for line, row in enumerate(rows, start=1):
        try:
            slug = _required_text(row.get("slug"), field="slug", max_length=128)
            if slug in seen_slugs:
                raise ValueError("slug 缺失或重复")
            dish_id = _optional_dish_id(row.get("id", row.get("dishId")))
            unit_price = _optional_price(row.get("unitPrice", row.get("price")))
            if dish_id is None or unit_price is None:
                raise ValueError("菜品必须包含数字 ID 和价格")
            if dish_id in seen_ids:
                raise ValueError("菜品 ID 重复")
            cuisine = _required_text(row.get("cuisine"), field="菜系", max_length=64)
            spicy_level = row.get("spicyLevel", 0)
            if (
                isinstance(spicy_level, bool)
                or not isinstance(spicy_level, int)
                or not 0 <= spicy_level <= 5
            ):
                raise ValueError("辣度必须为 0 到 5 的整数")
            image_url = row.get("imageUrl")
            if image_url is not None:
                image_url = _required_text(image_url, field="图片地址", max_length=512)
            valid.append(
                Dish(
                    slug=slug,
                    name=_required_text(row.get("name"), field="菜品名称", max_length=128),
                    cuisine=cuisine,
                    tags=_text_list(row.get("tags"), field="标签"),
                    spicy_level=spicy_level,
                    status="draft",
                    sources=_sources(row.get("sources")),  # type: ignore[arg-type]
                    allergens=_text_list(row.get("allergens"), field="过敏原"),
                    image_url=image_url,
                    id=dish_id,
                    unit_price=unit_price,
                )
            )
            cuisine_names.setdefault(cuisine, _cuisine_name(row, cuisine))
            seen_slugs.add(slug)
            seen_ids.add(dish_id)
        except (InvalidOperation, TypeError, ValueError) as error:
            failures.append({"line": line, "reason": str(error)})
    return ImportPlan(tuple(valid), cuisine_names, failures)


def import_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """校验导入内容，持久化由 ``SqlAlchemyCatalogStore`` 在同一事务完成。"""

    plan = _build_import_plan(rows)
    logger.info(
        "catalog_import_validated",
        module="catalog",
        operation="validate_import",
        result="success",
        imported=len(plan.dishes),
        failed=len(plan.failures),
    )
    return {
        "imported": len(plan.dishes),
        "failed": len(plan.failures),
        "failures": plan.failures,
        "dishes": [asdict(dish) for dish in plan.dishes],
    }


def _source_is_authorized(source: CatalogDishSource) -> bool:
    if (
        not source.source_url
        or not source.license_name
        or not source.attribution
        or source.review_status != "approved"
    ):
        return False
    expires = source.license_expires_at
    return expires is None or expires > datetime.now(UTC).replace(tzinfo=None)


def _source_url_fingerprint(source_url: str) -> str:
    """为 MySQL 的窄唯一索引提供 URL 的确定性指纹，原文仍完整存储。"""

    return sha256(source_url.encode("utf-8")).hexdigest()


def _record_is_publishable(
    record: CatalogDish, sources: list[CatalogDishSource] | None = None
) -> bool:
    source_rows = record.sources if sources is None else sources
    return (
        record.id > 0
        and bool(record.name.strip())
        and record.unit_price is not None
        and record.unit_price.is_finite()
        and record.unit_price >= Decimal("0")
        and bool(source_rows)
        and all(_source_is_authorized(source) for source in source_rows)
    )


def _date_payload(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def _dish_from_record(record: CatalogDish) -> Dish:
    tags = json.loads(record.tags_json)
    allergens = json.loads(record.allergens_json)
    if not isinstance(tags, list) or not isinstance(allergens, list):
        raise ValueError("目录数据格式无效")
    return Dish(
        id=record.id,
        slug=record.slug,
        name=record.name,
        cuisine=record.cuisine_slug,
        tags=tuple(str(value) for value in tags),
        spicy_level=record.spicy_level,
        status=record.status,
        sources=tuple(
            {
                "id": str(source.id),
                "url": source.source_url,
                "license": source.license_name,
                "attribution": source.attribution,
                "reviewStatus": source.review_status,
                "collectedAt": _date_payload(source.collected_at) or "",
                "licenseExpiresAt": _date_payload(source.license_expires_at) or "",
            }
            for source in record.sources
        ),
        allergens=tuple(str(value) for value in allergens),
        image_url=record.image_url,
        unit_price=record.unit_price,
    )


def _published_statement() -> Select[tuple[CatalogDish]]:
    return (
        select(CatalogDish)
        .where(CatalogDish.status == "published")
        .options(selectinload(CatalogDish.sources))
    )


def _dish_statement(dish_reference: str) -> Select[tuple[CatalogDish]]:
    statement = select(CatalogDish).options(selectinload(CatalogDish.sources))
    if dish_reference.isdecimal():
        return statement.where(CatalogDish.id == int(dish_reference))
    return statement.where(CatalogDish.slug == dish_reference)


class SqlAlchemyCatalogStore:
    """目录服务唯一的运行时主数据存储。"""

    async def list_cuisines(self, session: AsyncSession) -> list[dict[str, object]]:
        rows = await session.scalars(
            select(CatalogCuisine)
            .where(CatalogCuisine.status == "active")
            .order_by(CatalogCuisine.sort_order, CatalogCuisine.id)
        )
        return [
            {"id": cuisine.id, "slug": cuisine.slug, "name": cuisine.name} for cuisine in rows.all()
        ]

    async def list_dishes(
        self,
        session: AsyncSession,
        *,
        cuisine: str | None,
        keyword: str | None,
        tag: str | None,
        spicy_level: int | None,
        allergen: str | None,
        page: int = 1,
        page_size: int = 20,
    ) -> CatalogDishPage:
        filters = [CatalogDish.status == "published"]
        now = datetime.now(UTC).replace(tzinfo=None)
        authorized_source = (
            (CatalogDishSource.review_status == "approved")
            & CatalogDishSource.source_url.is_not(None)
            & CatalogDishSource.license_name.is_not(None)
            & CatalogDishSource.attribution.is_not(None)
            & (
                CatalogDishSource.license_expires_at.is_(None)
                | (CatalogDishSource.license_expires_at > now)
            )
        )
        unauthorized_source = ~authorized_source
        filters.extend(
            [
                CatalogDish.id > 0,
                func.trim(CatalogDish.name) != "",
                CatalogDish.unit_price.is_not(None),
                CatalogDish.unit_price >= Decimal("0"),
                exists(
                    select(CatalogDishSource.id).where(
                        CatalogDishSource.dish_id == CatalogDish.id,
                        authorized_source,
                    )
                ),
                ~exists(
                    select(CatalogDishSource.id).where(
                        CatalogDishSource.dish_id == CatalogDish.id,
                        unauthorized_source,
                    )
                ),
            ]
        )
        if cuisine:
            filters.append(CatalogDish.cuisine_slug == cuisine)
        if keyword:
            filters.append(CatalogDish.name.ilike(f"%{keyword}%"))
        if spicy_level is not None:
            filters.append(CatalogDish.spicy_level == spicy_level)
        if tag:
            filters.append(CatalogDish.tags_json.contains(f'"{tag}"'))
        if allergen:
            filters.append(~CatalogDish.allergens_json.contains(f'"{allergen}"'))
        total = int(
            await session.scalar(select(func.count(CatalogDish.id)).where(*filters)) or 0
        )
        bounded_statement = (
            _published_statement()
            .where(*filters[1:])
            .order_by(CatalogDish.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = await session.scalars(bounded_statement)
        dishes = [_dish_from_record(row) for row in rows.all() if _record_is_publishable(row)]
        return CatalogDishPage(items=dishes, total=total)

    async def get_published_dish(self, session: AsyncSession, dish_reference: str) -> Dish | None:
        record = await session.scalar(
            _published_statement().where(
                CatalogDish.id == int(dish_reference)
                if dish_reference.isdecimal()
                else CatalogDish.slug == dish_reference
            )
        )
        if record is None or not _record_is_publishable(record):
            return None
        return _dish_from_record(record)

    async def import_catalog(
        self, session: AsyncSession, rows: list[dict[str, object]], *, source_name: str
    ) -> dict[str, object]:
        plan = _build_import_plan(rows)
        failures = list(plan.failures)
        ids = [dish.id for dish in plan.dishes if dish.id is not None]
        slugs = [dish.slug for dish in plan.dishes]
        existing_ids = (
            set(
                (await session.scalars(select(CatalogDish.id).where(CatalogDish.id.in_(ids)))).all()
            )
            if ids
            else set()
        )
        existing_slugs = (
            set(
                (
                    await session.scalars(
                        select(CatalogDish.slug).where(CatalogDish.slug.in_(slugs))
                    )
                ).all()
            )
            if slugs
            else set()
        )
        persisted: list[Dish] = []
        for line, dish in enumerate(plan.dishes, start=1):
            if dish.id in existing_ids or dish.slug in existing_slugs:
                failures.append({"line": line, "reason": "菜品 ID 或 slug 已存在"})
            else:
                persisted.append(dish)
        if persisted:
            existing_cuisines = set(
                (
                    await session.scalars(
                        select(CatalogCuisine.slug).where(
                            CatalogCuisine.slug.in_([dish.cuisine for dish in persisted])
                        )
                    )
                ).all()
            )
            for cuisine_slug in {dish.cuisine for dish in persisted} - existing_cuisines:
                session.add(
                    CatalogCuisine(slug=cuisine_slug, name=plan.cuisine_names[cuisine_slug])
                )
            for dish in persisted:
                session.add(
                    CatalogDish(
                        id=dish.id,
                        slug=dish.slug,
                        name=dish.name,
                        cuisine_slug=dish.cuisine,
                        tags_json=json.dumps(list(dish.tags), ensure_ascii=False),
                        allergens_json=json.dumps(list(dish.allergens), ensure_ascii=False),
                        spicy_level=dish.spicy_level,
                        status="draft",
                        image_url=dish.image_url,
                        unit_price=dish.unit_price,
                        sources=[
                            CatalogDishSource(
                                source_url=str(source["url"]),
                                source_url_fingerprint=_source_url_fingerprint(str(source["url"])),
                                license_name=str(source["license"]),
                                attribution=str(source["attribution"]),
                                review_status=str(source["reviewStatus"]),
                                collected_at=source["collectedAt"],
                                license_expires_at=source["licenseExpiresAt"],
                            )
                            for source in dish.sources
                        ],
                    )
                )
        batch = CatalogImportBatch(
            source_name=source_name,
            imported_count=len(persisted),
            failed_count=len(failures),
            failure_report_json=json.dumps(failures, ensure_ascii=False),
        )
        session.add(batch)
        await session.flush()
        await logger.ainfo(
            "catalog_import_persisted",
            module="catalog",
            operation="import",
            result="success",
            batchId=batch.id,
            imported=len(persisted),
            failed=len(failures),
        )
        return {
            "batchId": batch.id,
            "imported": len(persisted),
            "failed": len(failures),
            "failures": failures,
        }

    async def review_source(
        self, session: AsyncSession, *, dish_reference: str, source_id: int, approved: bool
    ) -> dict[str, object]:
        dish = await session.scalar(_dish_statement(dish_reference).with_for_update())
        if dish is None:
            raise CatalogNotFoundError("菜品不存在")
        source = await session.scalar(
            select(CatalogDishSource)
            .where(CatalogDishSource.id == source_id, CatalogDishSource.dish_id == dish.id)
            .with_for_update()
        )
        if source is None:
            raise CatalogNotFoundError("授权来源不存在")
        source.review_status = "approved" if approved else "rejected"
        await session.flush()
        await logger.ainfo(
            "catalog_source_reviewed",
            module="catalog",
            operation="review_source",
            result="success",
            dishId=dish.id,
            sourceId=source.id,
            reviewStatus=source.review_status,
        )
        return {"dishId": dish.id, "sourceId": source.id, "reviewStatus": source.review_status}

    async def publish_dish(
        self, session: AsyncSession, *, dish_reference: str
    ) -> dict[str, object]:
        record = await session.scalar(_dish_statement(dish_reference).with_for_update())
        if record is None:
            raise CatalogNotFoundError("菜品不存在")
        sources = list(
            (
                await session.scalars(
                    select(CatalogDishSource)
                    .where(CatalogDishSource.dish_id == record.id)
                    .with_for_update()
                )
            ).all()
        )
        if not _record_is_publishable(record, sources):
            raise CatalogNotPublishableError("菜品来源未审核或价格无效")
        record.status = "published"
        await session.flush()
        await logger.ainfo(
            "catalog_dish_published",
            module="catalog",
            operation="publish",
            result="success",
            dishId=record.id,
        )
        return {"id": record.id, "dishId": record.id, "slug": record.slug, "status": record.status}


__all__ = [
    "CatalogDishPage",
    "CatalogNotFoundError",
    "CatalogNotPublishableError",
    "CatalogStore",
    "SqlAlchemyCatalogStore",
    "load_catalog",
    "import_rows",
]
