from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ..services.image_policy import validate_and_thumbnail
from ..services.storage import Storage

router = APIRouter(prefix="/api/media", tags=["media"])
logger = logging.getLogger("media.upload")


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    source_url: str = Form(...),  # noqa: B008
    license_name: str = Form(...),  # noqa: B008
    attribution: str = Form(...),  # noqa: B008
) -> dict[str, object]:
    if not source_url.strip() or not license_name.strip() or not attribution.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": "必须提供图片来源和授权信息", "data": None},
        )
    content = await file.read()
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
    thumbnail_key = storage.put(result.thumbnail, prefix="thumbnails")
    media_id = uuid4().hex
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
            "reviewStatus": "pending",
            "width": result.width,
            "height": result.height,
        },
    }
