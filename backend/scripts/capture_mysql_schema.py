from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

LOGGER = logging.getLogger("mysql_schema_capture")
EXCLUDED_TABLES = {"alembic_version"}


class SchemaCaptureError(RuntimeError):
    """A schema capture failure with a message that cannot expose connection details."""


def _table_metadata(connection: Connection) -> dict[str, dict[str, str | None]]:
    rows = connection.execute(
        text(
            """
            SELECT TABLE_NAME, TABLE_COLLATION, CCSA.CHARACTER_SET_NAME
            FROM information_schema.TABLES AS T
            LEFT JOIN information_schema.COLLATION_CHARACTER_SET_APPLICABILITY AS CCSA
              ON CCSA.COLLATION_NAME = T.TABLE_COLLATION
            WHERE T.TABLE_SCHEMA = DATABASE() AND T.TABLE_TYPE = 'BASE TABLE'
            ORDER BY T.TABLE_NAME
            """
        )
    ).mappings()
    return {
        cast(str, row["TABLE_NAME"]): {
            "charset": cast(str | None, row["CHARACTER_SET_NAME"]),
            "collation": cast(str | None, row["TABLE_COLLATION"]),
        }
        for row in rows
    }


def _capture_schema_sync(connection: Connection) -> dict[str, Any]:
    inspector = inspect(connection)
    metadata = _table_metadata(connection)
    tables: dict[str, Any] = {}

    table_names = set(inspector.get_table_names()) - EXCLUDED_TABLES
    for table_name in sorted(table_names):
        columns: dict[str, Any] = {}
        for column in sorted(inspector.get_columns(table_name), key=lambda item: str(item["name"])):
            column_name = str(column["name"])
            default = column.get("default")
            columns[column_name] = {
                "default": None if default is None else str(default),
                "nullable": bool(column["nullable"]),
                "type": str(column["type"]),
            }

        indexes: dict[str, Any] = {}
        primary_key = inspector.get_pk_constraint(table_name)
        primary_columns = [str(name) for name in primary_key.get("constrained_columns") or []]
        if primary_columns:
            indexes["PRIMARY"] = {"columns": primary_columns, "unique": True}
        for index in sorted(inspector.get_indexes(table_name), key=lambda item: str(item["name"])):
            index_name = str(index["name"])
            indexes[index_name] = {
                "columns": [str(name) for name in index.get("column_names") or []],
                "unique": bool(index.get("unique", False)),
            }

        foreign_keys: dict[str, Any] = {}
        for foreign_key in sorted(
            inspector.get_foreign_keys(table_name), key=lambda item: str(item.get("name") or "")
        ):
            foreign_key_name = str(foreign_key.get("name") or "")
            if not foreign_key_name:
                raise SchemaCaptureError(f"Unnamed foreign key found on table {table_name}")
            foreign_keys[foreign_key_name] = {
                "columns": [str(name) for name in foreign_key.get("constrained_columns") or []],
                "referred_columns": [
                    str(name) for name in foreign_key.get("referred_columns") or []
                ],
                "referred_table": str(foreign_key["referred_table"]),
            }

        table_properties = metadata.get(table_name)
        if table_properties is None:
            raise SchemaCaptureError(f"Table metadata unavailable for {table_name}")
        tables[table_name] = {
            "charset": table_properties["charset"],
            "collation": table_properties["collation"],
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
        }

    return {"tables": tables}


async def capture_schema(engine: AsyncEngine) -> dict[str, Any]:
    """Capture deterministic structural metadata from the connected MySQL database."""
    if engine.dialect.name != "mysql":
        raise SchemaCaptureError("Schema capture requires MySQL")
    LOGGER.info("event=mysql_schema_capture_started dialect=mysql")
    try:
        async with engine.connect() as connection:
            snapshot = await connection.run_sync(_capture_schema_sync)
    except SchemaCaptureError:
        raise
    except Exception as exc:
        LOGGER.error(
            "event=mysql_schema_capture_failed category=database errorType=%s",
            type(exc).__name__,
        )
        raise SchemaCaptureError("MySQL schema capture failed") from None

    tables = cast(dict[str, Any], snapshot["tables"])
    LOGGER.info(
        "event=mysql_schema_capture_completed tableCount=%s columnCount=%s indexCount=%s "
        "foreignKeyCount=%s",
        len(tables),
        sum(len(table["columns"]) for table in tables.values()),
        sum(len(table["indexes"]) for table in tables.values()),
        sum(len(table["foreign_keys"]) for table in tables.values()),
    )
    return snapshot


def schema_bytes(snapshot: dict[str, Any]) -> bytes:
    return (json.dumps(snapshot, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        LOGGER.error("event=mysql_schema_write_failed file=%s", path.name)
        raise SchemaCaptureError(f"Schema artifact write failed: {path.name}") from None
    LOGGER.info("event=mysql_schema_write_completed file=%s bytes=%s", path.name, len(content))


async def capture_to_files(
    engine: AsyncEngine,
    output: Path,
    sha256_output: Path,
) -> tuple[int, str]:
    snapshot = await capture_schema(engine)
    payload = schema_bytes(snapshot)
    digest = hashlib.sha256(payload).hexdigest()
    _atomic_write(output, payload)
    _atomic_write(sha256_output, f"{digest}\n".encode())
    table_count = len(cast(dict[str, Any], snapshot["tables"]))
    LOGGER.info(
        "event=mysql_schema_artifacts_completed tableCount=%s snapshotFile=%s hashFile=%s",
        table_count,
        output.name,
        sha256_output.name,
    )
    return table_count, digest


def _database_url() -> str:
    database_url = os.environ.get("SCHEMA_DATABASE_URL")
    if not database_url:
        raise SchemaCaptureError("SCHEMA_DATABASE_URL is required")
    return database_url


async def _main_async(output: Path, sha256_output: Path) -> None:
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    try:
        await capture_to_files(engine, output, sha256_output)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a deterministic MySQL schema snapshot")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha256", dest="sha256_output", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s level=%(levelname)s %(message)s")
    try:
        asyncio.run(_main_async(args.output, args.sha256_output))
    except SchemaCaptureError as exc:
        LOGGER.error("event=mysql_schema_capture_command_failed message=%s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
