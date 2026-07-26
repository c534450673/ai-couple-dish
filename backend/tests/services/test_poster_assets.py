import hashlib
import tomllib
from pathlib import Path

BACKEND = Path(__file__).parents[2]
FONT_DIR = BACKEND / "app" / "assets" / "fonts"
EXPECTED = {
    "NotoSansCJKsc-Regular.otf": (
        "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b",
        ("Noto Sans CJK SC", "Regular"),
    ),
    "NotoSansCJKsc-Bold.otf": (
        "b5f0d1a190a7f9b43c310a8850630af12553df32c4c050543f9059732d9b4c0a",
        ("Noto Sans CJK SC", "Bold"),
    ),
    "OFL.txt": (
        "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2",
        None,
    ),
}


def test_pillow_is_a_locked_runtime_dependency() -> None:
    document = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))

    assert "pillow>=11,<13" in document["project"]["dependencies"]
    assert 'name = "pillow"' in (BACKEND / "uv.lock").read_text(encoding="utf-8")


def test_vendored_font_assets_have_approved_hashes_and_identity() -> None:
    from PIL import ImageFont

    for filename, (expected_hash, identity) in EXPECTED.items():
        path = FONT_DIR / filename
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
        if identity is not None:
            assert ImageFont.truetype(path, 64).getname() == identity

    license_text = (FONT_DIR / "OFL.txt").read_text(encoding="ascii")
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_text


def test_vendored_regular_font_renders_chinese_pixels() -> None:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (900, 180), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_DIR / "NotoSansCJKsc-Regular.otf", 64)

    draw.text((20, 30), "双人宇宙 情侣菜谱 纪念日", font=font, fill="black")

    assert len(image.getcolors(maxcolors=1_000_000) or []) > 32
