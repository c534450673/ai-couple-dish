import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


EXPECTED_ROUTES = {
    ("POST", "/api/user/login"),
    ("POST", "/api/user/register"),
    ("POST", "/api/user/sendCode"),
    ("POST", "/api/user/phoneLogin"),
    ("GET", "/api/user/info"),
    ("PUT", "/api/user/update"),
    ("POST", "/api/user/logout"),
    ("POST", "/api/couple/generateCode"),
    ("POST", "/api/couple/bind"),
    ("GET", "/api/couple/info"),
    ("GET", "/api/couple/home"),
    ("POST", "/api/couple/unbind/apply"),
    ("POST", "/api/couple/unbind/confirm"),
    ("POST", "/api/couple/unbind/reject"),
    ("GET", "/api/couple/validateCode"),
    ("GET", "/api/couple/loveTimer"),
    ("GET", "/api/couple/recoverable"),
    ("POST", "/api/couple/recover"),
    ("GET", "/api/couple/codeInfo"),
    ("POST", "/api/couple/refreshCode"),
    ("POST", "/api/cart/add"),
    ("PUT", "/api/cart/quantity/{cartId}"),
    ("DELETE", "/api/cart/remove/{cartId}"),
    ("DELETE", "/api/cart/batch-remove"),
    ("DELETE", "/api/cart/clear"),
    ("GET", "/api/cart/list"),
    ("GET", "/api/cart/count"),
    ("POST", "/api/cart/checkout"),
    ("POST", "/api/order/create"),
    ("POST", "/api/order/cancel/{orderId}"),
    ("POST", "/api/order/accept/{orderId}"),
    ("POST", "/api/order/start-cooking/{orderId}"),
    ("POST", "/api/order/finish-cooking/{orderId}"),
    ("POST", "/api/order/complete/{orderId}"),
    ("POST", "/api/order/refund/{orderId}"),
    ("POST", "/api/order/confirm-refund/{orderId}"),
    ("GET", "/api/order/detail/{orderId}"),
    ("GET", "/api/order/my-buy"),
    ("GET", "/api/order/my-sell"),
    ("GET", "/api/order/couple"),
    ("GET", "/api/order/pending-count"),
    ("GET", "/api/coupleRank/info"),
    ("GET", "/api/coupleRank/rankList"),
    ("GET", "/api/coupleRank/rewards"),
    ("POST", "/api/coupleRank/claim/{rank}"),
    ("GET", "/api/coupleTree/info"),
    ("POST", "/api/coupleTree/water"),
    ("GET", "/api/coupleTree/nutrientLogs"),
    ("GET", "/api/coupleTree/skins"),
    ("POST", "/api/coupleTree/skin/change"),
    ("POST", "/api/dailyGreeting/send"),
    ("GET", "/api/dailyGreeting/today/status"),
    ("GET", "/api/dailyGreeting/both/status"),
    ("GET", "/api/dailyGreeting/streak"),
    ("GET", "/api/dailyGreeting/history"),
    ("GET", "/api/dailyGreeting/detail/{id}"),
    ("GET", "/api/dailyTask/today"),
    ("GET", "/api/dailyTask/detail/{id}"),
    ("POST", "/api/dailyTask/progress/{id}"),
    ("POST", "/api/dailyTask/claim/{id}"),
    ("GET", "/api/dailyTask/today/stats"),
    ("GET", "/api/notification/list"),
    ("GET", "/api/notification/unreadCount"),
    ("PUT", "/api/notification/read/{id}"),
    ("PUT", "/api/notification/readAll"),
    ("DELETE", "/api/notification/delete/{id}"),
    ("GET", "/api/menu/list"),
    ("GET", "/api/menu/detail/{id}"),
    ("POST", "/api/menu/add"),
    ("PUT", "/api/menu/update/{id}"),
    ("DELETE", "/api/menu/delete/{id}"),
    ("POST", "/api/menu/recover/{id}"),
    ("POST", "/api/menu/like/{id}"),
    ("DELETE", "/api/menu/unlike/{id}"),
    ("POST", "/api/menu/favorite/{id}"),
    ("DELETE", "/api/menu/unfavorite/{id}"),
    ("GET", "/api/menu/stats"),
    ("GET", "/api/menu/nearby"),
    ("GET", "/api/menu/map"),
    ("POST", "/api/recipe/create"),
    ("PUT", "/api/recipe/update/{recipeId}"),
    ("DELETE", "/api/recipe/delete/{recipeId}"),
    ("POST", "/api/recipe/publish/{recipeId}"),
    ("GET", "/api/recipe/detail/{recipeId}"),
    ("GET", "/api/recipe/my"),
    ("GET", "/api/recipe/couple"),
    ("GET", "/api/recipe/recommended"),
    ("GET", "/api/recipe/search"),
    ("GET", "/api/recipe/collected"),
    ("POST", "/api/recipe/like/{recipeId}"),
    ("DELETE", "/api/recipe/like/{recipeId}"),
    ("POST", "/api/recipe/collect/{recipeId}"),
    ("DELETE", "/api/recipe/collect/{recipeId}"),
    ("GET", "/api/anniversary/list"),
    ("GET", "/api/anniversary/upcoming"),
    ("GET", "/api/anniversary/next"),
    ("POST", "/api/anniversary/add"),
    ("PUT", "/api/anniversary/update/{id}"),
    ("DELETE", "/api/anniversary/delete/{id}"),
    ("GET", "/api/anniversary/today"),
    ("PUT", "/api/anniversary/reminderConfig"),
    ("GET", "/api/note/list"),
    ("GET", "/api/note/detail/{id}"),
    ("POST", "/api/note/add"),
    ("PUT", "/api/note/update/{id}"),
    ("DELETE", "/api/note/delete/{id}"),
    ("POST", "/api/note/like/{id}"),
    ("DELETE", "/api/note/unlike/{id}"),
    ("POST", "/api/note/comment/{id}"),
    ("GET", "/api/feed/today"),
    ("POST", "/api/feed/send"),
    ("GET", "/api/feed/received"),
    ("GET", "/api/feed/sent"),
    ("POST", "/api/feed/accept/{id}"),
    ("POST", "/api/feed/reject/{id}"),
    ("GET", "/api/wish/list"),
    ("GET", "/api/wish/detail/{id}"),
    ("POST", "/api/wish/add"),
    ("PUT", "/api/wish/update/{id}"),
    ("DELETE", "/api/wish/delete/{id}"),
    ("POST", "/api/wish/fulfill/{id}"),
    ("POST", "/api/wish/unfulfill/{id}"),
    ("POST", "/api/heartMoment/create"),
    ("GET", "/api/heartMoment/list"),
    ("DELETE", "/api/heartMoment/delete/{id}"),
    ("GET", "/api/heartMoment/random"),
    ("POST", "/api/timeCapsule/create"),
    ("GET", "/api/timeCapsule/list"),
    ("GET", "/api/timeCapsule/detail/{id}"),
    ("POST", "/api/timeCapsule/unlock/{id}"),
    ("DELETE", "/api/timeCapsule/delete/{id}"),
    ("GET", "/api/timeCapsule/pending"),
    ("GET", "/api/loveCalendar/month"),
    ("GET", "/api/loveCalendar/events/date"),
    ("GET", "/api/loveCalendar/events/range"),
    ("GET", "/api/loveCalendar/events/upcoming"),
    ("GET", "/api/loveCalendar/events/today"),
    ("GET", "/api/loveCalendar/year/overview"),
    ("POST", "/api/mood/send"),
    ("GET", "/api/mood/today"),
    ("GET", "/api/mood/history"),
    ("GET", "/api/mood/detail/{id}"),
    ("POST", "/api/mood/read/{id}"),
    ("GET", "/api/mood/stats"),
    ("GET", "/api/mood/types"),
    ("GET", "/api/mood/unread/count"),
    ("POST", "/api/upload/image"),
    ("POST", "/api/upload/images"),
    ("DELETE", "/api/upload/file"),
}


def test_business_route_inventory_is_registered() -> None:
    app = create_app(settings())
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "DELETE"}
    }
    assert EXPECTED_ROUTES <= actual


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/user/info"),
        ("GET", "/api/couple/info"),
        ("GET", "/api/coupleRank/info"),
        ("GET", "/api/coupleRank/rankList"),
        ("GET", "/api/coupleRank/rewards"),
        ("POST", "/api/coupleRank/claim/bronze"),
        ("GET", "/api/coupleTree/info"),
        ("POST", "/api/coupleTree/water"),
        ("GET", "/api/coupleTree/nutrientLogs"),
        ("GET", "/api/coupleTree/skins"),
        ("POST", "/api/coupleTree/skin/change?skinId=default"),
        ("POST", "/api/cart/add"),
        ("PUT", "/api/cart/quantity/1?quantity=1"),
        ("DELETE", "/api/cart/remove/1"),
        ("DELETE", "/api/cart/batch-remove"),
        ("DELETE", "/api/cart/clear"),
        ("GET", "/api/cart/list"),
        ("GET", "/api/cart/count"),
        ("POST", "/api/cart/checkout"),
        ("POST", "/api/order/create"),
        ("POST", "/api/order/cancel/1"),
        ("POST", "/api/order/accept/1"),
        ("POST", "/api/order/start-cooking/1"),
        ("POST", "/api/order/finish-cooking/1"),
        ("POST", "/api/order/complete/1"),
        ("POST", "/api/order/refund/1?reason=changed-plan"),
        ("POST", "/api/order/confirm-refund/1"),
        ("GET", "/api/order/detail/1"),
        ("GET", "/api/order/my-buy"),
        ("GET", "/api/order/my-sell"),
        ("GET", "/api/order/couple"),
        ("GET", "/api/order/pending-count"),
        ("POST", "/api/dailyGreeting/send"),
        ("GET", "/api/dailyGreeting/today/status?greetingType=1"),
        ("GET", "/api/dailyGreeting/both/status?greetingType=1"),
        ("GET", "/api/dailyGreeting/streak?streakType=1"),
        ("GET", "/api/dailyGreeting/history"),
        ("GET", "/api/dailyGreeting/detail/1"),
        ("GET", "/api/dailyTask/today"),
        ("GET", "/api/dailyTask/detail/1"),
        ("POST", "/api/dailyTask/progress/1?count=1"),
        ("POST", "/api/dailyTask/claim/1"),
        ("GET", "/api/dailyTask/today/stats"),
        ("GET", "/api/notification/list"),
        ("GET", "/api/menu/list"),
        ("GET", "/api/recipe/my"),
        ("GET", "/api/anniversary/list"),
        ("GET", "/api/anniversary/next"),
        ("GET", "/api/note/list"),
        ("GET", "/api/note/detail/1"),
        ("GET", "/api/feed/today"),
        ("GET", "/api/feed/received"),
        ("GET", "/api/wish/list"),
        ("GET", "/api/wish/detail/1"),
        ("GET", "/api/heartMoment/list"),
        ("GET", "/api/heartMoment/random"),
        ("POST", "/api/heartMoment/create"),
        ("DELETE", "/api/heartMoment/delete/1"),
        ("POST", "/api/timeCapsule/create"),
        ("GET", "/api/timeCapsule/list"),
        ("GET", "/api/timeCapsule/detail/1"),
        ("POST", "/api/timeCapsule/unlock/1"),
        ("DELETE", "/api/timeCapsule/delete/1"),
        ("GET", "/api/timeCapsule/pending"),
        ("GET", "/api/loveCalendar/month"),
        ("GET", "/api/loveCalendar/events/date?date=2026-07-26"),
        ("GET", "/api/loveCalendar/events/range?startDate=2026-07-26&endDate=2026-07-27"),
        ("GET", "/api/loveCalendar/events/upcoming"),
        ("GET", "/api/loveCalendar/events/today"),
        ("GET", "/api/loveCalendar/year/overview"),
        ("DELETE", "/api/upload/file"),
    ],
)
async def test_business_routes_require_authentication(method: str, path: str) -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == 401
    assert response.json()["data"] is None


async def test_wechat_login_rejects_blank_code_with_result_envelope() -> None:
    app = create_app(settings())

    async def no_session():
        yield None

    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/user/login", json={"code": ""})

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
    assert response.json()["message"]


async def test_phone_login_validation_does_not_echo_phone_or_code() -> None:
    phone = "13800138000"
    verify_code = "123456"
    app = create_app(settings())

    async def no_session():
        yield None

    app.dependency_overrides[get_session] = no_session
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/user/phoneLogin",
            json={"phone": phone, "verifyCode": verify_code},
        )

    assert response.status_code in {400, 500}
    assert phone not in response.text
    assert verify_code not in response.text
