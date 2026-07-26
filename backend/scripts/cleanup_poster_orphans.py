"""审计并清理 Poster 原子发布遗留文件。"""

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.config import Settings
from app.db.models import UserPoster
from app.db.session import Database
from app.services import poster_renderer


@dataclass
class CleanupReport:
    scanned: int = 0
    temp_candidates: int = 0
    final_candidates: int = 0
    deleted: int = 0
    refused: int = 0
    errors: int = 0


def _active_keys(active_urls: set[str], *, file_base_url: str, file_public_path: str) -> set[str]:
    keys: set[str] = set()
    for url in active_urls:
        key = poster_renderer._poster_key_from_url(  # noqa: SLF001
            file_base_url=file_base_url,
            file_public_path=file_public_path,
            poster_url=url,
        )
        if key is not None:
            keys.add(key)
    return keys


def _old_enough(path: Path, cutoff: datetime) -> bool:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        return False
    return modified < cutoff


def cleanup_poster_orphans(
    *,
    upload_root: Path,
    active_urls: set[str],
    file_base_url: str,
    file_public_path: str,
    older_than_hours: int,
    now: datetime,
    apply: bool,
) -> CleanupReport:
    if older_than_hours <= 0:
        raise ValueError("older_than_hours must be positive")
    report = CleanupReport()
    root = upload_root.resolve()
    poster_root = root / "poster"
    if poster_root.is_symlink():
        report.refused += 1
        return report
    if not poster_root.is_dir():
        return report
    active_keys = _active_keys(
        active_urls,
        file_base_url=file_base_url,
        file_public_path=file_public_path,
    )
    cutoff = now.astimezone(UTC) - timedelta(hours=older_than_hours)

    for directory, directory_names, file_names in os.walk(poster_root, followlinks=False):
        current = Path(directory)
        safe_directories: list[str] = []
        for name in directory_names:
            child = current / name
            if child.is_symlink():
                report.refused += 1
            else:
                safe_directories.append(name)
        directory_names[:] = safe_directories

        for name in file_names:
            path = current / name
            report.scanned += 1
            if path.is_symlink():
                report.refused += 1
                continue
            try:
                key = path.relative_to(root).as_posix()
            except ValueError:
                report.refused += 1
                continue
            candidate = False
            if name.endswith(".tmp"):
                if _old_enough(path, cutoff):
                    report.temp_candidates += 1
                    candidate = True
            elif poster_renderer.POSTER_KEY_PATTERN.fullmatch(key) is not None:
                if key not in active_keys and _old_enough(path, cutoff):
                    report.final_candidates += 1
                    candidate = True
            else:
                report.refused += 1
            if not apply or not candidate:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                report.errors += 1
            else:
                report.deleted += 1
    return report


def audit_record(
    *, request_id: str, report: CleanupReport, apply: bool, duration_ms: int
) -> dict[str, object]:
    mode = "apply" if apply else "dry_run"
    result = (
        f"{mode}_scanned_{report.scanned}_temp_{report.temp_candidates}_"
        f"final_{report.final_candidates}_deleted_{report.deleted}_"
        f"refused_{report.refused}_errors_{report.errors}"
    )
    return {
        "requestId": request_id,
        "module": "poster",
        "operation": f"cleanup.{mode}",
        "result": result,
        "durationMs": duration_ms,
        "errorCode": "NONE" if report.errors == 0 else "FILESYSTEM_ERRORS",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="审计并清理超过阈值的 Poster orphan 文件")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际删除；省略时仅执行 dry-run",
    )
    parser.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="候选文件最小年龄，默认 24 小时",
    )
    return parser


async def _execute(arguments: argparse.Namespace) -> int:
    request_id = str(uuid4())
    started = perf_counter()
    settings = Settings()
    database = Database(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    try:
        async with database.session() as session:
            result = await session.execute(
                select(UserPoster.poster_url).where(UserPoster.is_deleted == 0)
            )
            active_urls = {str(url) for url in result.scalars().all()}
        report = await asyncio.to_thread(
            cleanup_poster_orphans,
            upload_root=Path(settings.file_upload_path),
            active_urls=active_urls,
            file_base_url=settings.file_base_url,
            file_public_path=settings.file_public_path,
            older_than_hours=arguments.older_than_hours,
            now=datetime.now(UTC),
            apply=arguments.apply,
        )
        record = audit_record(
            request_id=request_id,
            report=report,
            apply=arguments.apply,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        print(json.dumps(record, ensure_ascii=True, separators=(",", ":")))
        return 1 if report.errors else 0
    except Exception:
        failure: dict[str, Any] = {
            "requestId": request_id,
            "module": "poster",
            "operation": "cleanup.apply" if arguments.apply else "cleanup.dry_run",
            "result": "failed",
            "durationMs": round((perf_counter() - started) * 1000),
            "errorCode": "CLEANUP_FAILED",
        }
        print(json.dumps(failure, ensure_ascii=True, separators=(",", ":")))
        return 1
    finally:
        await database.close()


def main() -> int:
    arguments = _parser().parse_args()
    if arguments.older_than_hours <= 0:
        _parser().error("--older-than-hours must be positive")
    return asyncio.run(_execute(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
