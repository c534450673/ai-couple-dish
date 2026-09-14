import json
from io import StringIO

import structlog

from packages.platform.config import Settings
from packages.platform.logging import configure_logging


def test_logs_are_json_and_exclude_secrets() -> None:
    stream = StringIO()
    settings = Settings(  # noqa: S106
        DB_PASSWORD="pw",  # noqa: S106
        JWT_SECRET="x" * 64,  # noqa: S106
        SERVICE_NAME="test",
    )
    configure_logging(settings, stream=stream)
    structlog.get_logger().info(
        "operation",
        requestId="r1",
        module="catalog",
        operation="list",
        result="ok",
        durationMs=1,
        Authorization="Bearer secret",  # noqa: S106
        password="secret",  # noqa: S106
    )
    payload = json.loads(stream.getvalue())
    assert payload["requestId"] == "r1"
    assert "Authorization" not in payload and "password" not in payload
