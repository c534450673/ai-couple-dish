from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from services.media.app.main import app
from services.media.app.services.storage import Storage


def test_stored_image_url_is_served_by_media_api(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MEDIA_PUBLIC_BASE_URL", raising=False)
    storage = Storage(tmp_path)
    monkeypatch.setattr(app.state, "storage", storage)
    output = BytesIO()
    Image.new("RGB", (32, 24), "red").save(output, format="JPEG")
    content = output.getvalue()
    key = storage.put(content)

    response = TestClient(app).get(storage.url(key), headers={"X-Request-ID": "media-test"})

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert response.headers["content-length"] == str(len(content))

    head = TestClient(app).head(storage.url(key), headers={"X-Request-ID": "media-head-test"})

    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-type"] == response.headers["content-type"]
    assert head.headers["cache-control"] == response.headers["cache-control"]
    assert head.headers["content-length"] == response.headers["content-length"]


def test_media_rejects_unissued_keys(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app.state, "storage", Storage(tmp_path))
    client = TestClient(app)

    invalid_category = client.get("/api/media/files/private/" + "a" * 32 + ".jpg")
    missing_file = client.get("/api/media/files/images/" + "a" * 32 + ".jpg")
    invalid_filename = client.get("/api/media/files/images/not-an-upload.jpg")
    invalid_head = client.head("/api/media/files/images/not-an-upload.jpg")

    assert invalid_category.status_code == 404
    assert missing_file.status_code == 404
    assert invalid_filename.status_code == 404
    assert invalid_head.status_code == invalid_filename.status_code


def test_media_rejects_symlink_outside_storage(tmp_path, monkeypatch) -> None:
    storage = Storage(tmp_path / "storage")
    monkeypatch.setattr(app.state, "storage", storage)
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"private data")
    (storage.root / "images").mkdir()
    filename = "a" * 32 + ".jpg"
    (storage.root / "images" / filename).symlink_to(outside)

    response = TestClient(app).get(f"/api/media/files/images/{filename}")

    assert response.status_code == 404
    assert b"private data" not in response.content
