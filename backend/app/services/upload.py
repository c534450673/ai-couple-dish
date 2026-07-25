import asyncio
import mimetypes
from datetime import date
from pathlib import Path, PurePosixPath
from time import perf_counter
from typing import Never
from uuid import uuid4

import structlog
from fastapi import Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import User

logger = structlog.get_logger()
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_COUNT = 9
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAGIC_HEADERS = {
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "gif": b"GIF",
    "webp": b"RIFF",
}


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "upload",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _fail(request: Request, operation: str, started: float, code: int, message: str) -> Never:
    await logger.awarning(
        "business_operation_failed",
        **_log_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _require_user(
    request: Request, session: AsyncSession, user_id: int, operation: str, started: float
) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _fail(request, operation, started, 1001, "用户不存在")
    return user


def _safe_original_name(filename: str | None) -> str:
    if not filename:
        return ""
    return filename.replace("\\", "/").rsplit("/", 1)[-1]


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def _validate_header(extension: str, content: bytes) -> bool:
    magic = MAGIC_HEADERS[extension]
    if not content.startswith(magic):
        return False
    return extension != "webp" or len(content) >= 12 and content[8:12] == b"WEBP"


async def _read_validated(
    request: Request,
    file: UploadFile,
    operation: str,
    started: float,
) -> tuple[str, str, bytes]:
    filename = _safe_original_name(file.filename)
    extension = _extension(filename)
    content_type = (file.content_type or "").lower()
    if (
        not filename
        or extension not in ALLOWED_EXTENSIONS
        or content_type not in ALLOWED_MIME_TYPES
        or mimetypes.guess_type(filename)[0] not in ALLOWED_MIME_TYPES
    ):
        await _fail(request, operation, started, 9001, "参数无效")
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) == 0 or len(content) > MAX_FILE_SIZE:
        await _fail(request, operation, started, 9001, "参数无效")
    if not _validate_header(extension, content):
        await _fail(request, operation, started, 9001, "参数无效")
    return filename, extension, content


def _file_result(
    base_url: str, file_key: str, filename: str, extension: str, size: int
) -> dict[str, object]:
    return {
        "url": f"{base_url.rstrip('/')}/{file_key}",
        "filename": Path(file_key).name,
        "originalFilename": filename,
        "size": size,
        "type": extension,
        "fileKey": file_key,
    }


def _resolved_target(base_path: str, parts: tuple[str, ...]) -> tuple[Path, Path]:
    root = Path(base_path).resolve()
    return root, root.joinpath(*parts).resolve()


async def _store(
    request: Request,
    user_id: int,
    file: UploadFile,
    operation: str,
    started: float,
) -> dict[str, object]:
    filename, extension, content = await _read_validated(request, file, operation, started)
    relative = PurePosixPath(
        "user",
        str(user_id),
        date.today().strftime("%Y/%m/%d"),
        f"{uuid4().hex}.{extension}",
    )
    root, target = _resolved_target(request.app.state.settings.file_upload_path, relative.parts)
    if not target.is_relative_to(root):
        await _fail(request, operation, started, 9002, "文件上传失败")
    try:
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, content)
    except OSError:
        await _fail(request, operation, started, 9002, "文件上传失败")
    result = _file_result(
        request.app.state.settings.file_base_url,
        relative.as_posix(),
        filename,
        extension,
        len(content),
    )
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, operation, "success", started)
    )
    return result


async def upload_image(
    request: Request, session: AsyncSession, user_id: int, file: UploadFile
) -> dict[str, object]:
    started = perf_counter()
    await _require_user(request, session, user_id, "upload_image", started)
    return await _store(request, user_id, file, "upload_image", started)


async def upload_images(
    request: Request, session: AsyncSession, user_id: int, files: list[UploadFile]
) -> list[dict[str, object]]:
    started = perf_counter()
    await _require_user(request, session, user_id, "upload_images", started)
    if not files or len(files) > MAX_IMAGE_COUNT:
        await _fail(request, "upload_images", started, 9001, "参数无效")
    results: list[dict[str, object]] = []
    for file in files:
        try:
            results.append(await _store(request, user_id, file, "upload_image", started))
        except BusinessError:
            continue
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "upload_images", "success", started)
    )
    return results


async def delete_file(request: Request, session: AsyncSession, user_id: int, file_key: str) -> bool:
    started = perf_counter()
    await _require_user(request, session, user_id, "delete_file", started)
    normalized = file_key.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or path.parts[:2] != ("user", str(user_id))
    ):
        await _fail(request, "delete_file", started, 3002, "无权操作此文件")
    root, target = _resolved_target(request.app.state.settings.file_upload_path, path.parts)
    if not target.is_relative_to(root):
        await _fail(request, "delete_file", started, 3002, "无权操作此文件")
    deleted = False
    try:
        if await asyncio.to_thread(target.is_file):
            await asyncio.to_thread(target.unlink)
            deleted = True
    except OSError:
        await _fail(request, "delete_file", started, 9002, "文件删除失败")
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(request, "delete_file", "success" if deleted else "missing", started),
    )
    return deleted
