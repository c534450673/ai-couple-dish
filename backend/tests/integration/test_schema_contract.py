import asyncio
import re
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from scripts.capture_mysql_schema import capture_schema, schema_bytes

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


def _reset_schema(connection: Connection) -> None:
    table_names = inspect(connection).get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in table_names:
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    schema_path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = schema_path.read_text()
    mysql_source = re.sub(
        r"CREATE (UNIQUE )?INDEX IF NOT EXISTS",
        r"CREATE \1INDEX",
        source,
    )
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


def _database_url(engine: AsyncEngine) -> str:
    return engine.url.render_as_string(hide_password=False)


async def _run_verifier(engine: AsyncEngine, *arguments: str) -> tuple[int, str]:
    backend = Path(__file__).parents[2]
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(backend / "scripts" / "verify_mysql_schema.py"),
        *arguments,
        cwd=backend,
        env={"SCHEMA_DATABASE_URL": _database_url(engine)},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = (stdout + stderr).decode()
    return process.returncode or 0, output


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as connection:
        names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    return set(names)


@pytest.mark.integration
async def test_schema_verifier_stamps_matching_database(mysql_engine: AsyncEngine) -> None:
    return_code, output = await _run_verifier(mysql_engine, "--stamp")

    assert return_code == 0, output
    async with mysql_engine.connect() as connection:
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "0001_existing_mysql_baseline"


@pytest.mark.integration
async def test_mysql_schema_contains_required_tables_and_lunar_column(
    mysql_engine: AsyncEngine,
) -> None:
    snapshot = await capture_schema(mysql_engine)
    assert REQUIRED_TABLES <= set(snapshot["tables"])
    assert "alembic_version" not in snapshot["tables"]
    anniversary = snapshot["tables"]["t_anniversary"]
    assert "is_lunar_date" in anniversary["columns"]


@pytest.mark.integration
async def test_custom_snapshot_cannot_authorize_stamp_on_drifted_database(
    mysql_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            "CREATE TABLE zz_schema_drift_probe (id BIGINT PRIMARY KEY)"
        )
    replacement_snapshot = tmp_path / "replacement-schema.json"
    replacement_snapshot.write_bytes(schema_bytes(await capture_schema(mysql_engine)))

    return_code, output = await _run_verifier(
        mysql_engine,
        "--snapshot",
        str(replacement_snapshot),
        "--stamp",
    )

    assert return_code == 1, output
    assert "alembic_version" not in await _table_names(mysql_engine)


@pytest.mark.integration
async def test_drifted_database_is_not_stamped(mysql_engine: AsyncEngine) -> None:
    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            "CREATE TABLE zz_schema_drift_probe (id BIGINT PRIMARY KEY)"
        )

    return_code, output = await _run_verifier(mysql_engine, "--stamp")

    assert return_code == 1, output
    assert "alembic_version" not in await _table_names(mysql_engine)
