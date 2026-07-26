import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from scripts import run_feed_expiry

BACKEND = Path(__file__).parents[2]
BASE = {"DB_PASSWORD": "db-secret", "JWT_SECRET": "x" * 64}


def test_web_lifespan_has_no_feed_expiry_writer() -> None:
    source = (BACKEND / "app/main.py").read_text(encoding="utf-8")

    assert "_feed_expiry_loop" not in source
    assert "asyncio.create_task" not in source


def test_feed_expiry_is_disabled_and_owned_by_spring() -> None:
    settings = Settings(_env_file=None, **BASE)
    ownership = json.loads((BACKEND / "contracts/scheduler-ownership.json").read_text())

    assert settings.fastapi_feed_expiry_enabled is False
    assert ownership["feed_expiration"] == {
        "defaultOwner": "spring",
        "springTask": "FeedExpireTask.handleExpiredFeeds",
        "fastapiShadowCommand": "python -m scripts.run_feed_expiry",
        "enabledByDefault": False,
        "schedule": "*/10 * * * *",
        "businessTimezone": "Asia/Shanghai",
        "singleWriter": True,
        "switchPrerequisites": [
            "explicit FASTAPI_FEED_EXPIRY_ENABLED=true",
            "Spring task disabled by approved deployment change",
            "Feed mutating HTTP owner moved to FastAPI or Spring mutation uses "
            "row lock/status=0 conditional update",
            "single managed CronJob worker with monitoring and rollback approval",
        ],
    }


def test_feed_expiry_help_needs_no_settings_or_dependencies() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "scripts.run_feed_expiry", "--help"],
        cwd=BACKEND,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "一次性执行" in result.stdout


async def test_disabled_feed_expiry_does_not_construct_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(_env_file=None, **BASE)

    def unexpected_database(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("disabled feed expiry must not create database")

    monkeypatch.setattr(run_feed_expiry, "Database", unexpected_database)
    assert await run_feed_expiry.execute(settings) == 2


async def test_feed_expiry_rolls_back_run_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.rollbacks = 0

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def rollback(self) -> None:
            self.rollbacks += 1

    session = FakeSession()

    class FakeFactory:
        def __call__(self) -> FakeSession:
            return session

    class FakeDatabase:
        engine = object()

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def connect(self) -> None:
            return None

        async def close(self) -> None:
            return None

    async def fail_expiry(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("run failure")

    monkeypatch.setattr(run_feed_expiry, "Database", FakeDatabase)
    monkeypatch.setattr(
        run_feed_expiry,
        "async_sessionmaker",
        lambda *_args, **_kwargs: FakeFactory(),
    )
    monkeypatch.setattr(run_feed_expiry, "expire_due", fail_expiry)
    settings = Settings(_env_file=None, FASTAPI_FEED_EXPIRY_ENABLED=True, **BASE)

    assert await run_feed_expiry.execute(settings) == 1
    assert session.rollbacks == 1


@pytest.mark.parametrize(("close_fails", "expected"), [(False, 0), (True, 1)])
async def test_feed_expiry_success_and_close_exit_codes(
    monkeypatch: pytest.MonkeyPatch, close_fails: bool, expected: int
) -> None:
    class FakeSession:
        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    class FakeFactory:
        def __call__(self) -> FakeSession:
            return FakeSession()

    class FakeDatabase:
        engine = object()

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def connect(self) -> None:
            return None

        async def close(self) -> None:
            if close_fails:
                raise RuntimeError("close failure")

    async def successful_expiry(*_args: object, **_kwargs: object) -> int:
        return 3

    monkeypatch.setattr(run_feed_expiry, "Database", FakeDatabase)
    monkeypatch.setattr(
        run_feed_expiry,
        "async_sessionmaker",
        lambda *_args, **_kwargs: FakeFactory(),
    )
    monkeypatch.setattr(run_feed_expiry, "expire_due", successful_expiry)
    settings = Settings(_env_file=None, FASTAPI_FEED_EXPIRY_ENABLED=True, **BASE)

    assert await run_feed_expiry.execute(settings) == expected
