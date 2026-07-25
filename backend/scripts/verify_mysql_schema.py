from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from scripts.capture_mysql_schema import SchemaCaptureError, capture_schema
else:
    if __package__:
        from scripts.capture_mysql_schema import SchemaCaptureError, capture_schema
    else:
        from capture_mysql_schema import SchemaCaptureError, capture_schema

LOGGER = logging.getLogger("mysql_schema_verify")
BASELINE_REVISION = "0001_existing_mysql_baseline"


class SchemaVerificationError(RuntimeError):
    """A verifier failure with a message safe for logs and terminals."""


def _changed_names(expected: dict[str, Any], actual: dict[str, Any]) -> tuple[list[str], list[str]]:
    expected_names = set(expected)
    actual_names = set(actual)
    added = actual_names - expected_names
    missing = expected_names - actual_names
    for name in expected_names & actual_names:
        if expected[name] != actual[name]:
            added.add(name)
            missing.add(name)
    return sorted(added), sorted(missing)


def compare_schemas(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, list[str]]:
    expected_tables = cast(dict[str, Any], expected.get("tables", {}))
    actual_tables = cast(dict[str, Any], actual.get("tables", {}))
    added_tables, missing_tables = _changed_names(
        {
            name: {key: value for key, value in table.items() if key not in {"columns", "indexes"}}
            for name, table in expected_tables.items()
        },
        {
            name: {key: value for key, value in table.items() if key not in {"columns", "indexes"}}
            for name, table in actual_tables.items()
        },
    )
    added_table_names = set(actual_tables) - set(expected_tables)
    missing_table_names = set(expected_tables) - set(actual_tables)
    added_tables = sorted(set(added_tables) | added_table_names)
    missing_tables = sorted(set(missing_tables) | missing_table_names)

    added_columns: list[str] = []
    missing_columns: list[str] = []
    added_indexes: list[str] = []
    missing_indexes: list[str] = []
    for table_name in sorted(set(expected_tables) & set(actual_tables)):
        expected_table = cast(dict[str, Any], expected_tables[table_name])
        actual_table = cast(dict[str, Any], actual_tables[table_name])
        column_added, column_missing = _changed_names(
            cast(dict[str, Any], expected_table.get("columns", {})),
            cast(dict[str, Any], actual_table.get("columns", {})),
        )
        index_added, index_missing = _changed_names(
            cast(dict[str, Any], expected_table.get("indexes", {})),
            cast(dict[str, Any], actual_table.get("indexes", {})),
        )
        added_columns.extend(f"{table_name}.{name}" for name in column_added)
        missing_columns.extend(f"{table_name}.{name}" for name in column_missing)
        added_indexes.extend(f"{table_name}.{name}" for name in index_added)
        missing_indexes.extend(f"{table_name}.{name}" for name in index_missing)

    return {
        "addedTables": added_tables,
        "missingTables": missing_tables,
        "addedColumns": sorted(added_columns),
        "missingColumns": sorted(missing_columns),
        "addedIndexes": sorted(added_indexes),
        "missingIndexes": sorted(missing_indexes),
    }


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        document: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        LOGGER.error("event=mysql_schema_snapshot_load_failed file=%s", path.name)
        raise SchemaVerificationError(f"Schema snapshot cannot be loaded: {path.name}") from None
    if not isinstance(document, dict) or not isinstance(document.get("tables"), dict):
        LOGGER.error("event=mysql_schema_snapshot_invalid file=%s", path.name)
        raise SchemaVerificationError(f"Schema snapshot is invalid: {path.name}")
    return cast(dict[str, Any], document)


async def verify_schema(
    engine: AsyncEngine,
    expected: dict[str, Any],
) -> dict[str, list[str]]:
    LOGGER.info("event=mysql_schema_verification_started")
    actual = await capture_schema(engine)
    return compare_schemas(expected, actual)


def _log_drift(diff: dict[str, list[str]]) -> None:
    LOGGER.error(
        "event=mysql_schema_drift_detected addedTableCount=%s missingTableCount=%s "
        "addedColumnCount=%s missingColumnCount=%s addedIndexCount=%s missingIndexCount=%s "
        "addedTables=%s missingTables=%s addedColumns=%s missingColumns=%s addedIndexes=%s "
        "missingIndexes=%s",
        len(diff["addedTables"]),
        len(diff["missingTables"]),
        len(diff["addedColumns"]),
        len(diff["missingColumns"]),
        len(diff["addedIndexes"]),
        len(diff["missingIndexes"]),
        diff["addedTables"],
        diff["missingTables"],
        diff["addedColumns"],
        diff["missingColumns"],
        diff["addedIndexes"],
        diff["missingIndexes"],
    )


def _stamp(database_url: str) -> None:
    alembic_path = Path(__file__).parents[1] / "alembic.ini"
    alembic_config = Config(str(alembic_path))
    alembic_config.attributes["schema_database_url"] = database_url
    LOGGER.info("event=mysql_schema_stamp_started revision=%s", BASELINE_REVISION)
    try:
        command.stamp(alembic_config, BASELINE_REVISION)
    except Exception as exc:
        LOGGER.error(
            "event=mysql_schema_stamp_failed revision=%s errorType=%s",
            BASELINE_REVISION,
            type(exc).__name__,
        )
        raise SchemaVerificationError("Alembic baseline stamp failed") from None
    LOGGER.info("event=mysql_schema_stamp_completed revision=%s", BASELINE_REVISION)


async def _main_async(snapshot_path: Path, *, stamp: bool) -> str | None:
    database_url = os.environ.get("SCHEMA_DATABASE_URL")
    if not database_url:
        raise SchemaVerificationError("SCHEMA_DATABASE_URL is required")
    expected = _load_snapshot(snapshot_path)
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        diff = await verify_schema(engine, expected)
    finally:
        await engine.dispose()

    if any(diff.values()):
        _log_drift(diff)
        raise SchemaVerificationError("MySQL schema differs from the audited snapshot")
    LOGGER.info(
        "event=mysql_schema_verification_completed status=matched tableCount=%s",
        len(cast(dict[str, Any], expected["tables"])),
    )
    return database_url if stamp else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify MySQL schema against the audited snapshot")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path(__file__).parents[1] / "contracts" / "mysql-schema.json",
    )
    parser.add_argument("--stamp", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s level=%(levelname)s %(message)s")
    try:
        stamp_database_url = asyncio.run(_main_async(args.snapshot, stamp=args.stamp))
        if stamp_database_url is not None:
            _stamp(stamp_database_url)
    except (SchemaCaptureError, SchemaVerificationError) as exc:
        LOGGER.error("event=mysql_schema_verification_failed message=%s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
