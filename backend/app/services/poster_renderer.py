"""海报栅格渲染、安全图片解码与 POSIX 原子发布。"""

from __future__ import annotations

import json
import os
import re
import secrets
import unicodedata
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

CANVAS_SIZE = (1080, 1440)
MAX_COMPRESSED_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = 16_000_000
ALLOWED_SOURCE_FORMATS = {"JPEG", "PNG", "WEBP"}
DEFAULT_FONT_DIR = Path(__file__).parents[1] / "assets" / "fonts"
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
POSTER_KEY_PATTERN = re.compile(
    r"^poster/user/[1-9][0-9]*/[0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9a-f]{32}\.png$"
)
BIDI_CONTROLS = {
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}


class PosterTemplateConfigError(ValueError):
    pass


class ImageCandidateRejected(ValueError):
    def __init__(self, reason_class: str) -> None:
        super().__init__(reason_class)
        self.reason_class = reason_class


class PosterRenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PosterPalette:
    background: str = "#101525"
    surface: str = "#1A2034"
    primary: str = "#FFB2B7"
    secondary: str = "#54E8D3"
    text: str = "#F7F7FB"


@dataclass(frozen=True)
class PosterRenderPayload:
    poster_type: str
    type_name: str
    title: str
    subtitle: str
    couple_name: str
    invite_code: str
    generated_date: date
    metrics: tuple[tuple[str, str], ...]
    palette: PosterPalette
    image_candidates: tuple[Path, ...] = ()


@dataclass(frozen=True)
class PublishedPoster:
    key: str
    path: Path
    url: str
    output_bytes: int
    rejection_reasons: tuple[str, ...] = ()


def parse_template_config(raw_config: str) -> PosterPalette:
    try:
        document = json.loads(raw_config)
    except (TypeError, json.JSONDecodeError) as error:
        raise PosterTemplateConfigError from error
    if not isinstance(document, dict):
        raise PosterTemplateConfigError
    allowed = {"schemaVersion", "background", "surface", "primary", "secondary", "text"}
    if set(document) - allowed or document.get("schemaVersion", 1) != 1:
        raise PosterTemplateConfigError
    defaults = PosterPalette()
    colors: dict[str, str] = {}
    for field_name in ("background", "surface", "primary", "secondary", "text"):
        value = document.get(field_name, getattr(defaults, field_name))
        if not isinstance(value, str) or COLOR_PATTERN.fullmatch(value) is None:
            raise PosterTemplateConfigError
        colors[field_name] = value.upper()
    return PosterPalette(**colors)


def sanitize_text(value: object, *, max_chars: int) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    safe = "".join(
        character
        for character in normalized
        if character not in BIDI_CONTROLS
        and not (ord(character) < 32 or 127 <= ord(character) <= 159)
    ).strip()
    if len(safe) <= max_chars:
        return safe
    return f"{safe[: max(0, max_chars - 1)]}…"


def _validated_fonts(font_dir: Path) -> tuple[Path, Path]:
    regular_path = font_dir / "NotoSansCJKsc-Regular.otf"
    bold_path = font_dir / "NotoSansCJKsc-Bold.otf"
    try:
        regular = ImageFont.truetype(regular_path, 20)
        bold = ImageFont.truetype(bold_path, 20)
    except OSError as error:
        raise PosterRenderError from error
    if regular.getname() != ("Noto Sans CJK SC", "Regular") or bold.getname() != (
        "Noto Sans CJK SC",
        "Bold",
    ):
        raise PosterRenderError
    return regular_path, bold_path


def validate_font_assets(font_dir: Path = DEFAULT_FONT_DIR) -> None:
    _validated_fonts(font_dir)


def _wrapped_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    *,
    max_width: int,
    max_lines: int,
) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    current = ""
    consumed = 0
    for character in text:
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = character
            if len(lines) == max_lines:
                break
        else:
            current = candidate
        consumed += 1
    if len(lines) < max_lines and current:
        lines.append(current)
    if consumed < len(text) and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    *,
    max_width: int,
    max_lines: int,
    line_gap: int,
) -> int:
    x, y = position
    lines = _wrapped_lines(draw, text, font, max_width=max_width, max_lines=max_lines)
    line_height = int(font.getbbox("国")[3] - font.getbbox("国")[1])
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
    return y


def _validate_dimensions(image: Image.Image) -> None:
    width, height = image.size
    if (
        width <= 0
        or height <= 0
        or width > MAX_IMAGE_DIMENSION
        or height > MAX_IMAGE_DIMENSION
        or width * height > MAX_IMAGE_PIXELS
    ):
        raise ImageCandidateRejected("dimensions")


def decode_source_image(path: Path) -> Image.Image:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_COMPRESSED_BYTES:
            raise ImageCandidateRejected("file")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as probe:
                if probe.format not in ALLOWED_SOURCE_FORMATS:
                    raise ImageCandidateRejected("format")
                _validate_dimensions(probe)
                if (
                    bool(getattr(probe, "is_animated", False))
                    or int(getattr(probe, "n_frames", 1)) != 1
                ):
                    raise ImageCandidateRejected("animated")
                probe.verify()
            with Image.open(path) as source:
                _validate_dimensions(source)
                oriented = ImageOps.exif_transpose(source)
                try:
                    oriented.load()
                    _validate_dimensions(oriented)
                    if "A" in oriented.getbands():
                        result = oriented.convert("RGBA")
                    else:
                        result = oriented.convert("RGB")
                    result.info.clear()
                    return result
                finally:
                    if oriented is not source:
                        oriented.close()
    except ImageCandidateRejected:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageCandidateRejected("bomb") from error
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise ImageCandidateRejected("decode") from error


def _canonical_public_path(path: str) -> str:
    return path.rstrip("/") or "/"


def _url_path_for_service(
    *, file_base_url: str, file_public_path: str, candidate_url: str
) -> str | None:
    if (
        not candidate_url
        or len(candidate_url) > 512
        or "\\" in candidate_url
        or "%" in candidate_url
    ):
        return None
    parsed = urlsplit(candidate_url)
    if parsed.query or parsed.fragment:
        return None
    base = urlsplit(file_base_url)
    if parsed.scheme or parsed.netloc:
        if (
            not base.scheme
            or parsed.scheme.lower() != base.scheme.lower()
            or parsed.netloc.lower() != base.netloc.lower()
        ):
            return None
    elif not candidate_url.startswith("/") or candidate_url.startswith("//"):
        return None
    public_path = _canonical_public_path(file_public_path)
    if not parsed.path.startswith(public_path + "/"):
        return None
    return parsed.path[len(public_path) + 1 :]


def _has_symlink_component(root: Path, target: Path) -> bool:
    current = root
    for part in target.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def resolve_local_image_candidate(
    *,
    upload_root: Path,
    file_base_url: str,
    file_public_path: str,
    candidate_url: str,
    member_ids: set[int],
) -> Path | None:
    relative = _url_path_for_service(
        file_base_url=file_base_url,
        file_public_path=file_public_path,
        candidate_url=candidate_url,
    )
    if relative is None:
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or len(path.parts) < 3:
        return None
    if path.parts[0] != "user" or not path.parts[1].isdigit():
        return None
    if int(path.parts[1]) not in member_ids:
        return None
    root = upload_root.resolve()
    candidate = root.joinpath(*path.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not resolved.is_relative_to(root) or _has_symlink_component(root, candidate):
        return None
    return resolved if resolved.is_file() else None


def _cover_image(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = source.size
    target_width, target_height = size
    scale = max(target_width / width, target_height / height)
    resized = source.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - target_width) // 2)
    top = max(0, (resized.height - target_height) // 2)
    cropped = resized.crop((left, top, left + target_width, top + target_height))
    resized.close()
    return cropped


def _render_canvas(
    payload: PosterRenderPayload, font_dir: Path
) -> tuple[Image.Image, tuple[str, ...]]:
    regular_path, bold_path = _validated_fonts(font_dir)
    palette = payload.palette
    canvas = Image.new("RGB", CANVAS_SIZE, palette.background)
    draw = ImageDraw.Draw(canvas)

    source: Image.Image | None = None
    rejection_reasons: list[str] = []
    for candidate in payload.image_candidates:
        try:
            source = decode_source_image(candidate)
        except ImageCandidateRejected as error:
            rejection_reasons.append(error.reason_class)
            continue
        break
    if source is not None:
        try:
            cover = _cover_image(source, (1080, 520)).convert("RGB")
            canvas.paste(cover, (0, 0))
            cover.close()
            overlay = Image.new("RGBA", (1080, 520), (8, 12, 24, 108))
            canvas.paste(overlay, (0, 0), overlay)
            overlay.close()
        finally:
            source.close()
    else:
        for radius in (110, 190, 270, 350):
            draw.arc(
                (540 - radius, 250 - radius, 540 + radius, 250 + radius),
                205,
                340,
                fill=palette.secondary,
                width=2,
            )
        for x, y in ((875, 90), (930, 220), (120, 330), (760, 400), (360, 100)):
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=palette.primary)

    brand_font = ImageFont.truetype(regular_path, 28)
    title_font = ImageFont.truetype(bold_path, 64)
    subtitle_font = ImageFont.truetype(regular_path, 34)
    metric_value_font = ImageFont.truetype(bold_path, 48)
    metric_label_font = ImageFont.truetype(regular_path, 25)
    footer_font = ImageFont.truetype(regular_path, 25)
    footer_small_font = ImageFont.truetype(regular_path, 20)

    draw.text((72, 48), "Couple Cosmos", font=brand_font, fill=palette.text)
    type_text = sanitize_text(payload.type_name, max_chars=12)
    type_width = draw.textlength(type_text, font=brand_font)
    draw.text((1008 - type_width, 48), type_text, font=brand_font, fill=palette.secondary)
    title = sanitize_text(payload.title, max_chars=40) or payload.type_name
    subtitle = sanitize_text(payload.subtitle, max_chars=80)
    next_y = _draw_wrapped(
        draw,
        (72, 150),
        title,
        title_font,
        palette.text,
        max_width=936,
        max_lines=2,
        line_gap=12,
    )
    _draw_wrapped(
        draw,
        (72, min(360, next_y + 22)),
        subtitle,
        subtitle_font,
        palette.text,
        max_width=936,
        max_lines=2,
        line_gap=10,
    )

    draw.rounded_rectangle((48, 500, 1032, 1120), radius=32, fill=palette.surface)
    metrics = payload.metrics[:3]
    for index in range(3):
        top = 550 + index * 175
        if index:
            draw.line((90, top - 34, 990, top - 34), fill="#343B52", width=2)
        label, value = metrics[index] if index < len(metrics) else ("记录", "0")
        draw.text(
            (90, top),
            sanitize_text(label, max_chars=20),
            font=metric_label_font,
            fill=palette.secondary,
        )
        _draw_wrapped(
            draw,
            (90, top + 42),
            sanitize_text(value, max_chars=40),
            metric_value_font,
            palette.text,
            max_width=850,
            max_lines=1,
            line_gap=0,
        )

    couple_name = sanitize_text(payload.couple_name, max_chars=40) or "我们的双人宇宙"
    invite_code = sanitize_text(payload.invite_code, max_chars=8)
    couple_line = _wrapped_lines(
        draw,
        couple_name,
        footer_font,
        max_width=936,
        max_lines=1,
    )[0]
    draw.text((72, 1185), couple_line, font=footer_font, fill=palette.text)
    draw.text((72, 1240), f"邀请码 {invite_code}", font=footer_font, fill=palette.primary)
    generated = payload.generated_date.isoformat()
    generated_width = draw.textlength(generated, font=footer_font)
    draw.text((1008 - generated_width, 1240), generated, font=footer_font, fill=palette.text)
    draw.line((72, 1320, 1008, 1320), fill="#343B52", width=2)
    draw.text(
        (72, 1340),
        "珍藏属于两个人的每一段旅程",
        font=footer_small_font,
        fill=palette.secondary,
    )
    return canvas, tuple(rejection_reasons)


def _open_managed_directory(root: Path, parts: tuple[str, ...]) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current_fd = os.open(root, flags)
    try:
        for part in parts:
            try:
                os.mkdir(part, mode=0o755, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def render_and_publish(
    *,
    upload_root: Path,
    file_base_url: str,
    user_id: int,
    payload: PosterRenderPayload,
    font_dir: Path = DEFAULT_FONT_DIR,
) -> PublishedPoster:
    if user_id <= 0:
        raise PosterRenderError
    upload_root.mkdir(parents=True, exist_ok=True)
    root = upload_root.resolve(strict=True)
    day_parts = tuple(payload.generated_date.strftime("%Y/%m/%d").split("/"))
    parent_parts = ("poster", "user", str(user_id), *day_parts)
    parent = root.joinpath(*parent_parts)
    parent_fd: int | None = None
    temp_name: str | None = None
    linked_final_name: str | None = None
    published = False
    canvas: Image.Image | None = None
    rejection_reasons: tuple[str, ...] = ()
    try:
        parent_fd = _open_managed_directory(root, parent_parts)
        temp_name = f".render.{secrets.token_hex(16)}.tmp"
        descriptor = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        try:
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                canvas, rejection_reasons = _render_canvas(payload, font_dir)
                canvas.save(output, format="PNG", compress_level=6)
                output.flush()
                os.fsync(output.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        verification_fd = os.open(temp_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        with os.fdopen(verification_fd, "rb") as verification_file:
            with Image.open(verification_file) as verification:
                verification.load()
                if (
                    verification.format != "PNG"
                    or verification.size != CANVAS_SIZE
                    or verification.mode != "RGB"
                ):
                    raise PosterRenderError
        for _attempt in range(4):
            candidate_name = f"{uuid4().hex}.png"
            try:
                os.link(
                    temp_name,
                    candidate_name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                continue
            linked_final_name = candidate_name
            break
        if linked_final_name is None:
            raise PosterRenderError
        os.unlink(temp_name, dir_fd=parent_fd)
        temp_name = None
        try:
            os.fsync(parent_fd)
        except OSError:
            pass
        output_bytes = os.stat(linked_final_name, dir_fd=parent_fd, follow_symlinks=False).st_size
        published = True
        final_path = parent / linked_final_name
        key = final_path.relative_to(root).as_posix()
        return PublishedPoster(
            key=key,
            path=final_path,
            url=f"{file_base_url.rstrip('/')}/{key}",
            output_bytes=output_bytes,
            rejection_reasons=rejection_reasons,
        )
    except PosterRenderError:
        raise
    except Exception as error:
        raise PosterRenderError from error
    finally:
        if canvas is not None:
            canvas.close()
        if temp_name is not None and parent_fd is not None:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except OSError:
                pass
        if linked_final_name is not None and not published and parent_fd is not None:
            try:
                os.unlink(linked_final_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except OSError:
                pass
        if parent_fd is not None:
            os.close(parent_fd)


def _poster_key_from_url(
    *, file_base_url: str, file_public_path: str, poster_url: str
) -> str | None:
    relative = _url_path_for_service(
        file_base_url=file_base_url,
        file_public_path=file_public_path,
        candidate_url=poster_url,
    )
    if relative is None or POSTER_KEY_PATTERN.fullmatch(relative) is None:
        return None
    return relative


def unlink_published_poster(
    *, upload_root: Path, file_base_url: str, file_public_path: str, poster_url: str
) -> Literal["deleted", "missing", "refused"]:
    key = _poster_key_from_url(
        file_base_url=file_base_url,
        file_public_path=file_public_path,
        poster_url=poster_url,
    )
    if key is None:
        return "refused"
    root = upload_root.resolve()
    target = root.joinpath(*PurePosixPath(key).parts)
    if _has_symlink_component(root, target):
        return "refused"
    try:
        resolved_parent = target.parent.resolve(strict=True)
    except OSError:
        return "missing"
    if not resolved_parent.is_relative_to(root):
        return "refused"
    try:
        target.unlink()
    except FileNotFoundError:
        return "missing"
    return "deleted"
