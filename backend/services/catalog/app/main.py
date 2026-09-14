import json
from pathlib import Path

from fastapi import Body, HTTPException, Query, Request

from packages.platform.service import create_service_app

from .services.catalog import import_rows, load_catalog

app = create_service_app("catalog")
_catalog, _load_failures = load_catalog()
app.state.catalog = _catalog
app.state.catalog_load_failures = _load_failures
_CUISINES = json.loads(
    (Path(__file__).resolve().parents[3] / "data/catalog/cuisines.json").read_text(encoding="utf-8")
)


def _envelope(data: object) -> dict[str, object]:
    return {"code": 200, "message": "操作成功", "data": data}


@app.get("/api/catalog/cuisines")
async def cuisines() -> dict[str, object]:
    return _envelope(_CUISINES)


@app.get("/api/catalog/dishes")
async def dishes(
    cuisine: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    spicy_level: int | None = Query(default=None, alias="spicyLevel", ge=0, le=5),
    allergen: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> dict[str, object]:
    matched = app.state.catalog.list(
        cuisine=cuisine, keyword=keyword, tag=tag, spicy_level=spicy_level, allergen=allergen
    )
    start = (page - 1) * page_size
    data = [
        {
            "slug": dish.slug,
            "name": dish.name,
            "cuisine": dish.cuisine,
            "tags": list(dish.tags),
            "spicyLevel": dish.spicy_level,
            "allergens": list(dish.allergens),
            "status": dish.status,
            "imageUrl": dish.image_url,
        }
        for dish in matched[start : start + page_size]
    ]
    return _envelope({"items": data, "page": page, "pageSize": page_size, "total": len(matched)})


@app.get("/api/catalog/dishes/{slug}")
async def dish_detail(slug: str) -> dict[str, object]:
    dish = app.state.catalog.get(slug)
    if dish is None or dish.status != "published":
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "菜品不存在", "data": None}
        )
    return _envelope(
        {
            "slug": dish.slug,
            "name": dish.name,
            "cuisine": dish.cuisine,
            "tags": list(dish.tags),
            "spicyLevel": dish.spicy_level,
            "allergens": list(dish.allergens),
            "status": dish.status,
            "imageUrl": dish.image_url,
            "sources": list(dish.sources),
        }
    )


@app.post("/api/catalog/dishes/{slug}/publish")
async def publish_dish(slug: str, request: Request) -> dict[str, object]:
    # 管理员服务会在网关层鉴权；此处要求显式 admin 身份，避免误发布。
    role = request.headers.get("X-Admin-Role")
    if role != "admin":
        raise HTTPException(
            status_code=403, detail={"code": 403, "message": "无权限", "data": None}
        )
    if not app.state.catalog.publish(slug):
        raise HTTPException(
            status_code=422, detail={"code": 422, "message": "菜品来源未审核", "data": None}
        )
    return _envelope({"slug": slug, "status": "published"})


@app.post("/api/catalog/import")
async def import_catalog(
    request: Request,
    payload: list[dict[str, object]] = Body(...),  # noqa: B008
) -> dict[str, object]:
    if request.headers.get("X-Admin-Role") != "admin":
        raise HTTPException(
            status_code=403, detail={"code": 403, "message": "无权限", "data": None}
        )
    result = import_rows(payload)
    return _envelope(
        {"imported": result["imported"], "failed": result["failed"], "failures": result["failures"]}
    )
