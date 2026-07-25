import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import decode_access_token
from app.core.config import Settings
from app.db.models import CoupleMenu, Recipe, RecipeCollect, RecipeLike, User
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient
from app.schemas.business import (
    BindCoupleRequest,
    GenerateCodeRequest,
    PhoneLoginRequest,
    WechatLoginRequest,
)
from app.services import couple as couple_service
from app.services import notification as notification_service
from app.services import user as user_service

SECRET = "b" * 64


def _reset_schema(connection: Connection) -> None:
    table_names = inspect(connection).get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in table_names:
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    schema_path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = schema_path.read_text()
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_business_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def request_context(redis: RedisClient) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(request_id="6ec4a2c3-42df-46a3-bf11-44fbf85a3380"),
        app=SimpleNamespace(state=SimpleNamespace(redis=redis, settings=settings())),
    )


@pytest.mark.integration
async def test_user_couple_notification_flow_uses_real_mysql_and_redis(
    mysql_business_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_business_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request = request_context(redis)
            first = await user_service.wechat_login(
                request,
                session,
                WechatLoginRequest(code="integration-openid-one", nickName="一号"),
            )
            second = await user_service.wechat_login(
                request,
                session,
                WechatLoginRequest(code="integration-openid-two", nickName="二号"),
            )
            first_id = int(first["userInfo"]["id"])
            second_id = int(second["userInfo"]["id"])

            code = await couple_service.generate_code(
                request,
                session,
                first_id,
                GenerateCodeRequest(loveStartDate=date.today()),
            )
            relation = await couple_service.bind(
                request,
                session,
                second_id,
                BindCoupleRequest(coupleCode=code),
            )

            assert relation["status"] == 1
            assert relation["partner"]["id"] == first_id
            assert await couple_service.validate_code(request, code) is False
            assert (await couple_service.get_info(session, first_id))["partner"]["id"] == second_id

            notifications = await notification_service.list_notifications(
                request, session, first_id, None, 1, 20
            )
            assert len(notifications) == 1
            assert notifications[0]["relatedType"] == "couple"
            assert await notification_service.unread_count(request, session, first_id) == 1
            await notification_service.mark_read(
                request, session, first_id, int(notifications[0]["id"])
            )
            assert await notification_service.unread_count(request, session, first_id) == 0

            claims = decode_access_token(first["token"], SECRET)
            await user_service.logout(request, session, first_id, claims)
            assert await redis.raw.exists(f"logout:blacklist:{claims.jti}") == 1
    finally:
        await redis.close()


@pytest.mark.integration
async def test_phone_verification_log_does_not_contain_phone_or_code(
    mysql_business_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_business_engine, expire_on_commit=False)
    request = request_context(redis)
    try:
        await redis.raw.set("user:verify:code:13800138000", "123456", ex=60)
        with capture_logs() as logs:
            async with session_factory() as session:
                session.add(
                    User(
                        openid="phone_13800138000",
                        phone="13800138000",
                        nick_name="测试用户",
                        member_level=0,
                        status=0,
                        is_deleted=0,
                    )
                )
                await session.commit()
                await user_service.phone_login(
                    request,
                    session,
                    PhoneLoginRequest(phone="13800138000", verifyCode="123456"),
                )
        assert "13800138000" not in str(logs)
        assert "123456" not in str(logs)
    finally:
        await redis.close()


@pytest.mark.integration
async def test_http_business_routes_keep_spring_envelopes(
    mysql_business_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_business_engine, expire_on_commit=False)
    app = create_app(settings())
    app.state.redis = redis

    async def session_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first_response = await client.post(
                "/api/user/login", json={"code": "http-openid-one", "nickName": "甲"}
            )
            second_response = await client.post(
                "/api/user/login", json={"code": "http-openid-two", "nickName": "乙"}
            )
            assert first_response.status_code == second_response.status_code == 200
            first_token = first_response.json()["data"]["token"]
            second_token = second_response.json()["data"]["token"]
            code_response = await client.post(
                "/api/couple/generateCode",
                headers={"Authorization": f"Bearer {first_token}"},
                json={"loveStartDate": date.today().isoformat()},
            )
            assert code_response.json()["code"] == 200
            bind_response = await client.post(
                "/api/couple/bind",
                headers={"Authorization": f"Bearer {second_token}"},
                json={"coupleCode": code_response.json()["data"]},
            )
            assert bind_response.json()["code"] == 200
            assert bind_response.json()["data"]["status"] == 1
            notifications = await client.get(
                "/api/notification/list",
                headers={"Authorization": f"Bearer {first_token}"},
            )
            assert notifications.json()["code"] == 200
            assert notifications.json()["data"][0]["relatedType"] == "couple"
    finally:
        await redis.close()


@pytest.mark.integration
async def test_menu_and_recipe_routes_use_real_mysql_and_keep_logs_redacted(
    mysql_business_engine: AsyncEngine, redis_url: str
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_business_engine, expire_on_commit=False)
    app = create_app(settings())
    app.state.redis = redis

    async def session_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    restaurant_name = "integration-private-restaurant"
    recipe_title = "integration-private-recipe"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                first = await client.post(
                    "/api/user/login", json={"code": "food-openid-one", "nickName": "甲"}
                )
                second = await client.post(
                    "/api/user/login", json={"code": "food-openid-two", "nickName": "乙"}
                )
                first_token = first.json()["data"]["token"]
                second_token = second.json()["data"]["token"]
                first_auth = {"Authorization": f"Bearer {first_token}"}
                second_auth = {"Authorization": f"Bearer {second_token}"}

                code_response = await client.post("/api/couple/generateCode", headers=first_auth)
                await client.post(
                    "/api/couple/bind",
                    headers=second_auth,
                    json={"coupleCode": code_response.json()["data"]},
                )

                menu_response = await client.post(
                    "/api/menu/add",
                    headers=first_auth,
                    json={
                        "restaurantName": restaurant_name,
                        "dishName": "星河汤",
                        "price": 88.5,
                        "rating": 5,
                        "status": 0,
                        "eatenDate": "2026-07-26",
                    },
                )
                assert menu_response.status_code == 200
                menu_id = int(menu_response.json()["data"])
                menu_list = await client.get("/api/menu/list", headers=second_auth)
                assert menu_list.json()["data"]["list"][0]["restaurantName"] == restaurant_name
                assert menu_list.json()["data"]["total"] == 1
                await client.post(f"/api/menu/like/{menu_id}", headers=second_auth)
                concurrent_likes = await asyncio.gather(
                    *[
                        client.post(f"/api/menu/like/{menu_id}", headers=second_auth)
                        for _ in range(4)
                    ]
                )
                assert all(response.json()["code"] == 200 for response in concurrent_likes)
                await client.post(f"/api/menu/favorite/{menu_id}", headers=second_auth)
                await client.put(
                    f"/api/menu/update/{menu_id}",
                    headers=first_auth,
                    json={"restaurantName": restaurant_name, "eatenDate": None},
                )
                menu_detail = await client.get(f"/api/menu/detail/{menu_id}", headers=first_auth)
                assert menu_detail.json()["data"]["likeCount"] == 5
                assert menu_detail.json()["data"]["isFavorite"] is True
                assert menu_detail.json()["data"]["eatenDate"] is None

                mapped_menu = await client.post(
                    "/api/menu/add",
                    headers=first_auth,
                    json={
                        "restaurantName": "mapped-private-restaurant",
                        "latitude": 60,
                        "longitude": 10.01,
                    },
                )
                far_menu = await client.post(
                    "/api/menu/add",
                    headers=first_auth,
                    json={
                        "restaurantName": "far-private-restaurant",
                        "latitude": 60,
                        "longitude": 10.1,
                    },
                )
                assert mapped_menu.json()["code"] == far_menu.json()["code"] == 200
                nearby = await client.get(
                    "/api/menu/nearby?latitude=60&longitude=10&radiusMeters=700",
                    headers=second_auth,
                )
                assert [item["id"] for item in nearby.json()["data"]] == [
                    mapped_menu.json()["data"]
                ]
                mapped = await client.get(
                    "/api/menu/map?centerLat=60&centerLng=10&zoomLevel=18",
                    headers=second_auth,
                )
                assert [item["id"] for item in mapped.json()["data"]] == [
                    mapped_menu.json()["data"]
                ]

                recipe_response = await client.post(
                    "/api/recipe/create",
                    headers=first_auth,
                    json={
                        "title": recipe_title,
                        "ingredients": [{"name": "水", "amount": "500ml"}],
                        "steps": [{"content": "加热", "imageUrl": None}],
                        "difficulty": "easy",
                        "cookingTime": 10,
                        "servings": 2,
                        "publish": True,
                    },
                )
                assert recipe_response.status_code == 200
                recipe_id = int(recipe_response.json()["data"])
                couple_page = await client.get("/api/recipe/couple", headers=second_auth)
                assert couple_page.json()["data"]["records"][0]["title"] == recipe_title
                await client.post(f"/api/recipe/like/{recipe_id}", headers=second_auth)
                await client.post(f"/api/recipe/collect/{recipe_id}", headers=second_auth)
                recipe_detail = await client.get(
                    f"/api/recipe/detail/{recipe_id}", headers=second_auth
                )
                assert recipe_detail.json()["data"]["liked"] is True
                assert recipe_detail.json()["data"]["collected"] is True
                assert recipe_detail.json()["data"]["ingredients"] == [
                    {"name": "水", "amount": "500ml"}
                ]
                assert recipe_detail.json()["data"]["steps"] == [
                    {"stepNo": 1, "content": "加热", "imageUrl": None}
                ]

                concurrent_unlikes = await asyncio.gather(
                    client.delete(f"/api/recipe/like/{recipe_id}", headers=second_auth),
                    client.delete(f"/api/recipe/like/{recipe_id}", headers=second_auth),
                )
                assert sorted(response.json()["code"] for response in concurrent_unlikes) == [
                    200,
                    3105,
                ]
                concurrent_likes = await asyncio.gather(
                    client.post(f"/api/recipe/like/{recipe_id}", headers=second_auth),
                    client.post(f"/api/recipe/like/{recipe_id}", headers=second_auth),
                )
                assert sorted(response.json()["code"] for response in concurrent_likes) == [
                    200,
                    3104,
                ]

                newer_recipe = await client.post(
                    "/api/recipe/create",
                    headers=first_auth,
                    json={"title": "newer-private-recipe", "publish": True},
                )
                newer_recipe_id = int(newer_recipe.json()["data"])
                await client.post(f"/api/recipe/collect/{newer_recipe_id}", headers=second_auth)
                await client.delete(f"/api/recipe/collect/{recipe_id}", headers=second_auth)
                await client.post(f"/api/recipe/collect/{recipe_id}", headers=second_auth)
                collected_page = await client.get("/api/recipe/collected", headers=second_auth)
                assert collected_page.json()["data"]["total"] == 2
                assert [item["id"] for item in collected_page.json()["data"]["records"]] == [
                    recipe_id,
                    newer_recipe_id,
                ]

        serialized_logs = str(logs)
        assert restaurant_name not in serialized_logs
        assert recipe_title not in serialized_logs
        assert "requestId" in serialized_logs
        assert "durationMs" in serialized_logs

        async with session_factory() as session:
            assert await session.scalar(select(func.count(CoupleMenu.id))) == 3
            assert await session.scalar(select(func.count(Recipe.id))) == 2
            assert await session.scalar(select(func.count(RecipeLike.id))) == 1
            assert await session.scalar(select(func.count(RecipeCollect.id))) == 2
    finally:
        await redis.close()
