import hashlib
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import verify_mysql_schema


def test_schema_hash_matches_snapshot() -> None:
    root = Path(__file__).parents[2] / "contracts"
    payload = (root / "mysql-schema.json").read_bytes()
    expected = (root / "mysql-schema.sha256").read_text().strip()
    assert hashlib.sha256(payload).hexdigest() == expected


def test_schema_verifier_supports_direct_script_execution() -> None:
    backend = Path(__file__).parents[2]
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(backend / "scripts" / "verify_mysql_schema.py"), "--help"],
        cwd=backend,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("tampered_artifact", ["snapshot", "hash"])
def test_stamp_rejects_tampered_canonical_artifacts_before_connection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tampered_artifact: str,
) -> None:
    contracts = Path(__file__).parents[2] / "contracts"
    snapshot_path = tmp_path / "mysql-schema.json"
    hash_path = tmp_path / "mysql-schema.sha256"
    snapshot_payload = (contracts / "mysql-schema.json").read_bytes()
    expected_hash = (contracts / "mysql-schema.sha256").read_text()
    snapshot_path.write_bytes(
        snapshot_payload + b" " if tampered_artifact == "snapshot" else snapshot_payload
    )
    hash_path.write_text("0" * 64 if tampered_artifact == "hash" else expected_hash)
    monkeypatch.setattr(verify_mysql_schema, "CANONICAL_SNAPSHOT", snapshot_path, raising=False)
    monkeypatch.setattr(verify_mysql_schema, "CANONICAL_HASH", hash_path, raising=False)

    async def fail_if_connection_starts(*args: object, **kwargs: object) -> None:
        raise AssertionError("database connection must not start")

    monkeypatch.setattr(verify_mysql_schema, "_main_async", fail_if_connection_starts)
    monkeypatch.setattr(
        verify_mysql_schema,
        "_stamp",
        lambda *args, **kwargs: pytest.fail("stamp must not start"),
    )

    with pytest.raises(SystemExit) as exit_info:
        verify_mysql_schema.main(["--stamp"])
    assert exit_info.value.code == 1


def test_existing_baseline_cannot_be_downgraded() -> None:
    migration_path = (
        Path(__file__).parents[2] / "migrations" / "versions" / "0001_existing_mysql_baseline.py"
    )
    migration = runpy.run_path(str(migration_path))

    with pytest.raises(RuntimeError, match="Existing production baseline cannot be downgraded"):
        migration["downgrade"]()
