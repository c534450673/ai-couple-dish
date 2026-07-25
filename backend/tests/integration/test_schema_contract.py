import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from scripts.capture_mysql_schema import capture_schema

REQUIRED_TABLES = {
    "t_user",
    "t_couple",
    "t_couple_menu",
    "t_recipe",
    "t_food_note",
    "t_feed",
    "t_anniversary",
    "t_wish",
    "t_notification",
    "t_note_like",
}


@pytest.fixture
async def mysql_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(os.environ["SCHEMA_DATABASE_URL"])
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_schema_verifier_stamps_matching_database() -> None:
    backend = Path(__file__).parents[2]
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(backend / "scripts" / "verify_mysql_schema.py"), "--stamp"],
        cwd=backend,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
async def test_mysql_schema_contains_required_tables_and_lunar_column(
    mysql_engine: AsyncEngine,
) -> None:
    snapshot = await capture_schema(mysql_engine)
    assert REQUIRED_TABLES <= set(snapshot["tables"])
    assert "alembic_version" not in snapshot["tables"]
    anniversary = snapshot["tables"]["t_anniversary"]
    assert "is_lunar_date" in anniversary["columns"]
