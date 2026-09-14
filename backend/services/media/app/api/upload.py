from __future__ import annotations

import logging
import mimetypes
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import CatalogDishImage
from packages.platform.admin_auth import require_admin

from ..services.image_policy import validate_and_thumbnail
from ..services.storage import Storage

router = APIRouter(prefix="/api/media", tags=["media"])
logger = logging.getLogger("media.upload")
request_logger = structlog.get_logger()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.api_route("/files/{category}/{filename}", methods=["GET", "HEAD"])
async def get_image(category: str, filename: str, request: Request) -> FileResponse:
    started = perf_counter()
    key = f"{category}/{filename}"
    request_id = request.headers.get("X-Request-ID", "unknown")
    storage: Storage = request.app.state.storage
    try:
        path = storage.get_path(key)
    except (ValueError, FileNotFoundError) as error:
        await request_logger.awarning(
            "media_file_not_found",
            requestId=request_id,
            module="media",
            operation="get_image",
            result="not_found",
            durationMs=round((perf_counter() - started) * 1000),
            errorCode=type(error).__name__,
        )
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "媒体文件不存在", "data": None},
        ) from error
    # 有数据库会话时，读取侧必须再次核验授权；这样即便对象存储 URL 被猜到，
    # pending/rejected 或已过期的素材也不会被公开。未注入数据库的离线测试模式
    # 仅验证对象路径安全，保持开发环境可直接预览已写入的文件。
    provider = getattr(request.app.state, "session_provider", None)
    if provider is not None:
        try:
            async with provider() as session:
                metadata = await session.scalar(
                    select(CatalogDishImage).where(
                        or_(
                            CatalogDishImage.object_key == key,
                            CatalogDishImage.thumbnail_key == key,
                        )
                    )
                )
        except SQLAlchemyError as error:
            await request_logger.aexception(
                "media_authorization_lookup_failed",
                requestId=request_id,
                module="media",
                operation="get_image.authorization",
                result="error",
                errorCode=type(error).__name__,
                objectKey=key,
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "媒体服务暂不可用", "data": None},
            ) from error
        except Exception as error:
            await request_logger.aexception(
                "media_authorization_lookup_failed",
                requestId=request_id,
                module="media",
                operation="get_image.authorization",
                result="error",
                errorCode=type(error).__name__,
                objectKey=key,
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 503, "message": "媒体服务暂不可用", "data": None},
            ) from error
        if metadata is None or not _metadata_is_authorized(metadata):
            await request_logger.awarning(
                "media_authorization_rejected",
                requestId=request_id,
                module="media",
                operation="get_image.authorization",
                result="rejected",
                errorCode="MEDIA_NOT_AUTHORIZED",
                objectKey=key,
                reviewStatus=getattr(metadata, "review_status", None),
            )
            raise HTTPException(
                status_code=404,
                detail={"code": 404, "message": "媒体授权未通过", "data": None},
            )
    await request_logger.ainfo(
        "media_file_served",
        requestId=request_id,
        module="media",
        operation="get_image",
        result="success",
        durationMs=round((perf_counter() - started) * 1000),
        errorCode="NONE",
        category=category,
        method=request.method,
        contentLength=path.stat().st_size,
    )
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Length": str(path.stat().st_size),
        },
    )


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    source_url: str = Form(...),  # noqa: B008
    license_name: str = Form(...),  # noqa: B008
    attribution: str = Form(...),  # noqa: B008
    dish_slug: str = Form(default="unassigned"),  # noqa: B008
    license_expires_at: str | None = Form(default=None),  # noqa: B008
) -> dict[str, object]:
    require_admin(request)
    source_url = source_url.strip()
    license_name = license_name.strip()
    attribution = attribution.strip()
    dish_slug = dish_slug.strip()
    if not source_url or not license_name or not attribution or not dish_slug:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": "必须提供图片来源和授权信息", "data": None},
        )
    if len(source_url) > 1024 or len(license_name) > 128 or len(attribution) > 512:
        raise HTTPException(
            status_code=422,
            detail={"code": 422, "message": "图片授权信息长度超出限制", "data": None},
        )
    if len(dish_slug) > 128:
        raise HTTPException(
            status_code=422,
            detail={"code": 422, "message": "菜品标识长度超出限制", "data": None},
        )
    expiry: datetime | None = None
    if license_expires_at:
        try:
            expiry = datetime.fromisoformat(license_expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                raise ValueError("授权到期时间必须包含时区")
            expiry = expiry.astimezone(UTC).replace(tzinfo=None)
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": 422, "message": "授权到期时间格式无效", "data": None},
            ) from error
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            await file.close()
            logger.warning("media_upload_rejected reason=size_limit bytes=%d", total)
            raise HTTPException(
                status_code=413,
                detail={"code": 413, "message": "图片不得超过10MB", "data": None},
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    await file.close()
    try:
        result = validate_and_thumbnail(content, filename=file.filename or "upload.jpg")
    except ValueError as error:
        logger.warning("media_upload_rejected reason=%s bytes=%d", str(error), len(content))
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": str(error), "data": None}
        ) from error
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        storage = Storage()
    key = storage.put(result.content)
    thumbnail_key: str | None = None
    try:
        thumbnail_key = storage.put(result.thumbnail, prefix="thumbnails")
    except Exception:
        _cleanup_objects(storage, key, thumbnail_key)
        logger.exception("media_upload_storage_failed key=%s", key)
        raise
    provider = getattr(request.app.state, "session_provider", None)
    if provider is None:
        _cleanup_objects(storage, key, thumbnail_key)
        await request_logger.aerror(
            "media_upload_persistence_unavailable",
            requestId=request.headers.get("X-Request-ID", "unknown"),
            module="media",
            operation="upload_image",
            result="error",
            errorCode="DATABASE_NOT_READY",
        )
        raise HTTPException(
            status_code=503,
            detail={"code": 503, "message": "媒体服务暂不可用", "data": None},
        )

    media_id = uuid4().hex
    try:
        async with provider() as session:
            session.add(
                CatalogDishImage(
                    dish_slug=dish_slug,
                    object_key=key,
                    source_url=source_url,
                    license_name=license_name,
                    attribution=attribution,
                    license_expires_at=expiry,
                    review_status="pending",
                    width=result.width,
                    height=result.height,
                    thumbnail_key=thumbnail_key,
                )
            )
            await session.commit()
    except SQLAlchemyError as error:
        _cleanup_objects(storage, key, thumbnail_key)
        await request_logger.aexception(
            "media_upload_persistence_failed",
            requestId=request.headers.get("X-Request-ID", "unknown"),
            module="media",
            operation="upload_image",
            result="error",
            errorCode=type(error).__name__,
            objectKey=key,
        )
        raise HTTPException(
            status_code=503,
            detail={"code": 503, "message": "媒体元数据保存失败", "data": None},
        ) from error
    except Exception as error:
        _cleanup_objects(storage, key, thumbnail_key)
        await request_logger.aexception(
            "media_upload_persistence_failed",
            requestId=request.headers.get("X-Request-ID", "unknown"),
            module="media",
            operation="upload_image",
            result="error",
            errorCode=type(error).__name__,
            objectKey=key,
        )
        raise HTTPException(
            status_code=503,
            detail={"code": 503, "message": "媒体元数据保存失败", "data": None},
        ) from error
    logger.info(
        "media_upload_completed mediaId=%s key=%s width=%d height=%d",
        media_id,
        key,
        result.width,
        result.height,
    )
    return {
        "code": 200,
        "message": "操作成功",
        "data": {
            "id": media_id,
            "key": key,
            "url": storage.url(key),
            "thumbnailUrl": storage.url(thumbnail_key),
            "sourceUrl": source_url,
            "licenseName": license_name,
            "attribution": attribution,
            "dishSlug": dish_slug,
            "reviewStatus": "pending",
            "licenseExpiresAt": license_expires_at,
            "width": result.width,
            "height": result.height,
        },
    }


def _cleanup_objects(storage: Storage, key: str, thumbnail_key: str | None) -> None:
    """删除事务失败后已写入的对象，清理失败只记录不覆盖原始错误。"""

    for object_key in (thumbnail_key, key):
        if not object_key:
            continue
        try:
            storage.delete(object_key)
        except Exception:
            logger.exception("media_upload_cleanup_failed key=%s", object_key)


def _metadata_is_authorized(metadata: CatalogDishImage) -> bool:
    """判断媒体元数据是否满足公开读取条件。"""

    if metadata.review_status != "approved":
        return False
    expiry = metadata.license_expires_at
    return expiry is None or expiry > datetime.now(UTC).replace(tzinfo=None)
