# FastAPI 基础设施与接口合同实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不停止现有 Spring Boot 服务的前提下，在 `backend/` 内建立可运行、可测试、可回滚的 Python 3.12 + FastAPI 基础设施和 Java/FastAPI 黑盒合同门禁，为后续 193 个接口按业务域迁移提供稳定基线。

**Architecture:** 迁移期让 Maven 与 Python 工程在 `backend/` 共存：Java 继续作为行为参考，FastAPI 使用 `backend/app/`、`backend/tests/`、`backend/migrations/` 和 `backend/Dockerfile.fastapi`。公网与 H5 始终只访问同源 `/api`；Nginx 按明确模块路由到单一写入者，禁止随机双写。MySQL 真实 schema 是 Alembic 基线的唯一事实来源，Spring OpenAPI、Controller/DTO、H5 调用和现有测试共同定义兼容合同。

**Tech Stack:** Python 3.12、uv、FastAPI、Pydantic v2、SQLAlchemy 2 async、asyncmy、Alembic、MySQL 8、redis-py asyncio、PyJWT HS512、bcrypt、structlog、Uvicorn、pytest、httpx、Testcontainers、Ruff、mypy。

## Global Constraints

- Python 固定为 `>=3.12,<3.13`；提交 `backend/uv.lock`，所有自动化安装使用 `uv sync --frozen`。
- FastAPI 路径保留现有 `/api` 前缀、camelCase path、HTTP method、query/body 位置、字段名和日期格式。
- 响应保持 `{"code": int, "message": string, "data": T | null}`；成功默认 `code=200`、`message="操作成功"`。
- 未授权返回 HTTP 401 + body `code=401`；参数错误返回 HTTP 400 + body `code=400`；现有业务异常默认保持 HTTP 200 + 非 200 业务码。
- H5 继续请求相对 `/api`，迁移期不得直接跨域访问 FastAPI 8000 端口。
- MySQL 8、Redis 7、现有表名、列名、软删除 `is_deleted` 和主要 Redis key/TTL 保持兼容。
- 迁移期每个写 endpoint 只有一个活动写入者；禁止代理层双写，禁止 Spring 与 Python 同时执行同一调度任务。
- JWT 继续使用 HS512、`Authorization: Bearer`、`sub` 用户 ID、`userId` claim、`jti` 和 `logout:blacklist:<jti>`。
- `JWT_SECRET` 至少 64 字符，所有密钥只从环境注入；任何源码、fixture、日志、URL、截图和镜像层不得含真实密钥。
- 日志必须结构化并包含 `requestId`、模块、操作、结果、耗时、状态码/业务码；不得记录 JWT、密码、验证码、完整手机号、情侣码、私密正文或请求 body。
- CORS `OPTIONS` 必须在认证前处理；生产环境不得以 `*` 配合 credentials。
- SQLAlchemy 每请求一个 `AsyncSession`；事务边界在 service，repository 不包含业务判断。
- Pydantic 默认 422 不得直接暴露，必须转换为兼容的 HTTP 400 Result envelope。
- 数据库迁移不得在 Web 进程启动时自动执行；Alembic 通过独立命令/Job 执行。
- 本工作包不迁移业务 Controller、不切换 H5 默认后端、不删除 Java；业务域迁移和 Java 退役使用后续独立计划。

## File Map

- `backend/pyproject.toml`：Python 版本、运行依赖、开发依赖和工具配置。
- `backend/uv.lock`：uv 解析出的精确依赖锁。
- `backend/app/main.py`：FastAPI app factory、lifespan、middleware 与 router 装配。
- `backend/app/core/`：配置、日志、错误、认证、限流和 request context。
- `backend/app/db/`：SQLAlchemy engine/session、schema inspector 与基础模型约定。
- `backend/app/redis/`：Redis client 生命周期和 key builder。
- `backend/app/api/health.py`：live/ready/兼容 health 路由。
- `backend/migrations/`：Alembic 配置、基线 revision 和 schema 断言。
- `backend/contracts/`：Spring OpenAPI、规范化 route inventory、错误码与 Redis key 合同。
- `backend/scripts/`：合同导出、schema dump 规范化和双实现比较脚本。
- `backend/tests/`：Python unit、API、contract、MySQL/Redis integration 与 security tests。
- `backend/Dockerfile.fastapi`：迁移期 FastAPI 独立镜像，不覆盖 Java Dockerfile。
- `deploy/dev/docker/docker-compose.fastapi.yml`：双栈开发覆盖文件。
- `deploy/dev/docker/nginx/conf.d/api-fastapi-foundation.conf`：只切 FastAPI health 的确定性路由。
- `.github/workflows/fastapi.yml`：Python 独立 CI 门禁。
- `docs/runbooks/fastapi-dual-stack.md`：启动、合同、切流、回滚和数据基线操作手册。

---

### Task 1: 建立可复现的 Python 3.12 工程

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/uv.lock`
- Create: `backend/app/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_project_baseline.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: 仓库现有 `backend/` 与 Python 3.12 运行时。
- Produces: `uv run pytest`、`uv run ruff check .`、`uv run mypy app` 三个稳定命令；后续任务只从 `backend/pyproject.toml` 获取依赖。

- [ ] **Step 1: 写工程基线失败测试**

```python
# backend/tests/test_project_baseline.py
from importlib import import_module
from pathlib import Path


def test_python_runtime_and_required_modules() -> None:
    import sys

    assert sys.version_info[:2] == (3, 12)
    for module in ("fastapi", "pydantic", "sqlalchemy", "redis", "structlog"):
        assert import_module(module)


def test_lockfile_is_committed() -> None:
    assert (Path(__file__).parents[1] / "uv.lock").is_file()
```

- [ ] **Step 2: 运行测试确认缺少 Python 工程**

Run: `cd backend && python3.12 -m pytest tests/test_project_baseline.py -q`

Expected: FAIL，因为尚无 pytest 依赖或 `uv.lock`。

- [ ] **Step 3: 写最小 pyproject**

```toml
# backend/pyproject.toml
[project]
name = "ai-couple-dish-backend"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "alembic>=1.14,<2",
  "asyncmy>=0.2,<1",
  "bcrypt>=4.2,<6",
  "fastapi>=0.115,<1",
  "pydantic>=2.10,<3",
  "pydantic-settings>=2.7,<3",
  "pyjwt[crypto]>=2.10,<3",
  "python-multipart>=0.0.20,<1",
  "redis[hiredis]>=5,<7",
  "sqlalchemy[asyncio]>=2.0,<2.1",
  "structlog>=24,<27",
  "uvicorn[standard]>=0.34,<1",
]

[dependency-groups]
dev = [
  "httpx>=0.28,<1",
  "mypy>=1.14,<2",
  "pytest>=8,<9",
  "pytest-asyncio>=0.25,<2",
  "pytest-cov>=6,<8",
  "pyyaml>=6,<7",
  "ruff>=0.9,<1",
  "testcontainers[mysql,redis]>=4.9,<5",
  "types-redis>=4.6,<5",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
  "contract: black-box Spring/FastAPI contract tests",
  "integration: tests requiring MySQL 8 and Redis 7",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC", "S"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
```

在 `.gitignore` 追加且仅追加：

```gitignore
# Python backend
backend/.venv/
backend/.pytest_cache/
backend/.mypy_cache/
backend/.ruff_cache/
backend/.coverage
backend/htmlcov/
```

- [ ] **Step 4: 生成锁文件并运行门禁**

Run: `cd backend && uv lock && uv sync --frozen && uv run pytest tests/test_project_baseline.py -q && uv run ruff check app tests && uv run mypy app`

Expected: `2 passed`；Ruff 和 mypy exit 0。

- [ ] **Step 5: 提交**

```bash
git add .gitignore backend/pyproject.toml backend/uv.lock backend/app/__init__.py backend/tests/__init__.py backend/tests/test_project_baseline.py
git commit -m "build: 建立FastAPI Python工程"
```

### Task 2: 实现严格环境配置

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/core/test_config.py`
- Create: `backend/.env.fastapi.example`

**Interfaces:**
- Consumes: `pydantic-settings`；现有 `DB_*`、`REDIS_*`、`JWT_*`、`CORS_ORIGINS`、`FILE_UPLOAD_PATH` 环境变量。
- Produces: `Settings`、`get_settings() -> Settings`、`Settings.database_url`、`Settings.redis_url`。

- [ ] **Step 1: 写配置失败测试**

```python
# backend/tests/core/test_config.py
import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE = {
    "DB_PASSWORD": "db-secret",
    "JWT_SECRET": "x" * 64,
}


def test_settings_reuse_existing_environment_names() -> None:
    settings = Settings(_env_file=None, **BASE)
    assert str(settings.database_url).startswith("mysql+asyncmy://root:db-secret@localhost:3306/")
    assert str(settings.redis_url) == "redis://localhost:6379/0"
    assert settings.api_prefix == "/api"
    assert settings.jwt_algorithm == "HS512"


def test_short_jwt_secret_fails_without_leaking_value() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="too-short")
    assert "至少64字符" in str(error.value)
    assert "too-short" not in str(error.value)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, APP_ENV="prod", CORS_ORIGINS="*", **BASE)
```

- [ ] **Step 2: 运行测试确认模块不存在**

Run: `cd backend && uv run pytest tests/core/test_config.py -q`

Expected: FAIL with `ModuleNotFoundError: app.core.config`。

- [ ] **Step 3: 实现 Settings**

```python
# backend/app/core/config.py
from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    app_env: Literal["local", "test", "staging", "prod"] = Field("local", alias="APP_ENV")
    service_name: str = Field("ai-couple-dish-fastapi", alias="SERVICE_NAME")
    release_sha: str = Field("dev", alias="RELEASE_SHA")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    api_prefix: str = "/api"

    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: int = Field(3306, alias="DB_PORT")
    db_name: str = Field("ai_couple_dish", alias="DB_NAME")
    db_username: str = Field("root", alias="DB_USERNAME")
    db_password: SecretStr = Field(alias="DB_PASSWORD")
    database_pool_size: int = Field(10, alias="DATABASE_POOL_SIZE", ge=1)
    database_max_overflow: int = Field(10, alias="DATABASE_MAX_OVERFLOW", ge=0)

    redis_host: str = Field("localhost", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")
    redis_password: SecretStr | None = Field(None, alias="REDIS_PASSWORD")
    redis_database: int = Field(0, alias="REDIS_DATABASE", ge=0)

    jwt_secret: SecretStr = Field(alias="JWT_SECRET")
    jwt_expiration: int = Field(604_800_000, alias="JWT_EXPIRATION", gt=0)
    jwt_algorithm: Literal["HS512"] = "HS512"
    cors_origins: str = Field(
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )
    file_upload_path: str = Field("/tmp/uploads", alias="FILE_UPLOAD_PATH")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 64:
            raise ValueError("JWT_SECRET 至少64字符")
        return value

    @model_validator(mode="after")
    def validate_production_cors(self) -> "Settings":
        if self.app_env == "prod" and "*" in self.allowed_origins:
            raise ValueError("生产环境 CORS_ORIGINS 不得包含通配符")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_username)
        password = quote_plus(self.db_password.get_secret_value())
        return f"mysql+asyncmy://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

    @computed_field
    @property
    def redis_url(self) -> str:
        auth = ""
        if self.redis_password:
            auth = f":{quote_plus(self.redis_password.get_secret_value())}@"
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

`backend/.env.fastapi.example` 只列变量名和安全占位符，`JWT_SECRET` 使用 `<inject-at-runtime-min-64-chars>`，不得填入可用密钥。

- [ ] **Step 4: 运行配置测试和静态检查**

Run: `cd backend && uv run pytest tests/core/test_config.py -q && uv run ruff check app/core tests/core && uv run mypy app/core`

Expected: `3 passed`；Ruff 和 mypy exit 0。

- [ ] **Step 5: 提交**

```bash
git add backend/app/core backend/tests/core backend/.env.fastapi.example
git commit -m "feat: 增加FastAPI严格环境配置"
```

### Task 3: 实现 Result envelope、异常映射和结构化请求日志

**Files:**
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/app/core/request_context.py`
- Create: `backend/app/core/middleware.py`
- Create: `backend/tests/core/test_errors.py`
- Create: `backend/tests/core/test_request_logging.py`

**Interfaces:**
- Consumes: `Settings`。
- Produces: `Result[T]`、`BusinessError(code, message)`、`install_exception_handlers(app)`、`RequestContextMiddleware`、`configure_logging(settings)`。

- [ ] **Step 1: 写 envelope 与脱敏日志失败测试**

```python
# backend/tests/core/test_errors.py
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import BusinessError, install_exception_handlers


def app_for_errors() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/business")
    async def business() -> None:
        raise BusinessError(2006, "未绑定情侣关系")

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("token=must-not-leak")

    return app


async def test_business_error_keeps_http_200_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_errors()), base_url="http://test") as client:
        response = await client.get("/business")
    assert response.status_code == 200
    assert response.json() == {"code": 2006, "message": "未绑定情侣关系", "data": None}


async def test_unhandled_error_is_generic() -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_errors(), raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/crash")
    assert response.status_code == 500
    assert response.json() == {"code": 500, "message": "服务器内部错误，请稍后重试", "data": None}
    assert "must-not-leak" not in response.text
```

```python
# backend/tests/core/test_request_logging.py
import json

from app.core.logging import sanitize_event


def test_log_sanitizer_removes_sensitive_fields() -> None:
    phone_value = "138" + "0013" + "8000"
    event = sanitize_event({
        "requestId": "req-1",
        "authorization": "Bearer secret",
        "phone": phone_value,
        "body": "private note",
        "operation": "request_complete",
    })
    encoded = json.dumps(event, ensure_ascii=False)
    assert event == {"requestId": "req-1", "operation": "request_complete"}
    assert "secret" not in encoded
    assert phone_value not in encoded
    assert "private note" not in encoded
```

- [ ] **Step 2: 运行测试确认实现缺失**

Run: `cd backend && uv run pytest tests/core/test_errors.py tests/core/test_request_logging.py -q`

Expected: FAIL because `app.core.errors` and `app.core.logging` do not exist。

- [ ] **Step 3: 实现最小合同**

```python
# backend/app/core/errors.py
from typing import Generic, TypeVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

T = TypeVar("T")
logger = structlog.get_logger()


class Result(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None


class BusinessError(RuntimeError):
    def __init__(self, code: int, message: str, *, http_status: int = 200) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def result_response(status: int, code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message, "data": None})


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_handler(_: Request, error: BusinessError) -> JSONResponse:
        return result_response(error.http_status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        messages = [str(item["msg"]) for item in error.errors()]
        return result_response(400, 400, ", ".join(messages))

    @app.exception_handler(Exception)
    async def exception_handler(_: Request, error: Exception) -> JSONResponse:
        await logger.aexception(
            "unhandled_exception",
            module="http",
            operation="exception_handler",
            result="error",
            errorCode="INTERNAL_ERROR",
            exc_info=error,
        )
        return result_response(500, 500, "服务器内部错误，请稍后重试")
```

`logging.py` 必须用 `structlog` 输出 JSON，并以 allowlist 方式只保留：`timestamp`、`level`、`event`、`requestId`、`service`、`release`、`module`、`operation`、`result`、`durationMs`、`method`、`route`、`status`、`errorCode`、`dependency`。`RequestContextMiddleware` 接受或生成 UUID request ID，将其写入 `X-Request-ID`，记录路由模板而不是包含 query 的完整 URL。

```python
# backend/app/core/request_context.py
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")
```

```python
# backend/app/core/logging.py
import logging
import sys
from typing import Any

import structlog

ALLOWED_FIELDS = {
    "timestamp", "level", "event", "requestId", "service", "release", "module",
    "operation", "result", "durationMs", "method", "route", "status", "errorCode",
    "dependency", "exception",
}


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key in ALLOWED_FIELDS}


def allowlist_processor(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    return sanitize_event(event_dict)


def configure_logging(level: str) -> None:
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            allowlist_processor,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
```

```python
# backend/app/core/middleware.py
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
        response: Response | None = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            await logger.ainfo(
                "http_request_completed",
                requestId=request_id,
                module="http",
                operation="request",
                result="completed" if response else "error",
                durationMs=round((perf_counter() - started) * 1000),
                method=request.method,
                route=getattr(route, "path", "unmatched"),
                status=response.status_code if response else 500,
                errorCode="NONE" if response and response.status_code < 400 else "HTTP_ERROR",
            )
            request_id_var.reset(token)
```

- [ ] **Step 4: 运行测试和敏感模式扫描**

Run: `cd backend && uv run pytest tests/core/test_errors.py tests/core/test_request_logging.py -q && uv run ruff check app/core tests/core && uv run mypy app/core`

Expected: `3 passed`；日志测试中敏感值 0 命中。

- [ ] **Step 5: 提交**

```bash
git add backend/app/core backend/tests/core
git commit -m "feat: 对齐FastAPI响应与结构化日志"
```

### Task 4: 建立 app factory、生命周期和健康检查

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/api/test_health.py`
- Create: `backend/tests/api/test_cors.py`

**Interfaces:**
- Consumes: `Settings`、`configure_logging()`、`RequestContextMiddleware`、`install_exception_handlers()`；Task 5 将向 `app.state` 注入 `db` 与 `redis`。
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`、`GET /api/health/live`、`GET /api/health/ready`、迁移期兼容 `GET /api/actuator/health`。

- [ ] **Step 1: 写健康检查与 CORS 失败测试**

```python
# backend/tests/api/test_health.py
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)


async def test_live_does_not_require_dependencies() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "操作成功", "data": {"status": "UP"}}


async def test_ready_reports_dependency_failure_without_details() -> None:
    app = create_app(settings())
    async def readiness() -> dict[str, bool]:
        return {"database": False, "redis": True}

    app.state.readiness = readiness
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["data"] == {"status": "DOWN"}
    assert "password" not in response.text.lower()
```

```python
# backend/tests/api/test_cors.py
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.api.test_health import settings


async def test_options_is_handled_before_authentication() -> None:
    app = create_app(settings())
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/api/health/live", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: 运行测试确认 app factory 缺失**

Run: `cd backend && uv run pytest tests/api/test_health.py tests/api/test_cors.py -q`

Expected: FAIL with `ModuleNotFoundError: app.main`。

- [ ] **Step 3: 实现 app factory 和 health router**

```python
# backend/app/api/health.py
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, Any]:
    return {"code": 200, "message": "操作成功", "data": {"status": "UP"}}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    check: Callable[[], Awaitable[dict[str, bool]]] = request.app.state.readiness
    states = await check()
    is_ready = all(states.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "code": 200 if is_ready else 503,
            "message": "操作成功" if is_ready else "服务暂不可用",
            "data": {"status": "UP" if is_ready else "DOWN"},
        },
    )
```

```python
# backend/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = active_settings
        yield

    app = FastAPI(
        title="AI Couple Dish API",
        docs_url=None if active_settings.app_env == "prod" else "/api/docs",
        openapi_url=None if active_settings.app_env == "prod" else "/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["Authorization", "Content-Disposition", "X-Request-ID"],
    )
    install_exception_handlers(app)
    app.include_router(health_router, prefix=active_settings.api_prefix)
    return app


app = create_app()
```

兼容 `/api/actuator/health` 必须复用同一个 ready 函数，不能复制第二套依赖判定。

- [ ] **Step 4: 运行 API 测试**

Run: `cd backend && uv run pytest tests/api/test_health.py tests/api/test_cors.py -q && uv run ruff check app tests/api && uv run mypy app`

Expected: `3 passed`；Ruff 和 mypy exit 0。

- [ ] **Step 5: 提交**

```bash
git add backend/app/api backend/app/main.py backend/tests/api
git commit -m "feat: 增加FastAPI生命周期与健康检查"
```

### Task 5: 建立异步 MySQL 与 Redis 生命周期

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/redis/__init__.py`
- Create: `backend/app/redis/client.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/conftest.py`
- Create: `backend/tests/integration/test_dependencies.py`

**Interfaces:**
- Consumes: `Settings.database_url`、`Settings.redis_url`。
- Produces: `Database.connect()/close()/session()/ping()`、`RedisClient.connect()/close()/ping()`、`get_session()`、`get_redis()`；app lifespan 创建并关闭资源。

- [ ] **Step 1: 写真实 MySQL 8/Redis 7 失败测试**

```python
# backend/tests/integration/test_dependencies.py
import pytest
from sqlalchemy import text

from app.db.session import Database
from app.redis.client import RedisClient


@pytest.mark.integration
async def test_mysql_uses_real_mysql_dialect(mysql_url: str) -> None:
    database = Database(mysql_url, pool_size=2, max_overflow=0)
    await database.connect()
    async with database.session() as session:
        assert (await session.execute(text("SELECT VERSION()"))).scalar_one().startswith("8.")
    await database.close()


@pytest.mark.integration
async def test_redis_round_trip_is_namespaced(redis_url: str) -> None:
    client = RedisClient(redis_url)
    await client.connect()
    await client.raw.set("test:foundation:ping", "ok", ex=5)
    assert await client.raw.get("test:foundation:ping") == "ok"
    await client.close()
```

`conftest.py` 使用 Testcontainers 启动 `mysql:8.0` 与 `redis:7-alpine`，数据库 URL 必须是 `mysql+asyncmy://...`；测试结束删除容器，不连接共享开发数据库。

- [ ] **Step 2: 运行测试确认适配器缺失**

Run: `cd backend && uv run pytest -m integration tests/integration/test_dependencies.py -q`

Expected: FAIL because `app.db.session` and `app.redis.client` do not exist。

- [ ] **Step 3: 实现资源适配器**

```python
# backend/app/db/session.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Database:
    def __init__(self, url: str, *, pool_size: int, max_overflow: int) -> None:
        self.engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self._factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def connect(self) -> None:
        await self.ping()

    async def close(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> bool:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


async def get_session(request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.db.session() as session:
        yield session
```

```python
# backend/app/redis/client.py
from fastapi import Request
from redis.asyncio import Redis


class RedisClient:
    def __init__(self, url: str) -> None:
        self.raw = Redis.from_url(url, decode_responses=True, health_check_interval=30)

    async def connect(self) -> None:
        await self.ping()

    async def close(self) -> None:
        await self.raw.aclose()

    async def ping(self) -> bool:
        return bool(await self.raw.ping())


def get_redis(request) -> Redis:
    return request.app.state.redis.raw
```

`main.py` lifespan 必须按 DB -> Redis 顺序连接，按 Redis -> DB 逆序关闭；连接失败记录脱敏依赖名后中止启动。readiness 使用 `asyncio.gather(..., return_exceptions=True)`，只返回布尔状态。

- [ ] **Step 4: 运行集成、API 和静态门禁**

Run: `cd backend && uv run pytest -m integration tests/integration/test_dependencies.py -q && uv run pytest tests/api/test_health.py -q && uv run ruff check app tests && uv run mypy app`

Expected: MySQL/Redis `2 passed`，health 测试通过，Ruff/mypy exit 0。

- [ ] **Step 5: 提交**

```bash
git add backend/app/db backend/app/redis backend/app/main.py backend/tests/integration
git commit -m "feat: 接入FastAPI异步MySQL与Redis"
```

### Task 6: 对齐 JWT、登出黑名单和密码哈希

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/core/passwords.py`
- Create: `backend/app/redis/keys.py`
- Create: `backend/tests/core/test_auth.py`
- Create: `backend/tests/core/test_passwords.py`
- Create: `backend/tests/integration/test_auth_blacklist.py`

**Interfaces:**
- Consumes: `Settings.jwt_secret`、`Settings.jwt_expiration`、Redis client。
- Produces: `TokenClaims(user_id, jti, expires_at)`、`create_access_token()`、`decode_access_token()`、`current_user_id()` dependency、`hash_password()`、`verify_password()`、`logout_blacklist_key(jti)`。

- [ ] **Step 1: 写 Spring JWT 兼容和 bcrypt 失败测试**

```python
# backend/tests/core/test_auth.py
from datetime import UTC, datetime, timedelta

import jwt

from app.core.auth import decode_access_token


SECRET = "s" * 64


def test_decodes_spring_hs512_claim_shape() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "userId": 42,
            "jti": "contract-jti",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS512",
    )
    claims = decode_access_token(token, SECRET)
    assert claims.user_id == 42
    assert claims.jti == "contract-jti"
```

```python
# backend/tests/core/test_passwords.py
from app.core.passwords import hash_password, verify_password


def test_bcrypt_hash_never_contains_plaintext() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$2")
    assert "correct horse" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)
```

- [ ] **Step 2: 运行测试确认认证模块缺失**

Run: `cd backend && uv run pytest tests/core/test_auth.py tests/core/test_passwords.py -q`

Expected: FAIL because auth/password modules do not exist。

- [ ] **Step 3: 实现兼容认证**

```python
# backend/app/redis/keys.py
def logout_blacklist_key(jti: str) -> str:
    if not jti or ":" in jti:
        raise ValueError("invalid jti")
    return f"logout:blacklist:{jti}"


def verify_code_key(phone: str) -> str:
    return f"user:verify:code:{phone}"


def couple_code_key(code: str) -> str:
    return f"couple:code:{code}"
```

```python
# backend/app/core/auth.py
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Header, Request
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.errors import BusinessError
from app.redis.keys import logout_blacklist_key


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    jti: str
    expires_at: datetime


def create_access_token(user_id: int, secret: str, expiration_ms: int) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "userId": user_id,
        "jti": __import__("uuid").uuid4().hex,
        "iat": now,
        "exp": now + timedelta(milliseconds=expiration_ms),
    }
    return jwt.encode(claims, secret, algorithm="HS512")


def decode_access_token(token: str, secret: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS512"])
        return TokenClaims(
            user_id=int(payload["sub"]),
            jti=str(payload["jti"]),
            expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=UTC),
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise BusinessError(401, "登录已过期，请重新登录", http_status=401) from error


async def current_user_id(
    request: Request,
    authorization: str | None = Header(default=None),
) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise BusinessError(401, "请先登录", http_status=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token or " " in token or "," in token:
        raise BusinessError(401, "登录信息无效", http_status=401)
    settings: Settings = request.app.state.settings
    claims = decode_access_token(token, settings.jwt_secret.get_secret_value())
    if await request.app.state.redis.raw.exists(logout_blacklist_key(claims.jti)):
        raise BusinessError(401, "登录已过期，请重新登录", http_status=401)
    return claims.user_id
```

`current_user_id()` 必须：解析 Bearer header；拒绝缺失/重复/非 Bearer header；decode HS512；查询 `logout:blacklist:<jti>`；返回 `int user_id`。任何日志只记录错误类别和 route，不记录 token、jti 原值或手机号。密码函数直接调用 `bcrypt.hashpw/checkpw`，不得自行实现加盐。

```python
# backend/app/core/passwords.py
import bcrypt

from app.core.errors import BusinessError


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if not encoded or len(encoded) > 72:
        raise BusinessError(400, "密码长度不合法", http_status=400)
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), encoded_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False
```

- [ ] **Step 4: 验证黑名单 TTL 和认证错误**

Run: `cd backend && uv run pytest tests/core/test_auth.py tests/core/test_passwords.py tests/integration/test_auth_blacklist.py -q && uv run ruff check app/core app/redis tests/core tests/integration && uv run mypy app/core app/redis`

Expected: 所有测试通过；黑名单 key TTL 与 token 剩余秒数相差不超过 1 秒；缺 token/无效 token/黑名单 token 均为 HTTP 401 Result envelope。

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/auth.py backend/app/core/passwords.py backend/app/redis/keys.py backend/tests/core backend/tests/integration/test_auth_blacklist.py
git commit -m "feat: 对齐FastAPI认证与密码安全"
```

### Task 7: 实现 Redis Lua 限流基础设施

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Create: `backend/tests/core/test_rate_limit.py`
- Create: `backend/tests/integration/test_rate_limit_redis.py`

**Interfaces:**
- Consumes: Redis client、`current_user_id()`。
- Produces: `RateLimitPolicy(scope, requests, window_seconds)`、`check_rate_limit()`；key 前缀固定 `rate_limit:`。

- [ ] **Step 1: 写原子限流失败测试**

```python
# backend/tests/integration/test_rate_limit_redis.py
import asyncio

import pytest

from app.core.rate_limit import RateLimitPolicy, check_rate_limit


@pytest.mark.integration
async def test_concurrent_limit_is_atomic(redis_client) -> None:
    policy = RateLimitPolicy(scope="user", requests=3, window_seconds=60)
    results = await asyncio.gather(
        *(check_rate_limit(redis_client, policy, "user-42") for _ in range(6))
    )
    assert results.count(True) == 3
    assert results.count(False) == 3
```

- [ ] **Step 2: 运行测试确认限流模块缺失**

Run: `cd backend && uv run pytest -m integration tests/integration/test_rate_limit_redis.py -q`

Expected: FAIL because `app.core.rate_limit` does not exist。

- [ ] **Step 3: 实现 Lua INCR + EXPIRE**

```python
# backend/app/core/rate_limit.py
from dataclasses import dataclass

from redis.asyncio import Redis

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    requests: int
    window_seconds: int


async def check_rate_limit(
    redis: Redis,
    policy: RateLimitPolicy,
    identity_hash: str,
) -> bool:
    key = f"rate_limit:{policy.scope}:{identity_hash}"
    current, _ttl = await redis.eval(RATE_LIMIT_SCRIPT, 1, key, policy.window_seconds)
    return int(current) <= policy.requests
```

HTTP adapter 被限流时返回 HTTP 429 + `{"code":429,"message":"操作过于频繁，请稍后重试","data":null}`。identity 必须是用户 ID 或 IP 的单向 HMAC，不得把 token 或完整 IP 直接写入 key/log。

- [ ] **Step 4: 运行并发测试和静态门禁**

Run: `cd backend && uv run pytest tests/core/test_rate_limit.py -q && uv run pytest -m integration tests/integration/test_rate_limit_redis.py -q && uv run ruff check app/core tests && uv run mypy app/core`

Expected: unit/integration 全部通过；6 个并发请求中恰好 3 个允许。

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/rate_limit.py backend/tests/core/test_rate_limit.py backend/tests/integration/test_rate_limit_redis.py
git commit -m "feat: 增加FastAPI原子限流"
```

### Task 8: 固化 Spring、H5、错误码和 Redis 合同清单

**Files:**
- Create: `backend/contracts/README.md`
- Create: `backend/contracts/spring-openapi.json`
- Create: `backend/contracts/routes.json`
- Create: `backend/contracts/h5-consumers.json`
- Create: `backend/contracts/error-codes.json`
- Create: `backend/contracts/redis-keys.json`
- Create: `backend/scripts/export_spring_contract.py`
- Create: `backend/tests/contract/fixtures/openapi-minimal.json`
- Create: `backend/tests/contract/test_export_spring_contract.py`

**Interfaces:**
- Consumes: 运行中 Spring `/api/v3/api-docs`、27 个 Controller/DTO、`frontend-h5/src/api/index.js`、`frontend-h5/src/api/ai.js`。
- Produces: 确定性 `routes.json`，每项为 `{method,path,controller,sideEffect,owner,migrationBatch}`；初始 `owner="spring"`。总数必须为 193，H5 强制兼容面为 58 个 API 加一个菜谱直接调用。

- [ ] **Step 1: 写规范化导出失败测试**

```python
# backend/tests/contract/test_export_spring_contract.py
import json
from pathlib import Path

from scripts.export_spring_contract import normalize_openapi, route_inventory


FIXTURE = Path(__file__).parent / "fixtures" / "openapi-minimal.json"


def test_normalization_removes_environment_noise() -> None:
    source = json.loads(FIXTURE.read_text())
    normalized = normalize_openapi(source)
    assert "servers" not in normalized
    assert normalized["paths"] == dict(sorted(normalized["paths"].items()))


def test_route_inventory_is_method_and_path_sorted() -> None:
    source = json.loads(FIXTURE.read_text())
    routes = route_inventory(source)
    assert routes == sorted(routes, key=lambda item: (item["path"], item["method"]))
    assert all(item["owner"] == "spring" for item in routes)
```

- [ ] **Step 2: 运行测试确认导出器不存在**

Run: `cd backend && uv run pytest tests/contract/test_export_spring_contract.py -q`

Expected: FAIL because `scripts.export_spring_contract` does not exist。

- [ ] **Step 3: 实现确定性导出器**

```python
# backend/scripts/export_spring_contract.py
import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx


def normalize_openapi(document: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(document)
    normalized.pop("servers", None)
    normalized["paths"] = {
        path: {
            method: operation
            for method, operation in sorted(item.items())
            if method.lower() in {"get", "post", "put", "delete", "patch"}
        }
        for path, item in sorted(normalized.get("paths", {}).items())
    }
    return normalized


def route_inventory(document: dict[str, Any]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for path, item in normalize_openapi(document)["paths"].items():
        contract_path = path if path.startswith("/api/") else f"/api{path}"
        for method, operation in item.items():
            routes.append({
                "method": method.upper(),
                "path": contract_path,
                "controller": operation.get("tags", ["unknown"])[0],
                "sideEffect": method.upper() != "GET",
                "owner": "spring",
                "migrationBatch": None,
            })
    return sorted(routes, key=lambda route: (route["path"], route["method"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    args = parser.parse_args()
    response = httpx.get(args.url, timeout=30)
    response.raise_for_status()
    normalized = normalize_openapi(response.json())
    args.output.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    args.routes.write_text(json.dumps(route_inventory(normalized), ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
```

导出后人工/脚本补充 `migrationBatch`：`user/couple=1`，`menu/recipe/note/feed/anniversary/wish/notification/upload=2`，`ai=3`，互动成长模块 `=4`，cart/order/invite/poster/timeCapsule/jobs `=5`。`sideEffect` 对 `GET` 中会触发写入或外部调用的例外必须显式改为 true。

`error-codes.json` 至少逐项登记现有可观察代码 `400,401,429,1001-1006,2001-2008,3001-3003,4001-4002,5001-5003,6001-6004,7001-7003,8001-8003,8501-8502,8601-8603,8701-8702,8801-8804,8901-8903,8951-8953,9001-9007,9999`，字段为 `code,httpStatus,message,ambiguousUsages`。9001-9005 的重复语义必须保留并标记，不能静默重编号。

`redis-keys.json` 必须精确记录：

```json
[
  {"pattern":"logout:blacklist:<jti>","ttl":"token remaining lifetime","sensitive":true},
  {"pattern":"user:verify:code:<phone>","ttl":"configured verification TTL","sensitive":true},
  {"pattern":"user:verify:expire:<phone>","ttl":"60 seconds","sensitive":true},
  {"pattern":"couple:code:<8-char-code>","ttl":"7 days","sensitive":true},
  {"pattern":"couple:code:user:<userId>","ttl":"7 days","sensitive":true},
  {"pattern":"ai:session:msg:<userId>:<sessionId>","ttl":"7 days","sensitive":true},
  {"pattern":"ai:session:pending:<userId>:<sessionId>","ttl":"30 minutes","sensitive":true},
  {"pattern":"rate_limit:<scope>:<identityHmac>","ttl":"policy window","sensitive":false}
]
```

测试必须断言 pattern 唯一。

- [ ] **Step 4: 导出真实清单并验证计数/敏感信息**

Run: `cd backend && uv run python scripts/export_spring_contract.py --url http://127.0.0.1:8080/api/v3/api-docs --output contracts/spring-openapi.json --routes contracts/routes.json`

Run: `cd backend && uv run pytest tests/contract/test_export_spring_contract.py -q && uv run python -c "import json; assert len(json.load(open('contracts/routes.json'))) == 193"`

Expected: `2 passed`，route count 为 193；合同文件中真实 JWT、手机号、情侣码和密钥模式 0 命中。若 Spring OpenAPI 省略 Controller 中的 route，以 Controller 静态盘点补齐并在 `contracts/README.md` 记录来源。

- [ ] **Step 5: 提交**

```bash
git add backend/contracts backend/scripts/export_spring_contract.py backend/tests/contract
git commit -m "test: 固化Spring与H5接口合同"
```

### Task 9: 建立 MySQL schema 审计与 Alembic 基线门禁

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_existing_mysql_baseline.py`
- Create: `backend/contracts/mysql-schema.json`
- Create: `backend/contracts/mysql-schema.sha256`
- Create: `backend/scripts/capture_mysql_schema.py`
- Create: `backend/scripts/verify_mysql_schema.py`
- Create: `backend/tests/integration/test_schema_contract.py`
- Create: `backend/tests/contract/test_schema_snapshot.py`

**Interfaces:**
- Consumes: 真实 MySQL 8 `information_schema`、36 个 Java entity、`schema.sql`、`schema-test.sql`、V1.1/V1.2 和一次性修复 SQL。
- Produces: 排序稳定且不含数据的 `mysql-schema.json`、SHA-256、no-op Alembic baseline `0001`；只有 schema 核验通过后才允许 `alembic stamp 0001_existing_mysql_baseline`。

- [ ] **Step 1: 写 schema 快照失败测试**

```python
# backend/tests/contract/test_schema_snapshot.py
import hashlib
from pathlib import Path


def test_schema_hash_matches_snapshot() -> None:
    root = Path(__file__).parents[2] / "contracts"
    payload = (root / "mysql-schema.json").read_bytes()
    expected = (root / "mysql-schema.sha256").read_text().strip()
    assert hashlib.sha256(payload).hexdigest() == expected
```

```python
# backend/tests/integration/test_schema_contract.py
import pytest

from scripts.capture_mysql_schema import capture_schema


REQUIRED_TABLES = {
    "t_user", "t_couple", "t_menu", "t_recipe", "t_food_note", "t_feed",
    "t_anniversary", "t_wish", "t_notification", "t_note_like",
}


@pytest.mark.integration
async def test_mysql_schema_contains_required_tables_and_lunar_column(mysql_engine) -> None:
    snapshot = await capture_schema(mysql_engine)
    assert REQUIRED_TABLES <= set(snapshot["tables"])
    anniversary = snapshot["tables"]["t_anniversary"]
    assert "is_lunar_date" in anniversary["columns"]
```

- [ ] **Step 2: 运行测试确认 schema 工具缺失**

Run: `cd backend && uv run pytest tests/contract/test_schema_snapshot.py tests/integration/test_schema_contract.py -q`

Expected: FAIL because snapshot and capture module do not exist。

- [ ] **Step 3: 实现结构化 schema 捕获与 no-op baseline**

`capture_mysql_schema.py` 必须使用 SQLAlchemy `inspect()`/`information_schema` 结构化读取并按 table、column、index、foreign key 名称排序；只保存 table/column/type/null/default/index/unique/foreign-key/charset/collation，不保存 row、AUTO_INCREMENT 当前值、host、用户名或 DSN。输出使用 `json.dumps(..., sort_keys=True, separators=(",", ":")) + "\n"`。

```python
# backend/migrations/versions/0001_existing_mysql_baseline.py
"""Register the audited pre-FastAPI MySQL schema without changing it."""

revision = "0001_existing_mysql_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("Existing production baseline cannot be downgraded")
```

`verify_mysql_schema.py` 重新捕获目标数据库并与提交快照比较，输出仅包含新增/缺失 table、column、index 的名称和数量；不得输出 DSN 或数据值。检测差异必须 exit 1；`--stamp` 仅在无差异时调用 Alembic stamp。

- [ ] **Step 4: 在隔离 MySQL 8 上生成并验证基线**

Run: `cd backend && uv run python scripts/capture_mysql_schema.py --output contracts/mysql-schema.json --sha256 contracts/mysql-schema.sha256`

Run: `cd backend && uv run pytest tests/contract/test_schema_snapshot.py -q && uv run pytest -m integration tests/integration/test_schema_contract.py -q && uv run python scripts/verify_mysql_schema.py`

Expected: snapshot hash 通过；required schema 通过；无 drift 时 verifier exit 0。生产库只允许在只读 dump、备份校验和 owner 审批后运行 `--stamp`，本任务不连接生产。

- [ ] **Step 5: 提交**

```bash
git add backend/alembic.ini backend/migrations backend/contracts/mysql-schema.json backend/contracts/mysql-schema.sha256 backend/scripts/capture_mysql_schema.py backend/scripts/verify_mysql_schema.py backend/tests/contract/test_schema_snapshot.py backend/tests/integration/test_schema_contract.py
git commit -m "feat: 建立MySQL审计与Alembic基线"
```

### Task 10: 建立 Java/FastAPI 黑盒合同比较器

**Files:**
- Create: `backend/contracts/cases/foundation.json`
- Create: `backend/contracts/migration-ownership.json`
- Create: `backend/scripts/compare_backends.py`
- Create: `backend/tests/contract/test_compare_backends.py`
- Create: `backend/tests/contract/test_migration_ownership.py`

**Interfaces:**
- Consumes: `SPRING_BASE_URL`、`FASTAPI_BASE_URL`、`contracts/routes.json`、环境注入的测试 token；绝不把 token 写入 case 或输出。
- Produces: `compare_case(case, spring_client, fastapi_client) -> Comparison`；只有 `owner="fastapi"` 的 route 才要求双实现相等，`owner="spring"` 明确跳过且统计。

- [ ] **Step 1: 写比较器失败测试**

```python
# backend/tests/contract/test_compare_backends.py
from scripts.compare_backends import normalize_response


def test_response_normalization_preserves_contract_fields() -> None:
    normalized = normalize_response(
        200,
        {"code": 200, "message": "操作成功", "data": {"id": 1}},
        ignored_json_paths=["data.createTime"],
    )
    assert normalized == {
        "httpStatus": 200,
        "body": {"code": 200, "message": "操作成功", "data": {"id": 1}},
    }


def test_normalization_rejects_non_result_body() -> None:
    try:
        normalize_response(422, {"detail": []}, ignored_json_paths=[])
    except ValueError as error:
        assert "Result envelope" in str(error)
    else:
        raise AssertionError("FastAPI default 422 must fail the contract")
```

```python
# backend/tests/contract/test_migration_ownership.py
import json
from pathlib import Path


def test_each_route_has_exactly_one_owner() -> None:
    document = json.loads((Path(__file__).parents[2] / "contracts/migration-ownership.json").read_text())
    assert document["defaultOwner"] == "spring"
    assert document["fastapiRoutes"] == []
    assert document["operationalFastapiRoutes"] == [
        "GET /api/health/live",
        "GET /api/health/ready",
        "GET /api/actuator/health",
    ]
    all_routes = document["fastapiRoutes"] + document["operationalFastapiRoutes"]
    assert len(all_routes) == len(set(all_routes))
```

- [ ] **Step 2: 运行测试确认比较器缺失**

Run: `cd backend && uv run pytest tests/contract/test_compare_backends.py tests/contract/test_migration_ownership.py -q`

Expected: FAIL because compare script and ownership file do not exist。

- [ ] **Step 3: 实现严格比较规则**

`foundation.json` 固定覆盖 FastAPI 自身的 live、ready、兼容 actuator health、未知 route 404、无 token 访问受保护测试 app 的 401、无效 JSON/字段的 HTTP 400。这些是 `operationalFastapiRoutes`，只验证 FastAPI，不伪装成 Spring 等价接口。每个 case 明确 `method,path,headers,query,json,expectedHttpStatus,expectedCode,ignoredJsonPaths,sideEffect=false`。写 case、短信、AI 和通知 side effect 在基础阶段禁止执行。

```python
# backend/scripts/compare_backends.py
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Comparison:
    case_id: str
    equal: bool
    spring: dict[str, Any]
    fastapi: dict[str, Any]


def normalize_response(
    status: int,
    body: dict[str, Any],
    *,
    ignored_json_paths: list[str],
) -> dict[str, Any]:
    if set(body) != {"code", "message", "data"}:
        raise ValueError("response is not a Result envelope")
    normalized = {"httpStatus": status, "body": body.copy()}
    for path in ignored_json_paths:
        _remove_path(normalized["body"], path.split("."))
    return normalized


def _remove_path(value: dict[str, Any], parts: list[str]) -> None:
    current: Any = value
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)
```

差异输出只允许 `caseId`、method、route 模板、HTTP/status/code、缺失/新增 JSON path；禁止输出 header、token、请求 body、完整响应私密 data。case 如果 `sideEffect=true`，比较器必须拒绝运行，除非显式 `--allow-side-effects` 且使用隔离数据库。

- [ ] **Step 4: 运行比较器自测和双服务只读 case**

Run: `cd backend && uv run pytest tests/contract -q`

Run: `cd backend && uv run python scripts/compare_backends.py --spring "$SPRING_BASE_URL" --fastapi "$FASTAPI_BASE_URL" --cases contracts/cases/foundation.json`

Expected: 单测全部通过；三个 operational route 通过 FastAPI 自检；`fastapiRoutes` 初始为空，193 个 Spring 业务 route 全部计入 skipped，不得伪报 migrated。

- [ ] **Step 5: 提交**

```bash
git add backend/contracts/cases backend/contracts/migration-ownership.json backend/scripts/compare_backends.py backend/tests/contract
git commit -m "test: 增加双后端黑盒合同门禁"
```

### Task 11: 建立双栈 Docker 与同源确定性路由

**Files:**
- Create: `backend/Dockerfile.fastapi`
- Create: `deploy/dev/docker/docker-compose.fastapi.yml`
- Create: `deploy/dev/docker/nginx/conf.d/api-fastapi-foundation.conf`
- Create: `backend/tests/deploy/test_dual_stack_config.py`
- Create: `backend/tests/deploy/test_docker_image.py`

**Interfaces:**
- Consumes: Java `backend:8080`、FastAPI `fastapi-backend:8000`、现有 MySQL/Redis、相对 `/api`。
- Produces: `docker compose -f docker-compose.yml -f docker-compose.fastapi.yml` 双栈；只有三个 health route 进入 FastAPI，其余 `/api/**` 仍进入 Spring。

- [ ] **Step 1: 写部署拓扑失败测试**

```python
# backend/tests/deploy/test_dual_stack_config.py
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[3]


def test_fastapi_overlay_does_not_replace_spring_writer() -> None:
    overlay = yaml.safe_load((ROOT / "deploy/dev/docker/docker-compose.fastapi.yml").read_text())
    service = overlay["services"]["fastapi-backend"]
    assert service["build"]["dockerfile"] == "Dockerfile.fastapi"
    assert service["expose"] == ["8000"]
    assert "ports" not in service
    assert "backend" not in overlay["services"]


def test_nginx_defaults_all_business_routes_to_spring() -> None:
    config = (ROOT / "deploy/dev/docker/nginx/conf.d/api-fastapi-foundation.conf").read_text()
    assert "location = /api/health/live" in config
    assert "location = /api/health/ready" in config
    assert "location /api/" in config
    assert "proxy_pass http://spring_backend;" in config
    assert "split_clients" not in config
    assert "mirror" not in config
```

- [ ] **Step 2: 运行测试确认双栈配置缺失**

Run: `cd backend && uv run pytest tests/deploy/test_dual_stack_config.py -q`

Expected: FAIL because overlay and replacement Nginx config do not exist。

- [ ] **Step 3: 写非 root FastAPI 镜像和 Compose overlay**

```dockerfile
# backend/Dockerfile.fastapi
FROM ghcr.io/astral-sh/uv:0.11.21 AS uv-bin
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=uv-bin /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=3)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
```

```yaml
# deploy/dev/docker/docker-compose.fastapi.yml
services:
  fastapi-backend:
    build:
      context: ../../../backend
      dockerfile: Dockerfile.fastapi
    restart: unless-stopped
    environment:
      APP_ENV: local
      DB_HOST: mysql
      DB_PORT: 3306
      DB_NAME: ${MYSQL_DATABASE:-ai_couple_dish}
      DB_USERNAME: ${MYSQL_USER:-aicoupledish}
      DB_PASSWORD: ${MYSQL_PASSWORD:-dev_password}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD:-redis_dev_pass}
      JWT_SECRET: ${JWT_SECRET:?JWT_SECRET must contain at least 64 characters}
      CORS_ORIGINS: http://localhost:3000,http://127.0.0.1:3000
      RELEASE_SHA: ${RELEASE_SHA:-dev}
    expose:
      - "8000"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - dev-network

  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d/api-fastapi-foundation.conf:/etc/nginx/conf.d/api.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - backend
      - fastapi-backend
```

Nginx replacement config 定义 `upstream spring_backend { server backend:8080; }` 和 `upstream fastapi_backend { server fastapi-backend:8000; }`。三个 exact location 为 `/api/health/live`、`/api/health/ready`、`/api/actuator/health`，`proxy_pass http://fastapi_backend;`；通用 `location /api/` 固定 `proxy_pass http://spring_backend;`。所有 location 传递 `X-Request-ID`、`Authorization`、`X-Forwarded-*`，不得记录 query/body；SSE 业务尚未切流，不在本任务添加 AI 代理例外。

- [ ] **Step 4: 验证配置、镜像用户和同源路由**

Run: `cd backend && uv run pytest tests/deploy -q`

Run: `cd deploy/dev/docker && JWT_SECRET="$(openssl rand -hex 64)" docker compose -f docker-compose.yml -f docker-compose.fastapi.yml config --quiet`

Run: `cd deploy/dev/docker && JWT_SECRET="$(openssl rand -hex 64)" docker compose -f docker-compose.yml -f docker-compose.fastapi.yml up -d --build && curl -fsS http://127.0.0.1/api/health/ready`

Expected: deploy tests 通过；Compose config exit 0；同源 health 返回 Result envelope；容器内 `id -u` 非 0；未知业务 route 仍由 Spring 处理。验证后只停止本次 compose project，不删除共享 volume。

- [ ] **Step 5: 提交**

```bash
git add backend/pyproject.toml backend/uv.lock backend/Dockerfile.fastapi backend/tests/deploy deploy/dev/docker/docker-compose.fastapi.yml deploy/dev/docker/nginx/conf.d/api-fastapi-foundation.conf
git commit -m "deploy: 增加FastAPI双栈基础路由"
```

### Task 12: 建立 Python CI、运行手册和工作包验收

**Files:**
- Create: `.github/workflows/fastapi.yml`
- Create: `backend/scripts/verify_fastapi_foundation.sh`
- Create: `backend/tests/security/test_no_sensitive_artifacts.py`
- Create: `docs/runbooks/fastapi-dual-stack.md`
- Modify: `README.md`
- Modify: `docs/ENVIRONMENT.md`

**Interfaces:**
- Consumes: Tasks 1-11 的全部命令与产物。
- Produces: 独立 `fastapi` CI 门禁、单命令验收脚本、开发/切流/回滚 runbook；README 明确 Java 是迁移期参考，FastAPI 尚未承载业务 route。

- [ ] **Step 1: 写敏感产物和文档状态失败测试**

```python
# backend/tests/security/test_no_sensitive_artifacts.py
import re
from pathlib import Path


ROOT = Path(__file__).parents[3]
TEXT_SUFFIXES = {".py", ".toml", ".json", ".md", ".yml", ".yaml", ".conf", ".sh"}
PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b1[3-9]\d{9}\b"),
]


def test_fastapi_artifacts_contain_no_secret_or_real_phone() -> None:
    roots = [ROOT / "backend/app", ROOT / "backend/contracts", ROOT / "docs/runbooks"]
    violations: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                text = path.read_text(errors="ignore")
                if any(pattern.search(text) for pattern in PATTERNS):
                    violations.append(str(path.relative_to(ROOT)))
    assert violations == []
```

- [ ] **Step 2: 运行测试确认 CI/runbook 缺失**

Run: `cd backend && uv run pytest tests/security/test_no_sensitive_artifacts.py -q && test -f ../.github/workflows/fastapi.yml && test -f ../docs/runbooks/fastapi-dual-stack.md`

Expected: FAIL because CI and runbook do not exist。

- [ ] **Step 3: 写 CI 和单命令验证脚本**

```yaml
# .github/workflows/fastapi.yml
name: FastAPI

on:
  pull_request:
    paths: ["backend/app/**", "backend/tests/**", "backend/migrations/**", "backend/contracts/**", "backend/pyproject.toml", "backend/uv.lock", "backend/Dockerfile.fastapi", ".github/workflows/fastapi.yml"]
  push:
    branches: [main]
    paths: ["backend/app/**", "backend/tests/**", "backend/migrations/**", "backend/contracts/**", "backend/pyproject.toml", "backend/uv.lock", "backend/Dockerfile.fastapi", ".github/workflows/fastapi.yml"]

jobs:
  python-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          version: "0.11.21"
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: uv sync --frozen
        working-directory: backend
      - run: uv lock --check
        working-directory: backend
      - run: uv run ruff check app tests scripts
        working-directory: backend
      - run: uv run mypy app
        working-directory: backend
      - run: uv run pytest -m "not integration" --cov=app --cov-report=term-missing
        working-directory: backend
      - run: uv run pytest -m integration
        working-directory: backend
      - run: docker build -f backend/Dockerfile.fastapi backend
```

```bash
# backend/scripts/verify_fastapi_foundation.sh
#!/usr/bin/env bash
set -euo pipefail

uv lock --check
uv sync --frozen
uv run ruff check app tests scripts
uv run mypy app
uv run pytest -m "not integration" --cov=app --cov-report=term-missing
uv run pytest -m integration
uv run python scripts/verify_mysql_schema.py
docker build -f Dockerfile.fastapi .
```

运行手册必须给出：前置 Python/MySQL/Redis；无密钥示例的环境变量清单；本地 Uvicorn；双栈 Compose；Spring OpenAPI 导出；schema audit/stamp 防护；合同比较；模块 owner 变更流程；Nginx 回滚到 Spring 的单文件操作；服务和临时容器精确清理；`/api/ai/chat/stream` 未来切流时 `proxy_buffering off` 的要求；生产不得使用本地上传 `emptyDir` 的风险。

README 和 ENVIRONMENT 只描述已实现现状，不得写“后端已迁移完成”；明确 `backend/Dockerfile` 仍是 Java，`backend/Dockerfile.fastapi` 是迁移期基础服务。

- [ ] **Step 4: 运行工作包完整验收**

Run: `cd backend && bash scripts/verify_fastapi_foundation.sh`

Run: `git diff --check && git status --short`

Expected: lock、Ruff、mypy、全部 unit/API/contract/integration/security tests、schema verifier 和 Docker build 均 exit 0；git status 只包含本任务预期文件。

额外只读记录：`cd frontend-h5 && npm test -- --run && npm run build && npx playwright test`。FastAPI 基础服务尚未接管业务 route，因此前端结果应与 Task 10 基线一致；任何差异都阻塞提交。

- [ ] **Step 5: GitNexus 范围检测与提交**

对所有修改的现有 symbol 先运行 `gitnexus_impact(..., direction="upstream")`；若工具仍没有 `gitnexus_detect_changes`，必须记录不可用事实并以 staged 文件清单、`git diff --cached --check`、敏感模式扫描替代，不能伪报通过。

```bash
git add .github/workflows/fastapi.yml backend/scripts/verify_fastapi_foundation.sh backend/tests/security docs/runbooks/fastapi-dual-stack.md README.md docs/ENVIRONMENT.md
git commit -m "ci: 建立FastAPI基础设施验收门禁"
```

## Completion Evidence

只有以下证据全部具备，才完成本工作包：

1. `backend/uv.lock` 可在 Python 3.12 上 `uv sync --frozen`。
2. Ruff、mypy、Python unit/API/contract/security、MySQL 8/Redis 7 integration 全部通过。
3. FastAPI live/ready/兼容 health、Result envelope、400/401/429/500、request ID 和敏感日志测试通过。
4. Spring route inventory 为 193，H5 强制合同面已登记，所有 route 有唯一 owner；业务 owner 仍为 Spring。
5. MySQL schema snapshot/hash、drift verifier 和 Alembic baseline 在隔离 MySQL 8 通过；未连接或 stamp 生产库。
6. 双栈 Compose 中 FastAPI 不暴露浏览器端口，只有 health exact routes 进入 FastAPI，所有业务 `/api/**` 仍进入 Spring。
7. FastAPI Docker 镜像以非 root 用户运行，构建不含开发依赖或真实密钥。
8. H5 Vitest、build 和 Playwright 基线无回归。
9. runbook 已验证启动、合同、schema、切流和回滚命令；Java 活动源码和部署尚未删除。

通过此门槛后，下一份独立计划迁移 `user + couple + notification` 身份与情侣边界；不能直接跳到菜单、AI 或 Java 退役。
