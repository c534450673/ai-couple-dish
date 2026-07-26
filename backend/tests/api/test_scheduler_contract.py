import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.core.config import Settings
from scripts import run_couple_code_reminder

BACKEND = Path(__file__).parents[2]
BASE = {"DB_PASSWORD": "db-secret", "JWT_SECRET": "x" * 64}


class CapturingLogger:
    def __init__(self) -> None:
        self.info: list[dict[str, object]] = []
        self.error: list[dict[str, object]] = []

    async def ainfo(self, _event: str, **fields: object) -> None:
        self.info.append(fields)

    async def aerror(self, _event: str, **fields: object) -> None:
        self.error.append(fields)


def test_scheduler_is_disabled_by_default_and_ttls_are_safe() -> None:
    settings = Settings(_env_file=None, **BASE)

    assert settings.fastapi_scheduler_enabled is False
    assert settings.couple_code_scheduler_lock_ttl_seconds >= 60
    assert settings.couple_code_scheduler_marker_ttl_seconds >= 26 * 60 * 60


def test_scheduler_ownership_is_separate_from_http_ownership() -> None:
    http_ownership = json.loads((BACKEND / "contracts/migration-ownership.json").read_text())
    scheduler_ownership = json.loads((BACKEND / "contracts/scheduler-ownership.json").read_text())

    assert http_ownership["defaultOwner"] == "spring"
    assert http_ownership["fastapiRoutes"] == []
    contract = scheduler_ownership["couple_code_expiration_reminder"]
    assert contract["defaultOwner"] == "spring"
    assert contract["fastapiShadowCommand"] == "python -m scripts.run_couple_code_reminder"
    assert contract["singleWriter"] is True
    assert contract["schedule"] == "0 * * * *"
    assert contract["businessTimezone"] == "Asia/Shanghai"


def test_scheduler_help_needs_no_settings_or_dependencies() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "scripts.run_couple_code_reminder", "--help"],
        cwd=BACKEND,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "一次性执行" in result.stdout


async def test_disabled_scheduler_does_not_construct_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(_env_file=None, **BASE)

    def unexpected_dependency(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("disabled scheduler must not create dependencies")

    monkeypatch.setattr(run_couple_code_reminder, "Database", unexpected_dependency)
    monkeypatch.setattr(run_couple_code_reminder, "RedisClient", unexpected_dependency)

    assert await run_couple_code_reminder.execute(settings) == 2


async def test_cli_uses_info_for_success_and_error_for_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = CapturingLogger()
    monkeypatch.setattr(run_couple_code_reminder.structlog, "get_logger", lambda: logger)

    await run_couple_code_reminder._log_result(
        "request", "run", "completed", time.monotonic(), "NONE"
    )
    await run_couple_code_reminder._log_result(
        "request", "run", "failed", time.monotonic(), "DEPENDENCY"
    )

    assert len(logger.info) == 1
    assert len(logger.error) == 1
    assert set(logger.info[0]) == {
        "requestId",
        "module",
        "operation",
        "result",
        "durationMs",
        "errorCode",
    }
