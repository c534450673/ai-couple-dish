import json
from pathlib import Path

from PIL import Image


def test_curated_candidates_have_traceable_image_rights_and_valid_assets() -> None:
    catalog_dir = Path(__file__).parents[2] / "data" / "catalog"
    rows = json.loads((catalog_dir / "curated-candidates.json").read_text(encoding="utf-8"))
    assert len(rows) >= 3
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["slug"] for row in rows}) == len(rows)

    for row in rows:
        assert row["status"] == "draft"
        assert row["name"] and row["cuisine"]
        assert row["sources"]
        for source in row["sources"]:
            assert all(source.get(key) for key in ("url", "license", "licenseUrl", "attribution"))
            assert source["reviewStatus"] == "pending"
        asset = (catalog_dir / row["imageAsset"]).resolve()
        assert asset.is_relative_to((catalog_dir / "assets").resolve())
        with Image.open(asset) as image:
            assert image.format == "JPEG"
            assert image.width >= 640 and image.height >= 480
            image.verify()
