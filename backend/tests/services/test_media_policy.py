from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from services.media.app.main import app
from services.media.app.services.image_policy import validate_and_thumbnail


def test_media_policy_reencodes_allowed_image() -> None:
    out = BytesIO()
    Image.new("RGB", (100, 80), "red").save(out, format="PNG")
    result = validate_and_thumbnail(out.getvalue(), filename="dish.png")
    assert result.mime == "image/jpeg"
    assert result.width == 100 and result.height == 80


def test_media_policy_rejects_svg() -> None:
    import pytest

    with pytest.raises(ValueError):
        validate_and_thumbnail(b"<svg/>", filename="dish.svg")


def test_media_upload_rejects_anonymous_requests(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", "admin-test-secret-" + "x" * 64)
    response = TestClient(app).post(
        "/api/media/upload",
        files={"file": ("dish.jpg", b"not-an-image", "image/jpeg")},
        data={
            "source_url": "https://example.test/source",
            "license_name": "CC0",
            "attribution": "Author",
        },
    )
    assert response.status_code == 401
