import json
import logging
from io import StringIO
from uuid import UUID, uuid4

import pytest
import structlog
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core import middleware as middleware_module
from app.core.config import Settings
from app.core.logging import configure_logging, sanitize_event
from app.core.middleware import RequestContextMiddleware
from app.core.request_context import request_id_var

BASE_SETTINGS = {
    "DB_PASSWORD": "db-secret",
    "JWT_SECRET": "x" * 64,
    "SERVICE_NAME": "test-service",
    "RELEASE_SHA": "test-release",
}


def test_log_sanitizer_removes_sensitive_and_exception_fields() -> None:
    phone_value = "138" + "0013" + "8000"
    event = sanitize_event(
        {
            "requestId": "req-1",
            "authorization": "Bearer secret",
            "phone": phone_value,
            "body": "private note",
            "exception": "token=must-not-leak",
            "exc_info": RuntimeError("token=must-not-leak"),
            "operation": "request_complete",
        }
    )
    encoded = json.dumps(event, ensure_ascii=False)
    assert event == {"requestId": "req-1", "operation": "request_complete"}
    assert "secret" not in encoded
    assert phone_value not in encoded
    assert "private note" not in encoded
    assert "must-not-leak" not in encoded


def test_configured_logging_emits_allowlisted_json_with_service_metadata() -> None:
    stream = StringIO()
    settings = Settings(_env_file=None, **BASE_SETTINGS)
    configure_logging(settings, stream=stream)

    structlog.get_logger().info(
        "request_complete",
        module="http",
        operation="request",
        result="completed",
        token="must-not-leak",  # noqa: S106
    )

    event = json.loads(stream.getvalue())
    assert event["event"] == "request_complete"
    assert event["service"] == "test-service"
    assert event["release"] == "test-release"
    assert event["level"] == "info"
    assert event["module"] == "http"
    assert "must-not-leak" not in stream.getvalue()

    logging.getLogger().handlers.clear()


def test_configured_poster_logging_emits_exact_six_field_json() -> None:
    stream = StringIO()
    settings = Settings(_env_file=None, **BASE_SETTINGS)
    configure_logging(settings, stream=stream)

    structlog.get_logger().error(
        "poster_private_event_name",
        requestId="poster-request",
        module="poster",
        operation="generate.decode",
        result="rejected_1",
        durationMs=7,
        errorCode="IMAGE_CANDIDATE_DECODE",
        path="must-not-leak",
    )

    event = json.loads(stream.getvalue())
    assert event == {
        "requestId": "poster-request",
        "module": "poster",
        "operation": "generate.decode",
        "result": "rejected_1",
        "durationMs": 7,
        "errorCode": "IMAGE_CANDIDATE_DECODE",
    }

    logging.getLogger().handlers.clear()


def test_configured_feed_expiry_logging_emits_exact_six_field_json() -> None:
    stream = StringIO()
    settings = Settings(_env_file=None, **BASE_SETTINGS)
    configure_logging(settings, stream=stream)

    structlog.get_logger().error(
        "private-feed-expiry-event",
        requestId="run-1",
        module="feed_expiry",
        operation="expire_due",
        result="processed_1",
        durationMs=1,
        errorCode="NONE",
        feedId=700,
        content="private feed content",
        receiverId=701,
    )

    assert json.loads(stream.getvalue()) == {
        "requestId": "run-1",
        "module": "feed_expiry",
        "operation": "expire_due",
        "result": "processed_1",
        "durationMs": 1,
        "errorCode": "NONE",
    }
    assert "private feed content" not in stream.getvalue()
    logging.getLogger().handlers.clear()


def app_for_request_logging() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/items/{item_id}")
    async def item(item_id: int, request: Request) -> dict[str, str | int]:
        return {"item_id": item_id, "request_id": request_id_var.get()}

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("private-body=must-not-leak")

    return app


async def test_middleware_accepts_valid_uuid_and_logs_route_template() -> None:
    request_id = str(uuid4())
    with structlog.testing.capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(app=app_for_request_logging()), base_url="http://test"
        ) as client:
            response = await client.get(
                "/items/42?token=must-not-leak",
                headers={"X-Request-ID": request_id, "Authorization": "Bearer must-not-leak"},
            )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id
    assert logs[0]["route"] == "/items/{item_id}"
    assert logs[0]["status"] == 200
    assert "must-not-leak" not in json.dumps(logs)
    assert request_id_var.get() == "unknown"


async def test_middleware_replaces_invalid_request_id() -> None:
    with structlog.testing.capture_logs():
        async with AsyncClient(
            transport=ASGITransport(app=app_for_request_logging()), base_url="http://test"
        ) as client:
            response = await client.get("/items/42", headers={"X-Request-ID": "not-a-uuid"})

    generated = response.headers["X-Request-ID"]
    assert str(UUID(generated)) == generated
    assert generated != "not-a-uuid"


async def test_middleware_logs_and_cleans_context_when_handler_raises() -> None:
    request_id = str(uuid4())
    with structlog.testing.capture_logs() as logs:
        async with AsyncClient(
            transport=ASGITransport(app=app_for_request_logging(), raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/crash", headers={"X-Request-ID": request_id})

    assert response.status_code == 500
    assert logs[0]["requestId"] == request_id
    assert logs[0]["route"] == "/crash"
    assert logs[0]["status"] == 500
    assert logs[0]["result"] == "error"
    assert "must-not-leak" not in json.dumps(logs)
    assert request_id_var.get() == "unknown"


async def test_middleware_cleans_context_when_request_logger_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingLogger:
        async def ainfo(self, _event: str, **_fields: object) -> None:
            raise RuntimeError("logging failed")

    monkeypatch.setattr(middleware_module, "logger", FailingLogger())

    async with AsyncClient(
        transport=ASGITransport(app=app_for_request_logging()), base_url="http://test"
    ) as client:
        with pytest.raises(RuntimeError, match="logging failed"):
            await client.get("/items/42")

    assert request_id_var.get() == "unknown"
