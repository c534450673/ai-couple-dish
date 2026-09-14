"""迁移期 HTTP 网关：认证、请求透传与统一可观测性。"""

from __future__ import annotations

import os
from time import perf_counter
from uuid import uuid4

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from packages.platform.auth import decode_token

logger = structlog.get_logger()
_PROTECTED_PREFIXES = ("/api/",)
_PUBLIC_PATHS = {"/api/user/login", "/api/health", "/health"}
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _secret(value: str | None) -> str:
    resolved = value or os.getenv("JWT_SECRET")
    if not resolved:
        raise RuntimeError("JWT_SECRET 未配置")
    if len(resolved) < 64:
        raise ValueError("JWT_SECRET 至少64字符")
    return resolved


def _response(status: int, code: int, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "data": None},
        headers={"X-Request-ID": request_id},
    )


def _log_fields(
    request_id: str, operation: str, result: str, started: float, error: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request_id,
        "module": "gateway",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error,
    }


def create_app(
    upstream: str | None = None,
    *,
    jwt_secret: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = 5.0,
) -> FastAPI:
    app = FastAPI(title="AI Couple Dish Gateway")
    app.state.jwt_secret = _secret(jwt_secret)
    app.state.upstream = upstream or os.getenv("GATEWAY_UPSTREAM", "http://127.0.0.1:8080")
    app.state.transport = transport
    app.state.timeout_seconds = timeout_seconds

    @app.middleware("http")
    async def middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = perf_counter()
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        path = request.url.path
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin", "*")
            response = Response(
                status_code=204,
                headers={
                    "X-Request-ID": request_id,
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization,Content-Type,X-Request-ID",
                },
            )
            await logger.ainfo(
                "gateway_request_completed",
                **_log_fields(request_id, "options", "success", started),
                status=204,
                method=request.method,
                route=path,
            )
            return response
        if path.startswith(_PROTECTED_PREFIXES) and path not in _PUBLIC_PATHS:
            authorization = request.headers.get("Authorization")
            token = (
                authorization.removeprefix("Bearer ").strip()
                if authorization and authorization.startswith("Bearer ")
                else ""
            )
            if not token or " " in token or "," in token:
                await logger.awarning(
                    "gateway_auth_rejected",
                    **_log_fields(request_id, "authenticate", "rejected", started, "AUTH_REQUIRED"),
                    status=401,
                    method=request.method,
                    route=path,
                )
                return _response(401, 401, "请先登录", request_id)
            try:
                decode_token(token, secret=app.state.jwt_secret)
            except Exception:
                await logger.awarning(
                    "gateway_auth_rejected",
                    **_log_fields(request_id, "authenticate", "rejected", started, "AUTH_INVALID"),
                    status=401,
                    method=request.method,
                    route=path,
                )
                return _response(401, 401, "登录信息无效", request_id)
        if path.startswith("/api/"):
            try:
                body = await request.body()
                headers = {
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in _HOP_BY_HOP
                }
                headers["X-Request-ID"] = request_id
                url = f"{app.state.upstream.rstrip('/')}{path}"
                if request.url.query:
                    url = f"{url}?{request.url.query}"
                timeout = httpx.Timeout(
                    app.state.timeout_seconds, connect=app.state.timeout_seconds
                )
                async with httpx.AsyncClient(
                    transport=app.state.transport, timeout=timeout
                ) as client:
                    upstream_response = await client.request(
                        request.method, url, headers=headers, content=body
                    )
                response_headers = {
                    key: value
                    for key, value in upstream_response.headers.items()
                    if key.lower() not in _HOP_BY_HOP
                }
                response_headers["X-Request-ID"] = request_id
                await logger.ainfo(
                    "gateway_request_completed",
                    **_log_fields(request_id, "proxy", "success", started),
                    status=upstream_response.status_code,
                    method=request.method,
                    route=path,
                )
                return Response(
                    content=upstream_response.content,
                    status_code=upstream_response.status_code,
                    headers=response_headers,
                )
            except (httpx.TimeoutException, TimeoutError):
                await logger.aerror(
                    "gateway_request_failed",
                    **_log_fields(request_id, "proxy", "error", started, "UPSTREAM_TIMEOUT"),
                    status=504,
                    method=request.method,
                    route=path,
                )
                return _response(504, 504, "服务暂时不可用", request_id)
            except Exception:
                await logger.aerror(
                    "gateway_request_failed",
                    **_log_fields(request_id, "proxy", "error", started, "UPSTREAM_ERROR"),
                    status=502,
                    method=request.method,
                    route=path,
                )
                return _response(502, 502, "上游服务暂时不可用", request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "gateway"}

    return app


try:
    app = create_app()
except (RuntimeError, ValueError):
    # 本地导入/静态检查没有密钥时保持模块可导入；实际启动应注入 JWT_SECRET。
    app = FastAPI(title="AI Couple Dish Gateway")

    @app.get("/health")
    async def health_unconfigured() -> dict[str, str]:
        return {"status": "ok", "service": "gateway"}
