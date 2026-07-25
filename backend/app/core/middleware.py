from time import perf_counter
from uuid import UUID, uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import request_id_var

logger = structlog.get_logger()


def safe_request_id(candidate: str | None) -> str:
    if candidate:
        try:
            return str(UUID(candidate))
        except ValueError:
            pass
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = safe_request_id(request.headers.get("X-Request-ID"))
        token = request_id_var.set(request_id)
        started = perf_counter()
        request.state.request_id = request_id
        request.state.request_started = started
        response: Response | None = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            try:
                await logger.ainfo(
                    "http_request_completed",
                    requestId=request_id,
                    module="http",
                    operation="request",
                    result="completed" if response is not None else "error",
                    durationMs=round((perf_counter() - started) * 1000),
                    method=request.method,
                    route=getattr(route, "path", "unmatched"),
                    status=response.status_code if response is not None else 500,
                    errorCode=(
                        "NONE"
                        if response is not None and response.status_code < 400
                        else "HTTP_ERROR"
                    ),
                )
            finally:
                request_id_var.reset(token)
