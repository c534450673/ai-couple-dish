from functools import lru_cache
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import quote_plus, urlsplit

from pydantic import Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

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
    file_upload_path: str = Field("/tmp/uploads", alias="FILE_UPLOAD_PATH")  # noqa: S108
    file_base_url: str = Field("http://localhost:8080/api/uploads", alias="FILE_BASE_URL")
    file_public_path: str = Field("/api/uploads", alias="FILE_PUBLIC_PATH")
    poster_render_concurrency: int = Field(2, alias="POSTER_RENDER_CONCURRENCY", ge=1, le=4)

    # AI 网关只接受环境变量注入，日志和错误响应不会暴露密钥。
    ai_base_url: str = Field("", alias="AI_BASE_URL")
    ai_api_key: SecretStr = Field(default=SecretStr(""), alias="AI_API_KEY")
    ai_model: str = Field("kimi-k2.6", alias="AI_MODEL", min_length=1, max_length=128)
    ai_timeout_ms: int = Field(120_000, alias="AI_TIMEOUT_MS", ge=1_000, le=300_000)
    ai_max_history: int = Field(20, alias="AI_MAX_HISTORY", ge=2, le=100)
    ai_max_tool_rounds: int = Field(5, alias="AI_MAX_TOOL_ROUNDS", ge=1, le=10)

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def mask_jwt_secret_in_validation_errors(cls, value: object) -> object:
        if isinstance(value, str):
            return SecretStr(value)
        return value

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

    @model_validator(mode="after")
    def validate_file_publish_url(self) -> "Settings":
        parsed = urlsplit(self.file_base_url)
        if parsed.query or parsed.fragment or "\\" in self.file_base_url or "%" in parsed.path:
            raise ValueError("FILE_BASE_URL 必须是不含查询参数或片段的规范 URL")
        if parsed.scheme:
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
                raise ValueError("FILE_BASE_URL 仅允许 http/https URL")
        elif (
            parsed.netloc
            or not self.file_base_url.startswith("/")
            or self.file_base_url.startswith("//")
        ):
            raise ValueError("FILE_BASE_URL 相对地址必须从根路径开始")

        public_path = self.file_public_path
        if (
            not public_path.startswith("/")
            or public_path.startswith("//")
            or "\\" in public_path
            or "%" in public_path
            or "?" in public_path
            or "#" in public_path
        ):
            raise ValueError("FILE_PUBLIC_PATH 必须是规范的根相对路径")

        def canonical(path: str) -> str:
            normalized = path.rstrip("/") or "/"
            raw_parts = normalized[1:].split("/") if normalized != "/" else []
            if any(part in {".", "..", ""} for part in raw_parts):
                raise ValueError("文件公开路径不得包含空段或点段")
            return PurePosixPath(normalized).as_posix()

        if canonical(parsed.path) != canonical(public_path):
            raise ValueError("FILE_PUBLIC_PATH 必须与 FILE_BASE_URL 的路径一致")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_username)
        password = quote_plus(self.db_password.get_secret_value())
        return f"mysql+asyncmy://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        auth = ""
        if self.redis_password:
            auth = f":{quote_plus(self.redis_password.get_secret_value())}@"
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
