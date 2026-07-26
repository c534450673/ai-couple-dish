import asyncio
import os
import re
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError
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
            # The canonical snapshot is the pre-migration baseline. Business integration
            # fixtures keep the generated column and unique index from schema-test.sql.
            await connection.exec_driver_sql(
                "ALTER TABLE t_daily_greeting "
                "DROP INDEX uk_daily_greeting_active_user_type_date, "
                "DROP COLUMN active_user_id"
            )
        yield engine
    finally:
        await engine.dispose()


def _database_url(engine: AsyncEngine) -> str:
    return engine.url.render_as_string(hide_password=False)


async def _run_verifier(
    engine: AsyncEngine,
    *arguments: str,
    isolated: str | None = None,
) -> tuple[int, str]:
    backend = Path(__file__).parents[2]
    environment = {"SCHEMA_DATABASE_URL": _database_url(engine)}
    if isolated is not None:
        environment["SCHEMA_DATABASE_ISOLATED"] = isolated
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(backend / "scripts" / "verify_mysql_schema.py"),
        *arguments,
        cwd=backend,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = (stdout + stderr).decode()
    return process.returncode or 0, output


async def _run_migrations(engine: AsyncEngine) -> tuple[int, str]:
    backend = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment["SCHEMA_DATABASE_URL"] = _database_url(engine)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(backend / "alembic.ini"),
        "upgrade",
        "head",
        cwd=backend,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, (stdout + stderr).decode()


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as connection:
        names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    return set(names)


@pytest.mark.integration
async def test_schema_verifier_stamps_matching_database(mysql_engine: AsyncEngine) -> None:
    return_code, output = await _run_verifier(mysql_engine, "--stamp", isolated="true")

    assert return_code == 0, output
    async with mysql_engine.connect() as connection:
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "0001_existing_mysql_baseline"


@pytest.mark.integration
async def test_schema_verifier_rejects_stamp_without_isolation_confirmation(
    mysql_engine: AsyncEngine,
) -> None:
    return_code, output = await _run_verifier(mysql_engine, "--stamp")

    assert return_code == 1, output
    assert "SCHEMA_DATABASE_ISOLATED=true is required for stamp" in output
    assert "alembic_version" not in await _table_names(mysql_engine)


@pytest.mark.integration
async def test_schema_verifier_rejects_stamp_with_false_isolation_confirmation(
    mysql_engine: AsyncEngine,
) -> None:
    return_code, output = await _run_verifier(mysql_engine, "--stamp", isolated="false")

    assert return_code == 1, output
    assert "SCHEMA_DATABASE_ISOLATED=true is required for stamp" in output
    assert "alembic_version" not in await _table_names(mysql_engine)


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
        isolated="true",
    )

    assert return_code == 1, output
    assert "alembic_version" not in await _table_names(mysql_engine)


@pytest.mark.integration
async def test_drifted_database_is_not_stamped(mysql_engine: AsyncEngine) -> None:
    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            "CREATE TABLE zz_schema_drift_probe (id BIGINT PRIMARY KEY)"
        )

    return_code, output = await _run_verifier(mysql_engine, "--stamp", isolated="true")

    assert return_code == 1, output
    assert "alembic_version" not in await _table_names(mysql_engine)


@pytest.mark.integration
async def test_daily_greeting_unique_migration_rejects_dirty_data_then_enforces_active_rows(
    mysql_engine: AsyncEngine,
) -> None:
    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            """
            INSERT INTO t_daily_greeting (
                couple_id, user_id, greeting_type, greeting_date, is_deleted
            ) VALUES
                (11, 101, 1, '2026-07-26', 0),
                (11, 101, 1, '2026-07-26', 0)
            """
        )

    return_code, output = await _run_migrations(mysql_engine)
    assert return_code == 1, output
    assert "Daily greeting unique migration preflight failed" in output

    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            "DELETE FROM t_daily_greeting WHERE id = ("
            "SELECT id FROM (SELECT MAX(id) AS id FROM t_daily_greeting) AS duplicate_row)"
        )

    return_code, output = await _run_migrations(mysql_engine)
    assert return_code == 0, output

    async with mysql_engine.begin() as connection:
        active_user_expression = await connection.scalar(
            text(
                "SELECT generation_expression FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 't_daily_greeting' "
                "AND column_name = 'active_user_id'"
            )
        )
        unique_index = await connection.scalar(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 't_daily_greeting' "
                "AND index_name = 'uk_daily_greeting_active_user_type_date' "
                "AND non_unique = 0"
            )
        )
        await connection.exec_driver_sql(
            """
            INSERT INTO t_daily_greeting (
                couple_id, user_id, greeting_type, greeting_date, is_deleted
            ) VALUES
                (11, 101, 1, '2026-07-26', 1),
                (11, 101, 1, '2026-07-26', 1)
            """
        )
    assert active_user_expression is not None
    assert int(unique_index or 0) == 3

    with pytest.raises(IntegrityError):
        async with mysql_engine.begin() as connection:
            await connection.exec_driver_sql(
                """
                INSERT INTO t_daily_greeting (
                    couple_id, user_id, greeting_type, greeting_date, is_deleted
                ) VALUES (11, 101, 1, '2026-07-26', 0)
                """
            )


@pytest.mark.integration
async def test_daily_greeting_unique_migration_resumes_after_column_only_partial_ddl(
    mysql_engine: AsyncEngine,
) -> None:
    async with mysql_engine.begin() as connection:
        await connection.exec_driver_sql(
            "ALTER TABLE t_daily_greeting ADD COLUMN active_user_id BIGINT "
            "GENERATED ALWAYS AS (CASE WHEN is_deleted = 0 THEN user_id ELSE NULL END) STORED"
        )

    return_code, output = await _run_migrations(mysql_engine)
    assert return_code == 0, output

    async with mysql_engine.connect() as connection:
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        unique_index_columns = await connection.scalar(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 't_daily_greeting' "
                "AND index_name = 'uk_daily_greeting_active_user_type_date' "
                "AND non_unique = 0"
            )
        )

    assert revision == "0002_daily_greeting_unique"
    assert int(unique_index_columns or 0) == 3
