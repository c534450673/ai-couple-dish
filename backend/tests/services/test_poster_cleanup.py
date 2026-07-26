import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from scripts import cleanup_poster_orphans as cleanup


def test_daily_poster_cleanup_command_exists() -> None:
    script = Path(__file__).parents[2] / "scripts" / "cleanup_poster_orphans.py"

    assert script.is_file()


def test_cleanup_module_help_runs_from_backend_working_directory() -> None:
    backend_root = Path(__file__).parents[2]

    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "scripts.cleanup_poster_orphans", "--help"],
        cwd=backend_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--apply" in completed.stdout
    assert "--older-than-hours" in completed.stdout
    assert "dry-run" in completed.stdout


def _touch(path: Path, content: bytes, modified: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    timestamp = modified.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_cleanup_dry_run_and_apply_only_remove_audited_candidates(tmp_path: Path) -> None:
    now = datetime(2026, 7, 26, 12, tzinfo=UTC)
    old = now - timedelta(hours=25)
    recent = now - timedelta(hours=2)
    directory = tmp_path / "poster" / "user" / "7" / "2026" / "07" / "25"
    active = directory / f"{uuid4().hex}.png"
    orphan = directory / f"{uuid4().hex}.png"
    recent_orphan = directory / f"{uuid4().hex}.png"
    old_temp = directory / f".{uuid4().hex}.deadbeef.tmp"
    unknown = directory / "legacy-name.png"
    _touch(active, b"active", old)
    _touch(orphan, b"orphan", old)
    _touch(recent_orphan, b"recent", recent)
    _touch(old_temp, b"temp", old)
    _touch(unknown, b"unknown", old)
    symlink = directory / f"{uuid4().hex}.png"
    symlink.symlink_to(orphan)
    active_url = f"/api/uploads/{active.relative_to(tmp_path).as_posix()}"

    dry_run = cleanup.cleanup_poster_orphans(
        upload_root=tmp_path,
        active_urls={active_url},
        file_base_url="/api/uploads",
        file_public_path="/api/uploads",
        older_than_hours=24,
        now=now,
        apply=False,
    )

    assert dry_run.temp_candidates == 1
    assert dry_run.final_candidates == 1
    assert dry_run.deleted == 0
    assert dry_run.refused == 2
    assert all(
        path.exists() or path.is_symlink()
        for path in (active, orphan, recent_orphan, old_temp, unknown, symlink)
    )

    applied = cleanup.cleanup_poster_orphans(
        upload_root=tmp_path,
        active_urls={active_url},
        file_base_url="/api/uploads",
        file_public_path="/api/uploads",
        older_than_hours=24,
        now=now,
        apply=True,
    )

    assert applied.deleted == 2
    assert active.is_file()
    assert recent_orphan.is_file()
    assert unknown.is_file()
    assert symlink.is_symlink()
    assert not orphan.exists()
    assert not old_temp.exists()


def test_cleanup_audit_record_uses_strict_log_allowlist() -> None:
    report = cleanup.CleanupReport(
        scanned=8,
        temp_candidates=1,
        final_candidates=2,
        deleted=0,
        refused=1,
        errors=0,
    )

    record = cleanup.audit_record(
        request_id="cleanup-request",
        report=report,
        apply=False,
        duration_ms=12,
    )

    assert set(record) == {
        "requestId",
        "module",
        "operation",
        "result",
        "durationMs",
        "errorCode",
    }
    assert record["result"] == ("dry_run_scanned_8_temp_1_final_2_deleted_0_refused_1_errors_0")
    assert "/" not in str(record)
