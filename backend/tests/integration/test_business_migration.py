import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
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
from app.db.models import (
    Anniversary,
    CoupleMenu,
    CoupleRank,
    CoupleTree,
    Feed,
    FoodNote,
    HeartMoment,
    MoodRecord,
    NoteLike,
    Notification,
    Recipe,
    RecipeCollect,
    RecipeLike,
    TreeNutrientLog,
    User,
    Wish,
)
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
from app.services import feed as feed_service
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
async def test_couple_rank_routes_keep_couple_scope_lazy_init_and_idempotent_claim(
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
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                users = []
                for code, nickname in (
                    ("rank-openid-one", "甲"),
                    ("rank-openid-two", "乙"),
                    ("rank-openid-three", "丙"),
                    ("rank-openid-four", "丁"),
                ):
                    response = await client.post(
                        "/api/user/login", json={"code": code, "nickName": nickname}
                    )
                    users.append({"Authorization": f"Bearer {response.json()['data']['token']}"})

                first_code = await client.post("/api/couple/generateCode", headers=users[0])
                assert (
                    await client.post(
                        "/api/couple/bind",
                        headers=users[1],
                        json={"coupleCode": first_code.json()["data"]},
                    )
                ).json()["code"] == 200
                second_code = await client.post("/api/couple/generateCode", headers=users[2])
                assert (
                    await client.post(
                        "/api/couple/bind",
                        headers=users[3],
                        json={"coupleCode": second_code.json()["data"]},
                    )
                ).json()["code"] == 200

                unbound = await client.get("/api/coupleRank/info", headers={})
                assert unbound.status_code == 401
                concurrent_info = await asyncio.gather(
                    *[client.get("/api/coupleRank/info", headers=users[0]) for _ in range(4)]
                )
                assert all(response.json()["code"] == 200 for response in concurrent_info)
                info = concurrent_info[0].json()["data"]
                assert info["currentRank"] == "bronze"
                assert info["rankScore"] == 0
                assert len(info["rankList"]) == 6

                first_rank_list = await client.get("/api/coupleRank/rankList", headers=users[1])
                assert first_rank_list.json()["code"] == 200
                assert len(first_rank_list.json()["data"]) == 1
                assert (await client.get("/api/coupleRank/rankList", headers=users[2])).json()[
                    "data"
                ] == first_rank_list.json()["data"]

                rewards = await client.get("/api/coupleRank/rewards", headers=users[1])
                assert rewards.json()["code"] == 200
                assert len(rewards.json()["data"]) == 6
                assert rewards.json()["data"][0]["claimed"] is True
                first_claim = await client.post("/api/coupleRank/claim/bronze", headers=users[0])
                second_claim = await client.post("/api/coupleRank/claim/bronze", headers=users[1])
                assert first_claim.json()["code"] == second_claim.json()["code"] == 200
                not_reached = await client.post("/api/coupleRank/claim/gold", headers=users[0])
                assert not_reached.json()["code"] == 8803

        assert "rank-openid" not in str(logs)
        assert "甲" not in str(logs)
        assert "requestId" in str(logs)
        assert "durationMs" in str(logs)
        async with session_factory() as session:
            assert await session.scalar(select(func.count(CoupleRank.id))) == 1
    finally:
        await redis.close()


@pytest.mark.integration
async def test_couple_tree_routes_keep_scope_atomic_growth_and_redacted_logs(
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
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                users = []
                for code, nickname in (("tree-openid-one", "树甲"), ("tree-openid-two", "树乙")):
                    response = await client.post(
                        "/api/user/login", json={"code": code, "nickName": nickname}
                    )
                    users.append({"Authorization": f"Bearer {response.json()['data']['token']}"})

                code_response = await client.post("/api/couple/generateCode", headers=users[0])
                assert (
                    await client.post(
                        "/api/couple/bind",
                        headers=users[1],
                        json={"coupleCode": code_response.json()["data"]},
                    )
                ).json()["code"] == 200

                concurrent_info = await asyncio.gather(
                    *[client.get("/api/coupleTree/info", headers=users[0]) for _ in range(4)]
                )
                assert all(response.json()["code"] == 200 for response in concurrent_info)
                info = concurrent_info[0].json()["data"]
                assert info["level"] == 1
                assert info["totalNutrient"] == 0
                assert info["availableSkins"][0]["unlocked"] is True

                assert (
                    await client.post(
                        "/api/coupleTree/water",
                        headers=users[0],
                        json={
                            "nutrientAmount": 100,
                            "sourceAction": "manual_water",
                            "remark": "只在测试日志中保存",
                        },
                    )
                ).json()["code"] == 200
                assert (
                    await client.post(
                        "/api/coupleTree/water",
                        headers=users[1],
                        json={"nutrientAmount": 10},
                    )
                ).json()["code"] == 200

                grown = (await client.get("/api/coupleTree/info", headers=users[1])).json()["data"]
                assert grown["level"] == 2
                assert grown["totalNutrient"] == 110
                assert grown["currentLevelNutrient"] == 10
                assert grown["availableSkins"][1]["unlocked"] is False

                logs_response = await client.get(
                    "/api/coupleTree/nutrientLogs?limit=1", headers=users[0]
                )
                logs_data = logs_response.json()["data"]
                assert len(logs_data) == 1
                assert logs_data[0]["nutrientAmount"] == 10
                assert logs_data[0]["sourceActionName"] == "手动浇水"
                assert logs_data[0]["userName"] == "树乙"

                locked = await client.post(
                    "/api/coupleTree/skin/change?skinId=spring", headers=users[0]
                )
                assert locked.json()["code"] == 9001
                changed = await client.post(
                    "/api/coupleTree/skin/change?skinId=default", headers=users[1]
                )
                assert changed.json()["code"] == 200

        assert "tree-openid" not in str(logs)
        assert "树甲" not in str(logs)
        assert "只在测试日志中保存" not in str(logs)
        assert "requestId" in str(logs)
        assert "durationMs" in str(logs)
        async with session_factory() as session:
            assert await session.scalar(select(func.count(CoupleTree.id))) == 1
            assert await session.scalar(select(func.count(TreeNutrientLog.id))) == 2
    finally:
        await redis.close()


@pytest.mark.integration
async def test_heart_moment_routes_keep_couple_scope_and_logs_redacted(
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
    private_content = "integration-private-heart-moment"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                users = []
                user_ids = []
                for code in ("moment-one", "moment-two", "moment-three", "moment-four"):
                    response = await client.post("/api/user/login", json={"code": code})
                    users.append({"Authorization": f"Bearer {response.json()['data']['token']}"})
                    user_ids.append(int(response.json()["data"]["userInfo"]["id"]))
                assert (
                    await client.post(
                        "/api/heartMoment/create", headers=users[0], json={"momentType": "text"}
                    )
                ).json()["code"] == 2006
                first_code = await client.post("/api/couple/generateCode", headers=users[0])
                await client.post(
                    "/api/couple/bind",
                    headers=users[1],
                    json={"coupleCode": first_code.json()["data"]},
                )
                second_code = await client.post("/api/couple/generateCode", headers=users[2])
                await client.post(
                    "/api/couple/bind",
                    headers=users[3],
                    json={"coupleCode": second_code.json()["data"]},
                )
                created = await client.post(
                    "/api/heartMoment/create",
                    headers=users[0],
                    json={"momentType": "text", "content": private_content},
                )
                moment_id = int(created.json()["data"])
                listed = await client.get(
                    "/api/heartMoment/list?page=0&pageSize=0", headers=users[1]
                )
                listed_item = listed.json()["data"][0]
                assert listed_item["id"] == moment_id
                assert set(listed_item) == {
                    "id",
                    "momentType",
                    "content",
                    "mediaUrl",
                    "createTime",
                    "timeDesc",
                    "creator",
                }
                assert listed_item["creator"]["id"] == user_ids[0]
                assert (await client.get("/api/heartMoment/random", headers=users[1])).json()[
                    "data"
                ]["id"] == moment_id
                assert (
                    await client.delete(f"/api/heartMoment/delete/{moment_id}", headers=users[1])
                ).json()["code"] == 3002
                assert (
                    await client.delete(f"/api/heartMoment/delete/{moment_id}", headers=users[2])
                ).json()["code"] == 3002
                assert (
                    await client.delete(f"/api/heartMoment/delete/{moment_id}", headers=users[0])
                ).json()["code"] == 200
                assert (await client.get("/api/heartMoment/random", headers=users[1])).json()[
                    "data"
                ] is None
        assert private_content not in str(logs)
        async with session_factory() as session:
            item = await session.get(HeartMoment, moment_id)
            assert item is not None and item.is_deleted == 1
    finally:
        await redis.close()


@pytest.mark.integration
async def test_mood_routes_keep_couple_scope_create_notifications_and_redact_logs(
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
    private_description = "integration-private-mood-description"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                users = []
                user_ids = []
                for code in ("mood-one", "mood-two", "mood-three", "mood-four"):
                    response = await client.post("/api/user/login", json={"code": code})
                    users.append({"Authorization": f"Bearer {response.json()['data']['token']}"})
                    user_ids.append(int(response.json()["data"]["userInfo"]["id"]))

                assert (
                    await client.post(
                        "/api/mood/send", headers=users[0], json={"moodType": "happy"}
                    )
                ).json()["code"] == 2006
                types = await client.get("/api/mood/types", headers=users[0])
                assert types.json()["code"] == 200
                assert {item["type"] for item in types.json()["data"]} == {
                    "happy",
                    "love",
                    "miss_you",
                    "tired",
                    "upset",
                    "sad",
                    "angry",
                    "anxious",
                }

                first_code = await client.post("/api/couple/generateCode", headers=users[0])
                await client.post(
                    "/api/couple/bind",
                    headers=users[1],
                    json={"coupleCode": first_code.json()["data"]},
                )
                second_code = await client.post("/api/couple/generateCode", headers=users[2])
                await client.post(
                    "/api/couple/bind",
                    headers=users[3],
                    json={"coupleCode": second_code.json()["data"]},
                )

                created = await client.post(
                    "/api/mood/send",
                    headers=users[0],
                    json={"moodType": "happy", "description": private_description},
                )
                mood_id = int(created.json()["data"])
                assert (
                    await client.post(
                        "/api/mood/send", headers=users[0], json={"moodType": "unknown"}
                    )
                ).json()["code"] == 400
                today = await client.get("/api/mood/today", headers=users[1])
                mood = today.json()["data"][0]
                assert set(mood) == {
                    "id",
                    "moodType",
                    "moodTypeName",
                    "description",
                    "moodIcon",
                    "moodColor",
                    "recordDate",
                    "isRead",
                    "readTime",
                    "createTime",
                    "sender",
                }
                assert mood["id"] == mood_id
                assert mood["isRead"] is False
                assert mood["sender"]["id"] == user_ids[0]
                assert (await client.get("/api/mood/history?limit=0", headers=users[1])).json()[
                    "data"
                ][0]["id"] == mood_id
                stats = await client.get("/api/mood/stats", headers=users[1])
                assert stats.json()["data"]["todayCount"] == 1
                assert stats.json()["data"]["weekCount"] == 1
                assert stats.json()["data"]["monthCount"] == 1
                assert stats.json()["data"]["distribution"] == [
                    {
                        "moodType": "happy",
                        "moodTypeName": "开心",
                        "count": 1,
                        "percentage": 100.0,
                    }
                ]
                assert (await client.get("/api/mood/unread/count", headers=users[1])).json()[
                    "data"
                ] == 1
                assert (await client.get("/api/mood/unread/count", headers=users[0])).json()[
                    "data"
                ] == 0
                assert (await client.get(f"/api/mood/detail/{mood_id}", headers=users[2])).json()[
                    "code"
                ] == 3002
                assert (await client.post(f"/api/mood/read/{mood_id}", headers=users[2])).json()[
                    "code"
                ] == 3002
                assert (await client.post(f"/api/mood/read/{mood_id}", headers=users[1])).json()[
                    "code"
                ] == 200
                assert (await client.get("/api/mood/unread/count", headers=users[1])).json()[
                    "data"
                ] == 0
        assert private_description not in str(logs)
        async with session_factory() as session:
            record = await session.get(MoodRecord, mood_id)
            notification = await session.scalar(
                select(Notification).where(
                    Notification.related_id == mood_id,
                    Notification.related_type == "mood_record",
                )
            )
            assert record is not None and record.is_read == 1 and record.read_time is not None
            assert (
                notification is not None
                and notification.user_id == user_ids[1]
                and notification.type == 2
            )
    finally:
        await redis.close()


@pytest.mark.integration
async def test_feed_and_wish_routes_keep_limits_permissions_and_logs_redacted(
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
    feed_content = "integration-private-feed-content"
    feed_message = "integration-private-feed-message"
    feed_image = "https://private.invalid/feed.jpg"
    reject_reason = "integration-private-reject-reason"
    wish_title = "integration-private-wish-title"
    wish_description = "integration-private-wish-description"
    wish_image = "https://private.invalid/wish.jpg"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                first = await client.post(
                    "/api/user/login", json={"code": "feed-openid-one", "nickName": "甲"}
                )
                second = await client.post(
                    "/api/user/login", json={"code": "feed-openid-two", "nickName": "乙"}
                )
                third = await client.post(
                    "/api/user/login", json={"code": "feed-openid-three", "nickName": "丙"}
                )
                fourth = await client.post(
                    "/api/user/login", json={"code": "feed-openid-four", "nickName": "丁"}
                )
                first_auth = {"Authorization": f"Bearer {first.json()['data']['token']}"}
                second_auth = {"Authorization": f"Bearer {second.json()['data']['token']}"}
                third_auth = {"Authorization": f"Bearer {third.json()['data']['token']}"}
                fourth_auth = {"Authorization": f"Bearer {fourth.json()['data']['token']}"}

                unbound_send = await client.post(
                    "/api/feed/send", headers=first_auth, json={"feedType": "meal"}
                )
                assert unbound_send.json()["code"] == 2006
                unbound_today = await client.get("/api/feed/today", headers=first_auth)
                assert unbound_today.json()["data"]["remainingCount"] == 3
                assert (await client.get("/api/wish/list", headers=first_auth)).json()["data"] == []

                first_code = await client.post("/api/couple/generateCode", headers=first_auth)
                first_bind = await client.post(
                    "/api/couple/bind",
                    headers=second_auth,
                    json={"coupleCode": first_code.json()["data"]},
                )
                assert first_bind.json()["code"] == 200
                third_code = await client.post("/api/couple/generateCode", headers=third_auth)
                third_bind = await client.post(
                    "/api/couple/bind",
                    headers=fourth_auth,
                    json={"coupleCode": third_code.json()["data"]},
                )
                assert third_bind.json()["code"] == 200

                concurrent_sends = await asyncio.gather(
                    *[
                        client.post(
                            "/api/feed/send",
                            headers=third_auth,
                            json={"feedType": "meal"},
                        )
                        for _ in range(4)
                    ]
                )
                concurrent_codes = [response.json()["code"] for response in concurrent_sends]
                assert concurrent_codes.count(200) == 1
                assert all(code in {200, 9005, 9006} for code in concurrent_codes)
                third_retry = await client.post(
                    "/api/feed/send", headers=third_auth, json={"feedType": "meal"}
                )
                assert third_retry.json()["code"] == 9006

                meal = await client.post(
                    "/api/feed/send",
                    headers=first_auth,
                    json={
                        "feedType": "meal",
                        "content": feed_content,
                        "imageUrls": [feed_image],
                        "message": feed_message,
                    },
                )
                assert meal.json()["code"] == 200
                meal_id = int(meal.json()["data"])
                duplicate_type = await client.post(
                    "/api/feed/send", headers=first_auth, json={"feedType": "meal"}
                )
                assert duplicate_type.json()["code"] == 9006

                sender_today = await client.get("/api/feed/today", headers=first_auth)
                assert sender_today.json()["data"]["sentToday"] is True
                assert sender_today.json()["data"]["sentCount"] == 1
                assert sender_today.json()["data"]["remainingCount"] == 2
                assert sender_today.json()["data"]["sentTypes"] == ["meal"]
                assert "meal" not in sender_today.json()["data"]["availableTypes"]
                receiver_today = await client.get("/api/feed/today", headers=second_auth)
                assert receiver_today.json()["data"]["receivedToday"] is True
                assert receiver_today.json()["data"]["pendingFeed"]["id"] == meal_id
                received = await client.get("/api/feed/received", headers=second_auth)
                assert received.json()["data"][0]["senderName"] == "甲"
                assert received.json()["data"][0]["receiverName"] == "乙"
                assert received.json()["data"][0]["feedTypeName"] == "正餐"
                assert received.json()["data"][0]["imageUrls"] == [feed_image]

                forbidden_accept = await client.post(
                    f"/api/feed/accept/{meal_id}", headers=first_auth
                )
                assert forbidden_accept.json()["code"] == 6004
                accepted = await client.post(f"/api/feed/accept/{meal_id}", headers=second_auth)
                assert accepted.json()["code"] == 200
                repeated_accept = await client.post(
                    f"/api/feed/accept/{meal_id}", headers=second_auth
                )
                assert repeated_accept.json()["code"] == 6003

                dessert = await client.post(
                    "/api/feed/send", headers=first_auth, json={"feedType": "dessert"}
                )
                dessert_id = int(dessert.json()["data"])
                rejected = await client.post(
                    f"/api/feed/reject/{dessert_id}",
                    headers=second_auth,
                    params={"reason": reject_reason},
                )
                assert rejected.json()["code"] == 200
                snack = await client.post(
                    "/api/feed/send", headers=first_auth, json={"feedType": "snack"}
                )
                snack_id = int(snack.json()["data"])
                total_limit = await client.post(
                    "/api/feed/send", headers=first_auth, json={"feedType": "drink"}
                )
                assert total_limit.json()["code"] == 9007

                async with session_factory() as session:
                    snack_item = await session.get(Feed, snack_id)
                    assert snack_item is not None
                    snack_item.expire_time = datetime.now() - timedelta(seconds=1)
                    await session.commit()
                async with session_factory() as session:
                    assert await feed_service.expire_due(session, "integration-scheduler") == 1
                expired_accept = await client.post(
                    f"/api/feed/accept/{snack_id}", headers=second_auth
                )
                assert expired_accept.json()["code"] == 6003

                outside_wish = await client.post(
                    "/api/wish/add",
                    headers=third_auth,
                    json={"wishType": "dish", "title": "outside"},
                )
                outside_wish_id = int(outside_wish.json()["data"])
                cross_detail = await client.get(
                    f"/api/wish/detail/{outside_wish_id}", headers=first_auth
                )
                assert cross_detail.json()["code"] == 8502

                wish = await client.post(
                    "/api/wish/add",
                    headers=first_auth,
                    json={
                        "wishType": "restaurant",
                        "title": wish_title,
                        "description": wish_description,
                        "imageUrl": wish_image,
                        "priority": 3,
                    },
                )
                assert wish.json()["code"] == 200
                wish_id = int(wish.json()["data"])
                wish_list = await client.get("/api/wish/list", headers=second_auth)
                wish_data = wish_list.json()["data"][0]
                assert wish_data["id"] == wish_id
                assert wish_data["creatorName"] == "甲"
                assert wish_data["wishTypeName"] == "餐厅"
                assert wish_data["priorityName"] == "高"
                assert wish_data["statusName"] == "待实现"
                assert wish_data["viewed"] is False
                updated = await client.put(
                    f"/api/wish/update/{wish_id}",
                    headers=second_auth,
                    json={"title": "updated", "priority": 1},
                )
                assert updated.json()["code"] == 200
                fulfilled = await client.post(f"/api/wish/fulfill/{wish_id}", headers=second_auth)
                assert fulfilled.json()["code"] == 200
                wish_detail = await client.get(f"/api/wish/detail/{wish_id}", headers=first_auth)
                assert wish_detail.json()["data"]["status"] == 2
                assert wish_detail.json()["data"]["achievedDate"] == date.today().isoformat()
                unfulfilled = await client.post(
                    f"/api/wish/unfulfill/{wish_id}", headers=first_auth
                )
                assert unfulfilled.json()["code"] == 200
                repeated_unfulfill = await client.post(
                    f"/api/wish/unfulfill/{wish_id}", headers=first_auth
                )
                assert repeated_unfulfill.json()["code"] == 9001
                deleted = await client.delete(f"/api/wish/delete/{wish_id}", headers=second_auth)
                assert deleted.json()["code"] == 200
                assert (await client.get("/api/wish/list", headers=first_auth)).json()["data"] == []
                deleted_detail = await client.get(f"/api/wish/detail/{wish_id}", headers=first_auth)
                assert deleted_detail.json()["code"] == 8501

        serialized_logs = str(logs)
        for secret in (
            feed_content,
            feed_message,
            feed_image,
            reject_reason,
            wish_title,
            wish_description,
            wish_image,
        ):
            assert secret not in serialized_logs
        assert "requestId" in serialized_logs
        assert "durationMs" in serialized_logs
        assert "errorCode" in serialized_logs

        async with session_factory() as session:
            assert await session.scalar(select(func.count(Feed.id))) == 4
            assert await session.scalar(select(func.count(Wish.id))) == 2
            assert (
                await session.scalar(
                    select(func.count(Notification.id)).where(Notification.related_type == "feed")
                )
                == 7
            )
    finally:
        await redis.close()


@pytest.mark.integration
async def test_upload_routes_validate_content_and_file_ownership(
    mysql_business_engine: AsyncEngine, redis_url: str, tmp_path: Path
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_business_engine, expire_on_commit=False)
    upload_settings = Settings(
        _env_file=None,
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET=SECRET,
        FILE_UPLOAD_PATH=str(tmp_path),
        FILE_BASE_URL="/api/uploads",
    )
    app = create_app(upload_settings)
    app.state.redis = redis

    async def session_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    private_filename = "private-upload-name.png"
    png_content = b"\x89PNG\r\n\x1a\npayload"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                login = await client.post(
                    "/api/user/login", json={"code": "upload-openid-one", "nickName": "上传者"}
                )
                second = await client.post(
                    "/api/user/login", json={"code": "upload-openid-two", "nickName": "其他用户"}
                )
                auth = {"Authorization": f"Bearer {login.json()['data']['token']}"}
                second_auth = {"Authorization": f"Bearer {second.json()['data']['token']}"}
                single = await client.post(
                    "/api/upload/image",
                    headers=auth,
                    files={"file": (private_filename, png_content, "image/png")},
                )
                assert single.json()["code"] == 200
                single_data = single.json()["data"]
                assert "fileKey" not in single_data
                assert single_data["originalFilename"] == private_filename
                assert single_data["type"] == "png"
                assert single_data["size"] == len(png_content)
                file_key = single_data["url"].removeprefix("/api/uploads/")
                downloaded = await client.get(single_data["url"])
                assert downloaded.status_code == 200
                assert downloaded.content == png_content

                invalid_extension = await client.post(
                    "/api/upload/image",
                    headers=auth,
                    files={"file": ("unsafe.txt", b"hello", "text/plain")},
                )
                assert invalid_extension.json()["code"] == 9001
                invalid_magic = await client.post(
                    "/api/upload/image",
                    headers=auth,
                    files={"file": ("fake.png", b"not-an-image", "image/png")},
                )
                assert invalid_magic.json()["code"] == 9001
                multiple = await client.post(
                    "/api/upload/images",
                    headers=auth,
                    files=[
                        ("files", ("one.png", png_content, "image/png")),
                        ("files", ("bad.txt", b"bad", "text/plain")),
                    ],
                )
                assert multiple.json()["code"] == 200
                assert multiple.json()["data"]["count"] == 1
                assert multiple.json()["data"]["files"][0]["fileKey"]

                traversal = await client.delete(
                    "/api/upload/file",
                    headers=auth,
                    params={"fileKey": "../outside.txt"},
                )
                assert traversal.json()["code"] == 3002
                cross_user = await client.delete(
                    "/api/upload/file",
                    headers=second_auth,
                    params={"fileKey": file_key},
                )
                assert cross_user.json()["code"] == 3002
                deleted = await client.delete(
                    "/api/upload/file", headers=auth, params={"fileKey": file_key}
                )
                assert deleted.json()["code"] == 200
                assert (await client.get(single_data["url"])).status_code == 404
                missing = await client.delete(
                    "/api/upload/file", headers=auth, params={"fileKey": file_key}
                )
                assert missing.json()["code"] == 500

        assert private_filename not in str(logs)
        assert "requestId" in str(logs)
        assert "durationMs" in str(logs)
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


@pytest.mark.integration
async def test_note_and_anniversary_routes_keep_contracts_and_logs_redacted(
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
    anniversary_name = "integration-private-anniversary"
    note_title = "integration-private-note"
    note_content = "integration-private-content"
    note_location = "integration-private-location"
    photo_url = "https://private.invalid/note.jpg"
    try:
        with capture_logs() as logs:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                first = await client.post(
                    "/api/user/login", json={"code": "memory-openid-one", "nickName": "甲"}
                )
                second = await client.post(
                    "/api/user/login", json={"code": "memory-openid-two", "nickName": "乙"}
                )
                first_auth = {"Authorization": f"Bearer {first.json()['data']['token']}"}
                second_auth = {"Authorization": f"Bearer {second.json()['data']['token']}"}
                code = await client.post("/api/couple/generateCode", headers=first_auth)
                await client.post(
                    "/api/couple/bind",
                    headers=second_auth,
                    json={"coupleCode": code.json()["data"]},
                )

                anniversary = await client.post(
                    "/api/anniversary/add",
                    headers=first_auth,
                    json={
                        "name": anniversary_name,
                        "anniversaryDate": date.today().isoformat(),
                        "anniversaryType": 2,
                        "isLunarDate": 1,
                        "lunarMonth": 8,
                        "lunarDay": 15,
                    },
                )
                assert anniversary.json()["code"] == 200
                anniversary_id = int(anniversary.json()["data"])
                duplicate = await client.post(
                    "/api/anniversary/add",
                    headers=second_auth,
                    json={
                        "name": "duplicate",
                        "anniversaryDate": date.today().isoformat(),
                        "anniversaryType": 2,
                    },
                )
                assert duplicate.json()["code"] == 5002

                anniversary_list = await client.get("/api/anniversary/list", headers=second_auth)
                assert anniversary_list.json()["code"] == 200
                anniversary_data = anniversary_list.json()["data"][0]
                assert anniversary_data["id"] == anniversary_id
                assert anniversary_data["daysUntil"] == 0
                assert anniversary_data["isLunarDate"] is True
                assert (await client.get("/api/anniversary/upcoming", headers=first_auth)).json()[
                    "data"
                ][0]["id"] == anniversary_id
                assert (await client.get("/api/anniversary/next", headers=first_auth)).json()[
                    "data"
                ]["id"] == anniversary_id
                assert (await client.get("/api/anniversary/today", headers=first_auth)).json()[
                    "data"
                ]["id"] == anniversary_id
                reminder = await client.put(
                    "/api/anniversary/reminderConfig",
                    headers=second_auth,
                    json={
                        "anniversaryId": anniversary_id,
                        "remindChannels": "app,wechat",
                        "remindHour": 9,
                        "appRemindEnabled": 1,
                    },
                )
                assert reminder.json()["code"] == 200
                forbidden_anniversary_update = await client.put(
                    f"/api/anniversary/update/{anniversary_id}",
                    headers=second_auth,
                    json={"name": "forbidden"},
                )
                assert forbidden_anniversary_update.json()["code"] == 3002
                forbidden_anniversary_delete = await client.delete(
                    f"/api/anniversary/delete/{anniversary_id}", headers=first_auth
                )
                assert forbidden_anniversary_delete.json()["code"] == 5003

                note = await client.post(
                    "/api/note/add",
                    headers=first_auth,
                    json={
                        "title": f"<b>{note_title}</b>",
                        "content": f"<script>{note_content}</script>",
                        "location": note_location,
                        "isAnniversaryLinked": 1,
                        "anniversaryId": anniversary_id,
                        "photoUrls": [photo_url],
                    },
                )
                assert note.json()["code"] == 200
                note_id = int(note.json()["data"])
                filtered = await client.get(
                    f"/api/note/list?anniversaryId={anniversary_id}", headers=second_auth
                )
                assert filtered.json()["code"] == 200
                note_data = filtered.json()["data"][0]
                assert note_data["title"] == f"&lt;b&gt;{note_title}&lt;/b&gt;"
                assert note_data["content"] == f"&lt;script&gt;{note_content}&lt;/script&gt;"
                assert note_data["photoUrls"] == [photo_url]
                assert note_data["isAuthor"] is False
                assert note_data["isLiked"] is False
                detail = await client.get(f"/api/note/detail/{note_id}", headers=second_auth)
                assert detail.json()["data"]["anniversaryName"] == anniversary_name

                assert (await client.post(f"/api/note/like/{note_id}", headers=second_auth)).json()[
                    "code"
                ] == 200
                assert (await client.post(f"/api/note/like/{note_id}", headers=second_auth)).json()[
                    "code"
                ] == 200
                assert (
                    await client.post(
                        f"/api/note/comment/{note_id}",
                        headers=second_auth,
                        params={"content": "private-comment"},
                    )
                ).json()["code"] == 200
                assert (
                    await client.delete(f"/api/note/unlike/{note_id}", headers=second_auth)
                ).json()["code"] == 200
                assert (
                    await client.delete(f"/api/note/unlike/{note_id}", headers=second_auth)
                ).json()["code"] == 200
                forbidden_note_update = await client.put(
                    f"/api/note/update/{note_id}",
                    headers=second_auth,
                    json={"title": "forbidden", "content": "forbidden"},
                )
                assert forbidden_note_update.json()["code"] == 4002
                assert (
                    await client.put(
                        f"/api/note/update/{note_id}",
                        headers=first_auth,
                        json={"title": "updated", "content": "updated"},
                    )
                ).json()["code"] == 200
                assert (
                    await client.delete(f"/api/note/delete/{note_id}", headers=second_auth)
                ).json()["code"] == 4002
                assert (
                    await client.delete(f"/api/note/delete/{note_id}", headers=first_auth)
                ).json()["code"] == 200

        serialized_logs = str(logs)
        for secret in (anniversary_name, note_title, note_content, note_location, photo_url):
            assert secret not in serialized_logs
        assert "requestId" in serialized_logs
        assert "durationMs" in serialized_logs

        async with session_factory() as session:
            assert await session.scalar(select(func.count(NoteLike.id))) == 0
            assert await session.scalar(select(func.count(FoodNote.id))) == 1
            assert await session.scalar(select(func.count(Anniversary.id))) == 1
    finally:
        await redis.close()
