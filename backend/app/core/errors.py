from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger()


class Result[T](BaseModel):
    code: int = 200
    message: str = "操作成功"
    data: T | None = None


class BusinessError(RuntimeError):
    def __init__(self, code: int, message: str, *, http_status: int = 200) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def result_response(status: int, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "data": None},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_handler(_: Request, error: BusinessError) -> JSONResponse:
        return result_response(error.http_status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        messages = [str(item["msg"]) for item in error.errors()]
        return result_response(400, 400, ", ".join(messages))

    @app.exception_handler(Exception)
    async def exception_handler(request: Request, _error: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        started = getattr(request.state, "request_started", None)
        duration_ms = max(0, round((perf_counter() - started) * 1000)) if started else 0
        await logger.aerror(
            "unhandled_exception",
            requestId=request_id,
            module="http",
            operation="exception_handler",
            result="error",
            durationMs=duration_ms,
            status=500,
            errorCode="INTERNAL_ERROR",
        )
        response = result_response(500, 500, "服务器内部错误，请稍后重试")
        response.headers["X-Request-ID"] = request_id
        return response
