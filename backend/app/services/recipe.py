import json
import math
from time import perf_counter
from typing import Any, cast

import structlog
from fastapi import Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Recipe, RecipeCollect, RecipeLike, User
from app.schemas.business import RecipeRequest

logger = structlog.get_logger()
STATUS_DRAFT = 0
STATUS_PUBLISHED = 1


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "recipe",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


def _decode_json(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []


def _encode_json(value: list[Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _encode_steps(payload: RecipeRequest) -> str | None:
    if payload.steps is None:
        return None
    return _encode_json(
        [
            {"stepNo": index, **item.model_dump(by_alias=True)}
            for index, item in enumerate(payload.steps, start=1)
        ]
    )


def _difficulty_desc(value: str | None) -> str | None:
    return {"easy": "简单", "medium": "中等", "hard": "困难"}.get(value or "")


async def _flags(
    session: AsyncSession, user_id: int, recipe_id: int
) -> tuple[bool, bool, str | None]:
    liked = await session.scalar(
        select(RecipeLike.id).where(
            RecipeLike.recipe_id == recipe_id, RecipeLike.user_id == user_id
        )
    )
    collect = await session.scalar(
        select(RecipeCollect).where(
            RecipeCollect.recipe_id == recipe_id, RecipeCollect.user_id == user_id
        )
    )
    return (
        liked is not None,
        collect is not None,
        collect.create_time.isoformat() if collect else None,
    )


async def _payload(session: AsyncSession, recipe: Recipe, user_id: int) -> dict[str, object | None]:
    creator = await session.scalar(select(User).where(User.id == recipe.user_id))
    liked, collected, collect_time = await _flags(session, user_id, recipe.id)
    return {
        "id": recipe.id,
        "userId": recipe.user_id,
        "userName": creator.nick_name if creator else None,
        "userAvatar": creator.avatar_url if creator else None,
        "title": recipe.title,
        "coverUrl": recipe.cover_url,
        "description": recipe.description,
        "ingredients": _decode_json(recipe.ingredients),
        "steps": _decode_json(recipe.steps),
        "difficulty": recipe.difficulty,
        "difficultyDesc": _difficulty_desc(recipe.difficulty),
        "cookingTime": recipe.cooking_time,
        "servings": recipe.servings,
        "status": recipe.status,
        "likeCount": recipe.like_count,
        "collectCount": recipe.collect_count,
        "liked": liked,
        "collected": collected,
        "collectTime": collect_time,
        "createTime": recipe.create_time.isoformat() if recipe.create_time else None,
    }


async def _page(
    session: AsyncSession,
    user_id: int,
    conditions: list[Any],
    page_num: int,
    page_size: int,
    *,
    order_by: Any = None,
) -> dict[str, object]:
    total = int((await session.scalar(select(func.count(Recipe.id)).where(*conditions))) or 0)
    query = select(Recipe).where(*conditions)
    if order_by is None:
        query = query.order_by(Recipe.create_time.desc(), Recipe.id.desc())
    else:
        query = query.order_by(order_by, Recipe.id.desc())
    result = await session.execute(query.offset((page_num - 1) * page_size).limit(page_size))
    records = [await _payload(session, recipe, user_id) for recipe in result.scalars().all()]
    pages = math.ceil(total / page_size) if total else 0
    return {
        "records": records,
        "current": page_num,
        "size": page_size,
        "total": total,
        "pages": pages,
    }


def _validate_page(page_num: int, page_size: int) -> None:
    if page_num < 1 or page_size < 1 or page_size > 100:
        raise BusinessError(9001, "参数无效")


async def create(
    request: Request, session: AsyncSession, user_id: int, payload: RecipeRequest
) -> int:
    started = perf_counter()
    await _user(session, user_id)
    recipe = Recipe(
        user_id=user_id,
        title=payload.title.strip(),
        cover_url=payload.cover_url,
        description=payload.description,
        ingredients=_encode_json(
            [item.model_dump() for item in payload.ingredients]
            if payload.ingredients is not None
            else None
        ),
        steps=_encode_steps(payload),
        difficulty=payload.difficulty,
        cooking_time=payload.cooking_time,
        servings=payload.servings,
        status=STATUS_PUBLISHED if payload.publish else STATUS_DRAFT,
        like_count=0,
        collect_count=0,
        is_deleted=0,
    )
    session.add(recipe)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "create", "success", started)
    )
    return recipe.id


async def _owned_recipe(session: AsyncSession, user_id: int, recipe_id: int) -> Recipe:
    recipe = await session.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.is_deleted == 0)
    )
    if recipe is None:
        raise BusinessError(3101, "菜谱不存在")
    if recipe.user_id != user_id:
        raise BusinessError(3102, "无权操作该菜谱")
    return recipe


def _apply_request(recipe: Recipe, payload: RecipeRequest) -> None:
    recipe.title = payload.title.strip()
    recipe.cover_url = payload.cover_url
    recipe.description = payload.description
    if payload.ingredients is not None:
        recipe.ingredients = _encode_json([item.model_dump() for item in payload.ingredients])
    if payload.steps is not None:
        recipe.steps = _encode_steps(payload)
    recipe.difficulty = payload.difficulty
    recipe.cooking_time = payload.cooking_time
    recipe.servings = payload.servings


async def update_recipe(
    request: Request, session: AsyncSession, user_id: int, recipe_id: int, payload: RecipeRequest
) -> None:
    started = perf_counter()
    recipe = await _owned_recipe(session, user_id, recipe_id)
    _apply_request(recipe, payload)
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "update", "success", started)
    )


async def delete_recipe(
    request: Request, session: AsyncSession, user_id: int, recipe_id: int
) -> None:
    started = perf_counter()
    recipe = await _owned_recipe(session, user_id, recipe_id)
    recipe.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "delete", "success", started)
    )


async def publish(request: Request, session: AsyncSession, user_id: int, recipe_id: int) -> None:
    started = perf_counter()
    recipe = await _owned_recipe(session, user_id, recipe_id)
    if recipe.status == STATUS_PUBLISHED:
        raise BusinessError(3103, "菜谱已发布")
    recipe.status = STATUS_PUBLISHED
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "publish", "success", started)
    )


async def detail(
    request: Request, session: AsyncSession, user_id: int, recipe_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    recipe = await session.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.is_deleted == 0)
    )
    if recipe is None or (recipe.status == STATUS_DRAFT and recipe.user_id != user_id):
        raise BusinessError(3101, "菜谱不存在")
    result = await _payload(session, recipe, user_id)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "detail", "success", started)
    )
    return result


async def my_recipes(
    request: Request, session: AsyncSession, user_id: int, page_num: int, page_size: int
) -> dict[str, object]:
    started = perf_counter()
    _validate_page(page_num, page_size)
    result = await _page(
        session,
        user_id,
        [Recipe.user_id == user_id, Recipe.is_deleted == 0],
        page_num,
        page_size,
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "my", "success", started)
    )
    return result


async def couple_recipes(
    request: Request, session: AsyncSession, user_id: int, page_num: int, page_size: int
) -> dict[str, object]:
    started = perf_counter()
    _validate_page(page_num, page_size)
    user = await _user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    ids = select(User.id).where(User.couple_id == user.couple_id, User.is_deleted == 0)
    result = await _page(
        session,
        user_id,
        [Recipe.user_id.in_(ids), Recipe.status == STATUS_PUBLISHED, Recipe.is_deleted == 0],
        page_num,
        page_size,
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "couple", "success", started)
    )
    return result


async def recommended(
    request: Request, session: AsyncSession, user_id: int, page_num: int, page_size: int
) -> dict[str, object]:
    started = perf_counter()
    _validate_page(page_num, page_size)
    result = await _page(
        session,
        user_id,
        [Recipe.status == STATUS_PUBLISHED, Recipe.is_deleted == 0],
        page_num,
        page_size,
        order_by=Recipe.like_count.desc(),
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "recommended", "success", started)
    )
    return result


async def search(
    request: Request,
    session: AsyncSession,
    user_id: int,
    keyword: str | None,
    page_num: int,
    page_size: int,
) -> dict[str, object]:
    started = perf_counter()
    _validate_page(page_num, page_size)
    conditions: list[Any] = [Recipe.status == STATUS_PUBLISHED, Recipe.is_deleted == 0]
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append((Recipe.title.like(pattern)) | (Recipe.description.like(pattern)))
    result = await _page(session, user_id, conditions, page_num, page_size)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "search", "success", started)
    )
    return result


async def collected(
    request: Request, session: AsyncSession, user_id: int, page_num: int, page_size: int
) -> dict[str, object]:
    started = perf_counter()
    _validate_page(page_num, page_size)
    conditions = [RecipeCollect.user_id == user_id, Recipe.is_deleted == 0]
    total = int(
        (
            await session.scalar(
                select(func.count(RecipeCollect.id))
                .select_from(RecipeCollect)
                .join(Recipe, Recipe.id == RecipeCollect.recipe_id)
                .where(*conditions)
            )
        )
        or 0
    )
    rows = await session.execute(
        select(Recipe)
        .join(RecipeCollect, Recipe.id == RecipeCollect.recipe_id)
        .where(*conditions)
        .order_by(RecipeCollect.create_time.desc(), RecipeCollect.id.desc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
    )
    result = {
        "records": [await _payload(session, recipe, user_id) for recipe in rows.scalars().all()],
        "current": page_num,
        "size": page_size,
        "total": total,
        "pages": math.ceil(total / page_size) if total else 0,
    }
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "collected", "success", started)
    )
    return result


async def _published_recipe(session: AsyncSession, recipe_id: int) -> Recipe:
    recipe = await session.scalar(
        select(Recipe).where(
            Recipe.id == recipe_id, Recipe.status == STATUS_PUBLISHED, Recipe.is_deleted == 0
        )
    )
    if recipe is None:
        raise BusinessError(3101, "菜谱不存在")
    return recipe


async def _toggle_relation(
    request: Request,
    session: AsyncSession,
    user_id: int,
    recipe_id: int,
    relation: type[RecipeLike] | type[RecipeCollect],
    counter: Any,
    operation: str,
    enabled: bool,
) -> None:
    started = perf_counter()
    await _published_recipe(session, recipe_id)
    if enabled:
        session.add(relation(recipe_id=recipe_id, user_id=user_id))
        try:
            await session.flush()
        except IntegrityError as error:
            await session.rollback()
            await logger.awarning(
                "business_operation_rejected",
                **_log_fields(request, operation, "rejected", started, "RELATION_EXISTS"),
            )
            raise BusinessError(3104, "操作已存在") from error
        await session.execute(
            update(Recipe)
            .where(Recipe.id == recipe_id)
            .values(**{counter: getattr(Recipe, counter) + 1})
        )
    else:
        deleted = cast(
            CursorResult[Any],
            await session.execute(
                delete(relation).where(
                    relation.recipe_id == recipe_id,
                    relation.user_id == user_id,
                )
            ),
        )
        if deleted.rowcount != 1:
            await session.rollback()
            await logger.awarning(
                "business_operation_rejected",
                **_log_fields(request, operation, "rejected", started, "RELATION_MISSING"),
            )
            raise BusinessError(3105, "操作不存在")
        await session.execute(
            update(Recipe)
            .where(Recipe.id == recipe_id)
            .values(**{counter: func.greatest(getattr(Recipe, counter) - 1, 0)})
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )


async def like(request: Request, session: AsyncSession, user_id: int, recipe_id: int) -> None:
    await _toggle_relation(
        request, session, user_id, recipe_id, RecipeLike, "like_count", "like", True
    )


async def unlike(request: Request, session: AsyncSession, user_id: int, recipe_id: int) -> None:
    await _toggle_relation(
        request, session, user_id, recipe_id, RecipeLike, "like_count", "unlike", False
    )


async def collect(request: Request, session: AsyncSession, user_id: int, recipe_id: int) -> None:
    await _toggle_relation(
        request, session, user_id, recipe_id, RecipeCollect, "collect_count", "collect", True
    )


async def uncollect(request: Request, session: AsyncSession, user_id: int, recipe_id: int) -> None:
    await _toggle_relation(
        request, session, user_id, recipe_id, RecipeCollect, "collect_count", "uncollect", False
    )
