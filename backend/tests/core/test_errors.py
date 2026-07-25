import json
from uuid import UUID

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.errors import BusinessError, Result, install_exception_handlers
from app.core.middleware import RequestContextMiddleware


class Payload(BaseModel):
    name: str


def app_for_errors() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/business")
    async def business() -> None:
        raise BusinessError(2006, "未绑定情侣关系")

    @app.get("/validate/{item_id}")
    async def validate(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("token=must-not-leak")

    return app


def app_with_middleware_and_errors() -> FastAPI:
    app = app_for_errors()
    app.add_middleware(RequestContextMiddleware)
    return app


def test_result_envelope_supports_typed_data() -> None:
    result = Result[Payload](code=0, message="ok", data=Payload(name="dish"))
    assert result.model_dump() == {"code": 0, "message": "ok", "data": {"name": "dish"}}


def test_result_envelope_uses_success_defaults() -> None:
    result = Result[Payload](data=Payload(name="dish"))
    assert result.model_dump() == {
        "code": 200,
        "message": "操作成功",
        "data": {"name": "dish"},
    }


async def test_business_error_keeps_http_200_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_for_errors()), base_url="http://test"
    ) as client:
        response = await client.get("/business")
    assert response.status_code == 200
    assert response.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}


async def test_request_validation_error_maps_status_and_body_to_400() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_for_errors()), base_url="http://test"
    ) as client:
        response = await client.get("/validate/not-an-integer")
    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["data"] is None
    assert response.json()["message"]


async def test_unhandled_error_is_generic_and_log_is_sanitized() -> None:
    with structlog.testing.capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(app=app_for_errors(), raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/crash")

    assert response.status_code == 500
    assert response.json() == {"code": 500, "message": "服务器内部错误，请稍后重试", "data": None}
    encoded_logs = json.dumps(logs, ensure_ascii=False)
    assert "must-not-leak" not in response.text
    assert "must-not-leak" not in encoded_logs
    assert len(logs) == 1
    event = logs[0]
    assert event["event"] == "unhandled_exception"
    assert event["module"] == "http"
    assert event["operation"] == "exception_handler"
    assert event["result"] == "error"
    assert event["errorCode"] == "INTERNAL_ERROR"
    assert event["status"] == 500
    assert isinstance(event["durationMs"], int)
    assert event["durationMs"] >= 0
    assert str(UUID(response.headers["X-Request-ID"])) == response.headers["X-Request-ID"]
    assert event["requestId"] == response.headers["X-Request-ID"]
    assert event["log_level"] == "error"


async def test_unhandled_error_keeps_request_id_after_middleware_cleanup() -> None:
    request_id = "d9ab8192-9917-4a5d-b81c-7194e3d85305"
    with structlog.testing.capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(
                app=app_with_middleware_and_errors(), raise_app_exceptions=False
            ),
            base_url="http://test",
        ) as client:
            response = await client.get("/crash", headers={"X-Request-ID": request_id})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == request_id
    exception_event = next(event for event in logs if event["event"] == "unhandled_exception")
    assert exception_event["requestId"] == request_id
    assert exception_event["module"] == "http"
    assert exception_event["operation"] == "exception_handler"
    assert exception_event["result"] == "error"
    assert isinstance(exception_event["durationMs"], int)
    assert exception_event["status"] == 500
    assert exception_event["errorCode"] == "INTERNAL_ERROR"
    assert "must-not-leak" not in json.dumps(logs)


@pytest.mark.parametrize("http_status", [400, 409])
async def test_business_error_can_override_http_status(http_status: int) -> None:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/business")
    async def business() -> None:
        raise BusinessError(9001, "conflict", http_status=http_status)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/business")
    assert response.status_code == http_status
    assert response.json() == {"code": 9001, "message": "conflict", "data": None}
