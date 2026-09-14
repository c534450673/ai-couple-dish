import json
from io import StringIO

import structlog

from packages.platform.config import Settings
from packages.platform.logging import configure_logging


def test_logs_are_json_and_exclude_secrets() -> None:
    stream = StringIO()
    settings = Settings(DB_PASSWORD="pw", JWT_SECRET="x" * 64, SERVICE_NAME="test")
    configure_logging(settings, stream=stream)
    structlog.get_logger().info(
        "operation",
        requestId="r1",
        module="catalog",
        operation="list",
        result="ok",
        durationMs=1,
        Authorization="Bearer secret",
        password="secret",
    )
    payload = json.loads(stream.getvalue())
    assert payload["requestId"] == "r1"
    assert "Authorization" not in payload and "password" not in payload
