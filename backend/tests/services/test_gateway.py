import httpx
import pytest
from httpx import ASGITransport, MockTransport, Request, Response

from packages.platform.auth import issue_user_token
from services.gateway.app.main import create_app

SECRET = "gateway-test-secret-" + "x" * 64


async def _client(app):
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
