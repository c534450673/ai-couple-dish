from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.schemas.business import RecipeRequest
from app.services import recipe as recipe_service

router = APIRouter(prefix="/recipe", tags=["菜谱模块"])


@router.post("/create")
async def create(
    request: Request,
    payload: RecipeRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.create(request, session, user_id, payload),
    }


@router.put("/update/{recipeId}")
async def update(
    request: Request,
    recipeId: int,
    payload: RecipeRequest,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.update_recipe(request, session, user_id, recipeId, payload)
    return {"code": 200, "message": "更新成功", "data": None}


@router.delete("/delete/{recipeId}")
async def delete(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.delete_recipe(request, session, user_id, recipeId)
    return {"code": 200, "message": "删除成功", "data": None}


@router.post("/publish/{recipeId}")
async def publish(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.publish(request, session, user_id, recipeId)
    return {"code": 200, "message": "操作成功", "data": None}


@router.get("/detail/{recipeId}")
async def detail(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.detail(request, session, user_id, recipeId),
    }


@router.get("/my")
async def my(
    request: Request,
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.my_recipes(request, session, user_id, page_num, page_size),
    }


@router.get("/couple")
async def couple(
    request: Request,
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.couple_recipes(request, session, user_id, page_num, page_size),
    }


@router.get("/recommended")
async def recommended(
    request: Request,
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.recommended(request, session, user_id, page_num, page_size),
    }


@router.get("/search")
async def search(
    request: Request,
    keyword: str | None = Query(default=None, max_length=128),
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.search(
            request, session, user_id, keyword, page_num, page_size
        ),
    }


@router.get("/collected")
async def collected(
    request: Request,
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=100),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "code": 200,
        "message": "操作成功",
        "data": await recipe_service.collected(request, session, user_id, page_num, page_size),
    }


@router.post("/like/{recipeId}")
async def like(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.like(request, session, user_id, recipeId)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/like/{recipeId}")
async def unlike(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.unlike(request, session, user_id, recipeId)
    return {"code": 200, "message": "操作成功", "data": None}


@router.post("/collect/{recipeId}")
async def collect(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.collect(request, session, user_id, recipeId)
    return {"code": 200, "message": "操作成功", "data": None}


@router.delete("/collect/{recipeId}")
async def uncollect(
    request: Request,
    recipeId: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    await recipe_service.uncollect(request, session, user_id, recipeId)
    return {"code": 200, "message": "操作成功", "data": None}
