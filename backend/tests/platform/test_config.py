import pytest

from packages.platform.config import Settings


def test_settings_require_long_jwt_secret() -> None:
    with pytest.raises(ValueError):
        Settings(DB_PASSWORD="pw", JWT_SECRET="too-short")
