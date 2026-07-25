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
        Settings(  # noqa: S106
            _env_file=None,
            DB_PASSWORD="db-secret",  # noqa: S106
            JWT_SECRET="too-short",  # noqa: S106
        )
    assert "至少64字符" in str(error.value)
    assert "too-short" not in str(error.value)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, APP_ENV="prod", CORS_ORIGINS="*", **BASE)
