import hashlib
import subprocess
import sys
from pathlib import Path


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
