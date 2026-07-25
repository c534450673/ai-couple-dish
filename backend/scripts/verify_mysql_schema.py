from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
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
CANONICAL_SNAPSHOT = Path(__file__).parents[1] / "contracts" / "mysql-schema.json"
CANONICAL_HASH = Path(__file__).parents[1] / "contracts" / "mysql-schema.sha256"


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


def _parse_snapshot(payload: bytes, path: Path) -> dict[str, Any]:
    try:
        document: object = json.loads(payload)
    except json.JSONDecodeError:
        LOGGER.error("event=mysql_schema_snapshot_invalid category=json file=%s", path.name)
        raise SchemaVerificationError(f"Schema snapshot is invalid: {path.name}") from None
    if not isinstance(document, dict) or not isinstance(document.get("tables"), dict):
        LOGGER.error("event=mysql_schema_snapshot_invalid category=shape file=%s", path.name)
        raise SchemaVerificationError(f"Schema snapshot is invalid: {path.name}")
    return cast(dict[str, Any], document)


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError:
        LOGGER.error("event=mysql_schema_snapshot_load_failed file=%s", path.name)
        raise SchemaVerificationError(f"Schema snapshot cannot be loaded: {path.name}") from None
    return _parse_snapshot(payload, path)


def _load_audited_snapshot(path: Path) -> dict[str, Any]:
    LOGGER.info(
        "event=mysql_schema_audit_validation_started snapshotFile=%s hashFile=%s",
        CANONICAL_SNAPSHOT.name,
        CANONICAL_HASH.name,
    )
    try:
        requested_path = path.resolve(strict=True)
        canonical_path = CANONICAL_SNAPSHOT.resolve(strict=True)
    except OSError:
        LOGGER.error("event=mysql_schema_audit_validation_failed category=missing_artifact")
        raise SchemaVerificationError("Canonical schema audit artifacts are unavailable") from None
    if requested_path != canonical_path:
        LOGGER.error(
            "event=mysql_schema_audit_validation_failed category=noncanonical_snapshot "
            "snapshotFile=%s",
            path.name,
        )
        raise SchemaVerificationError("Stamp requires the canonical schema snapshot")

    try:
        payload = CANONICAL_SNAPSHOT.read_bytes()
        expected_digest = CANONICAL_HASH.read_text().strip()
    except OSError:
        LOGGER.error("event=mysql_schema_audit_validation_failed category=unreadable_artifact")
        raise SchemaVerificationError("Canonical schema audit artifacts are unavailable") from None
    actual_digest = hashlib.sha256(payload).hexdigest()
    if len(expected_digest) != 64 or not hmac.compare_digest(actual_digest, expected_digest):
        LOGGER.error("event=mysql_schema_audit_validation_failed category=hash_mismatch")
        raise SchemaVerificationError("Canonical schema snapshot hash mismatch")

    snapshot = _parse_snapshot(payload, CANONICAL_SNAPSHOT)
    LOGGER.info(
        "event=mysql_schema_audit_validation_completed status=matched tableCount=%s",
        len(cast(dict[str, Any], snapshot["tables"])),
    )
    return snapshot


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


async def _main_async(expected: dict[str, Any], *, stamp: bool) -> str | None:
    if stamp and os.environ.get("SCHEMA_DATABASE_ISOLATED") != "true":
        LOGGER.error(
            "event=mysql_schema_stamp_rejected reason=isolated_database_confirmation_required"
        )
        raise SchemaVerificationError("SCHEMA_DATABASE_ISOLATED=true is required for stamp")
    database_url = os.environ.get("SCHEMA_DATABASE_URL")
    if not database_url:
        raise SchemaVerificationError("SCHEMA_DATABASE_URL is required")
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Verify MySQL schema against the audited snapshot")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=CANONICAL_SNAPSHOT,
    )
    parser.add_argument("--stamp", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s level=%(levelname)s %(message)s")
    try:
        expected = (
            _load_audited_snapshot(args.snapshot) if args.stamp else _load_snapshot(args.snapshot)
        )
        stamp_database_url = asyncio.run(_main_async(expected, stamp=args.stamp))
        if stamp_database_url is not None:
            _stamp(stamp_database_url)
    except (SchemaCaptureError, SchemaVerificationError) as exc:
        LOGGER.error("event=mysql_schema_verification_failed message=%s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
