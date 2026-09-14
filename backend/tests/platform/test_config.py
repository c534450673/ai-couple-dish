import pytest

from packages.platform.config import Settings


def test_settings_require_long_jwt_secret() -> None:
    with pytest.raises(ValueError):
        Settings(  # noqa: S106
            DB_PASSWORD="pw",  # noqa: S106
            JWT_SECRET="too-short",  # noqa: S106
        )
