import importlib.util
import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image

from app.services import poster_renderer as renderer

FONT_DIR = Path(__file__).parents[2] / "app" / "assets" / "fonts"


def test_poster_renderer_module_exists() -> None:
    assert importlib.util.find_spec("app.services.poster_renderer") is not None


def _payload(poster_type: str = "anniversary", *, candidates=()):
    return renderer.PosterRenderPayload(
        poster_type=poster_type,
        type_name={
            "anniversary": "纪念日",
            "feed": "恋爱动态",
            "map": "足迹地图",
            "annual": "年度总结",
        }[poster_type],
        title="双人宇宙纪念册",
        subtitle="一起记录每一个值得珍藏的日子",
        couple_name="星河与月光",
        invite_code="A1B2C3D4",
        generated_date=date(2026, 7, 26),
        metrics=(("相恋天数", "365 天"), ("纪念日期", "2026-07-26"), ("珍藏时刻", "12 次")),
        palette=renderer.parse_template_config('{"background":"#101525"}'),
        image_candidates=tuple(candidates),
    )


def test_template_config_is_fixed_palette_not_a_layer_dsl() -> None:
    palette = renderer.parse_template_config(
        json.dumps(
            {
                "schemaVersion": 1,
                "background": "#102030",
                "surface": "#203040",
                "primary": "#FFB2B7",
                "secondary": "#54E8D3",
                "text": "#F7F7FB",
            }
        )
    )
    compatible = renderer.parse_template_config('{"background":"#FF6B6B"}')

    assert palette.background == "#102030"
    assert palette.surface == "#203040"
    assert compatible.background == "#FF6B6B"
    assert compatible.surface == "#1A2034"

    for invalid in (
        "not-json",
        "[]",
        '{"schemaVersion":2}',
        '{"background":"red"}',
        '{"font":"/tmp/font.otf"}',
        '{"imageUrl":"https://example.com/a.png"}',
        '{"x":10}',
    ):
        with pytest.raises(renderer.PosterTemplateConfigError):
            renderer.parse_template_config(invalid)


@pytest.mark.parametrize("poster_type", ["anniversary", "feed", "map", "annual"])
def test_renderer_publishes_real_fixed_rgb_png(tmp_path: Path, poster_type: str) -> None:
    published = renderer.render_and_publish(
        upload_root=tmp_path,
        file_base_url="/api/uploads",
        user_id=7,
        payload=_payload(poster_type),
        font_dir=FONT_DIR,
    )

    assert published.path.is_file()
    assert published.url.startswith("/api/uploads/poster/user/7/")
    assert published.path.relative_to(tmp_path).as_posix() == published.key
    assert published.output_bytes == published.path.stat().st_size
    assert not list(tmp_path.rglob("*.tmp"))
    assert not [path for path in tmp_path.rglob(".*") if path.is_file()]

    with Image.open(published.path) as image:
        image.load()
        assert image.format == "PNG"
        assert image.size == (1080, 1440)
        assert image.mode == "RGB"
        assert image.getpixel((10, 10)) == (16, 21, 37)
        assert image.getpixel((80, 600)) == (26, 32, 52)
        assert len(image.getcolors(maxcolors=2_000_000) or []) > 100
        assert "exif" not in image.info
        assert "icc_profile" not in image.info


def test_text_is_nfkc_normalized_and_strips_controls_and_bidi() -> None:
    value = renderer.sanitize_text("ＡＢＣ\x00\n标题\u202e隐藏", max_chars=6)

    assert value == "ABC标题…"


def test_couple_display_name_stays_inside_footer_safe_width(tmp_path: Path) -> None:
    published = renderer.render_and_publish(
        upload_root=tmp_path,
        file_base_url="/api/uploads",
        user_id=7,
        payload=replace(_payload(), couple_name="双" * 40),
        font_dir=FONT_DIR,
    )

    with Image.open(published.path) as image:
        image.load()
        overflow = image.crop((1009, 1180, 1080, 1225))
        assert set(overflow.get_flattened_data()) == {(16, 21, 37)}


def test_local_image_resolution_enforces_member_prefix_url_and_symlink_scope(
    tmp_path: Path,
) -> None:
    member_image = tmp_path / "user" / "7" / "2026" / "07" / "photo.png"
    member_image.parent.mkdir(parents=True)
    Image.new("RGB", (40, 20), "red").save(member_image)

    assert (
        renderer.resolve_local_image_candidate(
            upload_root=tmp_path,
            file_base_url="https://api.example.com/uploads",
            file_public_path="/uploads",
            candidate_url="https://api.example.com/uploads/user/7/2026/07/photo.png",
            member_ids={7, 8},
        )
        == member_image.resolve()
    )
    assert (
        renderer.resolve_local_image_candidate(
            upload_root=tmp_path,
            file_base_url="https://api.example.com/uploads",
            file_public_path="/uploads",
            candidate_url="/uploads/user/7/2026/07/photo.png",
            member_ids={7, 8},
        )
        == member_image.resolve()
    )

    outside = tmp_path.parent / "outside-poster-image.png"
    Image.new("RGB", (10, 10), "blue").save(outside)
    symlink = member_image.with_name("escape.png")
    symlink.symlink_to(outside)
    for invalid in (
        "https://evil.example/uploads/user/7/2026/07/photo.png",
        "/uploads/user/9/2026/07/photo.png",
        "/uploads/user/7/../8/photo.png",
        "/uploads/user/7/%252e%252e/8/photo.png",
        "/uploads/user/7/2026/07/photo.png?token=secret",
        "/uploads/user/7/2026/07/photo.png#fragment",
        r"/uploads/user\7\photo.png",
        str(member_image),
        "/uploads/user/7/2026/07/escape.png",
    ):
        assert (
            renderer.resolve_local_image_candidate(
                upload_root=tmp_path,
                file_base_url="https://api.example.com/uploads",
                file_public_path="/uploads",
                candidate_url=invalid,
                member_ids={7, 8},
            )
            is None
        )


def test_source_decoder_applies_exif_and_rejects_unsafe_formats(tmp_path: Path) -> None:
    oriented = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (20, 40), "green").save(oriented, exif=exif)

    decoded = renderer.decode_source_image(oriented)
    try:
        assert decoded.mode == "RGB"
        assert decoded.size == (40, 20)
        assert "exif" not in decoded.info
    finally:
        decoded.close()

    gif = tmp_path / "source.gif"
    Image.new("RGB", (20, 20), "red").save(gif, format="GIF")
    animated = tmp_path / "animated.webp"
    Image.new("RGB", (20, 20), "red").save(
        animated,
        format="WEBP",
        save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")],
    )
    oversized = tmp_path / "oversized.png"
    Image.new("RGB", (4097, 1), "black").save(oversized)
    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
    too_large = tmp_path / "compressed.png"
    with too_large.open("wb") as handle:
        handle.truncate(10 * 1024 * 1024 + 1)

    for invalid in (gif, animated, oversized, truncated, too_large):
        with pytest.raises(renderer.ImageCandidateRejected):
            renderer.decode_source_image(invalid)


def test_source_decoder_classifies_pixel_limit_and_decompression_bomb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    over_pixel_limit = tmp_path / "over-pixel-limit.png"
    Image.new("1", (4096, 4096)).save(over_pixel_limit)
    with pytest.raises(renderer.ImageCandidateRejected) as dimensions:
        renderer.decode_source_image(over_pixel_limit)
    assert dimensions.value.reason_class == "dimensions"

    warning_bomb = tmp_path / "warning-bomb.png"
    Image.new("RGB", (40, 40), "red").save(warning_bomb)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(renderer.ImageCandidateRejected) as bomb:
        renderer.decode_source_image(warning_bomb)
    assert bomb.value.reason_class == "bomb"


def test_renderer_reports_all_candidate_decode_rejection_reasons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-an-image")
    animated = tmp_path / "animated.webp"
    Image.new("RGB", (20, 20), "red").save(
        animated,
        format="WEBP",
        save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")],
    )
    warning_bomb = tmp_path / "warning-bomb.png"
    Image.new("RGB", (40, 40), "red").save(warning_bomb)
    valid = tmp_path / "valid.png"
    Image.new("RGB", (40, 40), "green").save(valid)
    original_decode = renderer.decode_source_image

    def decode_with_scoped_bomb_limit(path: Path) -> Image.Image:
        if path != warning_bomb:
            return original_decode(path)
        previous_limit = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = 1000
        try:
            return original_decode(path)
        finally:
            Image.MAX_IMAGE_PIXELS = previous_limit

    monkeypatch.setattr(renderer, "decode_source_image", decode_with_scoped_bomb_limit)

    published = renderer.render_and_publish(
        upload_root=tmp_path / "uploads",
        file_base_url="/api/uploads",
        user_id=7,
        payload=_payload(candidates=(bad, animated, warning_bomb, valid)),
        font_dir=FONT_DIR,
    )

    assert published.rejection_reasons == ("decode", "animated", "bomb")


def test_renderer_falls_back_after_bad_candidate_and_strips_source_metadata(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-an-image")
    source = tmp_path / "source.png"
    Image.new("RGB", (320, 200), "#54E8D3").save(source, pnginfo=None)

    published = renderer.render_and_publish(
        upload_root=tmp_path / "uploads",
        file_base_url="/api/uploads",
        user_id=8,
        payload=_payload(candidates=(bad, source)),
        font_dir=FONT_DIR,
    )

    with Image.open(published.path) as image:
        image.load()
        assert image.getpixel((540, 300)) != (16, 21, 37)
        assert image.info == {}


@pytest.mark.parametrize("symlink_component", ["poster", "user_id"])
def test_publish_refuses_symlink_in_managed_directory_chain(
    tmp_path: Path, symlink_component: str
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    if symlink_component == "poster":
        link = upload_root / "poster"
    else:
        link = upload_root / "poster" / "user" / "7"
        link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(renderer.PosterRenderError):
        renderer.render_and_publish(
            upload_root=upload_root,
            file_base_url="/api/uploads",
            user_id=7,
            payload=_payload(),
            font_dir=FONT_DIR,
        )

    assert not list(outside.iterdir())


def test_atomic_publish_collision_preserves_existing_final_and_retries_uuid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_id = UUID("11111111-1111-1111-1111-111111111111")
    second_id = UUID("22222222-2222-2222-2222-222222222222")
    identifiers = iter((first_id, second_id))
    collision = tmp_path / "poster" / "user" / "7" / "2026" / "07" / "26" / f"{first_id.hex}.png"
    sentinel = b"existing-final-must-not-change"
    original_render = renderer._render_canvas

    def render_after_collision(*args, **kwargs):
        canvas = original_render(*args, **kwargs)
        collision.write_bytes(sentinel)
        return canvas

    monkeypatch.setattr(renderer, "uuid4", lambda: next(identifiers))
    monkeypatch.setattr(renderer, "_render_canvas", render_after_collision)

    published = renderer.render_and_publish(
        upload_root=tmp_path,
        file_base_url="/api/uploads",
        user_id=7,
        payload=_payload(),
        font_dir=FONT_DIR,
    )

    assert collision.read_bytes() == sentinel
    assert published.path.name == f"{second_id.hex}.png"


def test_atomic_publish_failure_leaves_no_temp_or_final(tmp_path: Path, monkeypatch) -> None:
    def fail_link(*_args, **_kwargs) -> None:
        raise OSError("sentinel path must not be logged")

    monkeypatch.setattr(renderer.os, "link", fail_link)

    with pytest.raises(renderer.PosterRenderError):
        renderer.render_and_publish(
            upload_root=tmp_path,
            file_base_url="/api/uploads",
            user_id=7,
            payload=_payload(),
            font_dir=FONT_DIR,
        )

    assert not list(tmp_path.rglob("*.png"))
    assert not [path for path in tmp_path.rglob(".*") if path.is_file()]


def test_poster_unlink_only_accepts_owned_service_urls(tmp_path: Path) -> None:
    published = renderer.render_and_publish(
        upload_root=tmp_path,
        file_base_url="https://api.example.com/uploads",
        user_id=7,
        payload=_payload(),
        font_dir=FONT_DIR,
    )

    assert (
        renderer.unlink_published_poster(
            upload_root=tmp_path,
            file_base_url="https://api.example.com/uploads",
            file_public_path="/uploads",
            poster_url=published.url,
        )
        == "deleted"
    )
    assert (
        renderer.unlink_published_poster(
            upload_root=tmp_path,
            file_base_url="https://api.example.com/uploads",
            file_public_path="/uploads",
            poster_url=published.url,
        )
        == "missing"
    )

    protected = tmp_path / "protected.png"
    protected.write_bytes(b"protected")
    for unsafe in (
        "https://evil.example/uploads/poster/user/7/2026/07/26/abc.png",
        "/uploads/user/7/private.png",
        "/uploads/poster/user/7/../../protected.png",
        "/uploads/poster/user/7/2026/07/26/not-a-uuid.png",
        "/uploads/poster/user/7/2026/07/26/00000000000000000000000000000000.png?x=1",
    ):
        assert (
            renderer.unlink_published_poster(
                upload_root=tmp_path,
                file_base_url="https://api.example.com/uploads",
                file_public_path="/uploads",
                poster_url=unsafe,
            )
            == "refused"
        )
    assert protected.read_bytes() == b"protected"
