import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, MockTransport, Request, Response

from packages.platform.auth import issue_user_token
from services.gateway.app.main import create_app

SECRET = "gateway-test-secret-" + "x" * 64


async def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://gateway")


@pytest.mark.asyncio
async def test_gateway_options_is_handled_before_authentication() -> None:
    app = create_app(upstream="http://upstream", jwt_secret=SECRET)
    async with await _client(app) as client:
        response = await client.options(
            "/api/couple/info",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )

    assert response.status_code == 204
    assert response.headers["x-request-id"]
    assert response.headers["access-control-allow-methods"]
    assert "Idempotency-Key" in response.headers["access-control-allow-headers"]


@pytest.mark.asyncio
async def test_gateway_forwards_query_body_headers_and_upstream_content_type() -> None:
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    observed: dict[str, object] = {}

    async def handler(request: Request) -> Response:
        observed["url"] = str(request.url)
        observed["body"] = await request.aread()
        observed["request_id"] = request.headers["x-request-id"]
        observed["authorization"] = request.headers["authorization"]
        return Response(
            201, content=b'{"ok":true}', headers={"content-type": "application/problem+json"}
        )

    app = create_app(
        upstream="http://upstream",
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.post(
            "/api/couple/info?tag=a&tag=b",
            content=b"payload",
            headers={
                "authorization": f"Bearer {token}",
                "content-type": "application/octet-stream",
            },
        )

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"] == observed["request_id"]
    assert observed == {
        "url": "http://upstream/api/couple/info?tag=a&tag=b",
        "body": b"payload",
        "request_id": response.headers["x-request-id"],
        "authorization": f"Bearer {token}",
    }


@pytest.mark.asyncio
async def test_gateway_rejects_missing_or_invalid_authorization() -> None:
    app = create_app(upstream="http://upstream", jwt_secret=SECRET)
    async with await _client(app) as client:
        missing = await client.get("/api/couple/info")
        invalid = await client.get("/api/couple/info", headers={"authorization": "Bearer nope"})

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["code"] == invalid.json()["code"] == 401
    assert "x-request-id" in missing.headers


@pytest.mark.asyncio
async def test_gateway_timeout_returns_504_and_request_id() -> None:
    async def handler(_: Request) -> Response:
        raise httpx.ReadTimeout("upstream timeout")

    token = issue_user_token(user_id=1, secret=SECRET, expires_ms=60_000)
    app = create_app(
        upstream="http://upstream", jwt_secret=SECRET, transport=MockTransport(handler)
    )
    async with await _client(app) as client:
        response = await client.get(
            "/api/couple/info", headers={"authorization": f"Bearer {token}"}
        )

    assert response.status_code == 504
    assert response.json()["code"] == 504
    assert response.headers["x-request-id"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "service"),
    (
        ("/api/user/profile", "identity"),
        ("/api/couple/bind", "identity"),
        ("/api/catalog/dishes", "catalog"),
        ("/api/media/upload", "media"),
        ("/api/dining/cart", "dining"),
        ("/api/admin/login", "admin"),
        ("/api/analytics/reports/daily", "analytics"),
    ),
)
async def test_gateway_routes_service_prefixes_to_their_configured_upstream(
    path: str, service: str
) -> None:
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    observed: list[str] = []

    async def handler(request: Request) -> Response:
        observed.append(str(request.url))
        return Response(200, json={"code": 200, "message": "操作成功", "data": None})

    upstreams = {
        "identity": "http://identity:8101",
        "catalog": "http://catalog:8102",
        "media": "http://media:8103",
        "dining": "http://dining:8104",
        "admin": "http://admin:8105",
        "analytics": "http://analytics:8106",
    }
    app = create_app(
        upstream="http://legacy:8080",
        upstreams=upstreams,
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    headers = {} if service == "admin" else {"Authorization": f"Bearer {token}"}
    async with await _client(app) as client:
        response = await client.get(path, headers=headers)

    assert response.status_code == 200
    assert observed == [f"{upstreams[service]}{path}"]


@pytest.mark.asyncio
async def test_gateway_keeps_unmigrated_routes_on_the_legacy_upstream() -> None:
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    observed: list[str] = []

    async def handler(request: Request) -> Response:
        observed.append(str(request.url))
        return Response(200, json={"code": 200, "message": "操作成功", "data": None})

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"dining": "http://dining:8104", "identity": "http://identity:8101"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.get(
            "/api/coupleTree/info", headers={"Authorization": f"Bearer {token}"}
        )
        old_user = await client.get("/api/user/info", headers={"Authorization": f"Bearer {token}"})
        old_couple = await client.get(
            "/api/couple/info", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == old_user.status_code == old_couple.status_code == 200
    assert observed == [
        "http://legacy:8080/api/coupleTree/info",
        "http://legacy:8080/api/user/info",
        "http://legacy:8080/api/couple/info",
    ]


@pytest.mark.asyncio
async def test_gateway_reads_service_upstream_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GATEWAY_DINING_SERVICE_URL", "http://dining-env:8104/")
    token = issue_user_token(user_id=7, secret=SECRET, expires_ms=60_000)
    observed: list[str] = []

    async def handler(request: Request) -> Response:
        observed.append(str(request.url))
        return Response(200)

    app = create_app(
        upstream="http://legacy:8080",
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.get(
            "/api/dining/cart", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert observed == ["http://dining-env:8104/api/dining/cart"]


@pytest.mark.asyncio
async def test_gateway_delegates_admin_authentication_and_preserves_its_error() -> None:
    async def handler(request: Request) -> Response:
        assert request.headers["authorization"] == "Bearer invalid-admin-token"
        return Response(
            401,
            json={"code": 401, "message": "管理员登录信息无效", "data": None},
        )

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"admin": "http://admin:8105"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.get(
            "/api/admin/orders", headers={"Authorization": "Bearer invalid-admin-token"}
        )

    assert response.status_code == 401
    assert response.json() == {"code": 401, "message": "管理员登录信息无效", "data": None}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ("/api/user/login", "/api/user/register", "/api/user/sendCode", "/api/user/phoneLogin"),
)
async def test_gateway_allows_unauthenticated_login_paths(path: str) -> None:
    observed: list[str] = []

    async def handler(request: Request) -> Response:
        observed.append(str(request.url))
        return Response(200)

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"identity": "http://identity:8101"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.post(path)

    assert response.status_code == 200
    assert observed == [f"http://identity:8101{path}"]


@pytest.mark.asyncio
async def test_gateway_serves_media_files_without_user_token() -> None:
    async def handler(request: Request) -> Response:
        assert str(request.url) == "http://media:8103/api/media/files/images/example.jpg"
        return Response(200, content=b"image", headers={"content-type": "image/jpeg"})

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"media": "http://media:8103"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.get("/api/media/files/images/example.jpg")
        protected = await client.get("/api/media/private")

    assert response.status_code == 200
    assert response.content == b"image"
    assert protected.status_code == 401


@pytest.mark.asyncio
async def test_gateway_delegates_media_upload_admin_authentication() -> None:
    async def handler(request: Request) -> Response:
        assert request.headers["authorization"] == "Bearer admin-token"
        return Response(403, json={"code": 403, "message": "无管理员权限", "data": None})

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"media": "http://media:8103"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.post(
            "/api/media/upload", headers={"Authorization": "Bearer admin-token"}
        )

    assert response.status_code == 403
    assert response.json()["message"] == "无管理员权限"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    (
        "/api/catalog/import",
        "/api/catalog/dishes/7/sources/9/review",
        "/api/catalog/dishes/7/publish",
    ),
)
async def test_gateway_delegates_catalog_admin_authentication(path: str) -> None:
    async def handler(request: Request) -> Response:
        assert request.headers["authorization"] == "Bearer invalid-admin-token"
        return Response(403, json={"code": 403, "message": "无管理员权限", "data": None})

    app = create_app(
        upstream="http://legacy:8080",
        upstreams={"catalog": "http://catalog:8102"},
        jwt_secret=SECRET,
        transport=MockTransport(handler),
    )
    async with await _client(app) as client:
        response = await client.post(
            path, headers={"Authorization": "Bearer invalid-admin-token"}
        )

    assert response.status_code == 403
    assert response.json()["message"] == "无管理员权限"
