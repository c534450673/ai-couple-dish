"""媒体对象存储：本地开发卷与可注入 COS 适配。"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger("media.storage")
_STORED_IMAGE_KEY = re.compile(r"(?:images|thumbnails)/[0-9a-f]{32}\.jpg\Z")


class Storage:
    def __init__(self, root: str | Path | None = None) -> None:
        resolved_root: str | Path = (
            root if root is not None else os.getenv("FILE_UPLOAD_PATH", "/tmp/uploads")  # noqa: S108
        )
        self.root = Path(resolved_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cos_bucket = os.getenv("COS_BUCKET")
        self.cos_region = os.getenv("COS_REGION")

    def put(self, content: bytes, *, suffix: str = ".jpg", prefix: str = "images") -> str:
        key = f"{prefix}/{uuid4().hex}{suffix}"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info(
            "media_object_stored key=%s bytes=%d backend=%s",
            key,
            len(content),
            "cos" if self.cos_bucket else "local",
        )
        return key

    def delete(self, key: str) -> None:
        path = self.get_path(key)
        path.unlink(missing_ok=True)
        logger.info("media_object_deleted key=%s", key)

    def url(self, key: str) -> str:
        base = os.getenv("MEDIA_PUBLIC_BASE_URL", "")
        return f"{base.rstrip('/')}/{key}" if base else f"/api/media/files/{key}"

    def get_path(self, key: str) -> Path:
        if not _STORED_IMAGE_KEY.fullmatch(key):
            raise ValueError("无效的媒体文件路径")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise FileNotFoundError(key)
        return path
