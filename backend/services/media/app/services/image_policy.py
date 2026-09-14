from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ImageResult:
    content: bytes
    mime: str
    width: int
    height: int
    thumbnail: bytes
    thumbnail_mime: str = "image/jpeg"


def validate_and_thumbnail(
    content: bytes, *, filename: str, max_bytes: int = 10 * 1024 * 1024
) -> ImageResult:
    if len(content) > max_bytes or Path(filename).suffix.lower() not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        raise ValueError("仅支持 JPEG/PNG/WebP 且文件不得超过10MB")
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            if image.width > 10_000 or image.height > 10_000:
                raise ValueError("图片尺寸过大")
            rgb = image.convert("RGB")
            output = BytesIO()
            rgb.save(output, format="JPEG", quality=90, optimize=True)
            thumb = rgb.copy()
            thumb.thumbnail((800, 800))
            thumb_output = BytesIO()
            thumb.save(thumb_output, format="JPEG", quality=85, optimize=True)
            return ImageResult(
                output.getvalue(), "image/jpeg", image.width, image.height, thumb_output.getvalue()
            )
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("无效图片") from error
