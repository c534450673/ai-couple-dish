from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import jwt
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.exc import OperationalError

from app.db.models import CatalogDishImage
from services.media.app.main import app, create_app
from services.media.app.services.image_policy import validate_and_thumbnail
from services.media.app.services.storage import Storage

ADMIN_SECRET = "admin-test-secret-" + "x" * 64


def _admin_token() -> str:
    return jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "iss": "admin-service",
            "aud": "admin-web",
            "jti": "media-test",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        ADMIN_SECRET,
        algorithm="HS512",
    )


def _image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (100, 80), "red").save(output, format="JPEG")
    return output.getvalue()


class _Session:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.records: list[Any] = []
        self.committed = False

    def add(self, record: Any) -> None:
        self.records.append(record)

    async def commit(self) -> None:
        if self.error:
            raise self.error
        self.committed = True

    async def scalar(self, _statement: Any) -> Any:
        return getattr(self, "metadata", None)


def _provider(session: _Session):
    @asynccontextmanager
    async def provide():
        yield session

    return provide


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
    monkeypatch.setenv("ADMIN_JWT_SECRET", ADMIN_SECRET)
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


def test_media_upload_persists_authorization_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", ADMIN_SECRET)
    session = _Session()
    service = create_app(session_provider=_provider(session))
    storage = Storage(tmp_path)
    monkeypatch.setattr(service.state, "storage", storage)

    response = TestClient(service).post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        files={"file": ("dish.jpg", _image_bytes(), "image/jpeg")},
        data={
            "dish_slug": "kung-pao-chicken",
            "source_url": "https://example.test/source",
            "license_name": "CC-BY-4.0",
            "attribution": "Example Author",
            "license_expires_at": "2030-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 200
    assert session.committed is True
    assert len(session.records) == 1
    record = session.records[0]
    assert record.dish_slug == "kung-pao-chicken"
    assert record.source_url == "https://example.test/source"
    assert record.license_name == "CC-BY-4.0"
    assert record.attribution == "Example Author"
    assert record.review_status == "pending"
    assert record.width == 100 and record.height == 80
    assert record.object_key.startswith("images/")
    assert record.thumbnail_key.startswith("thumbnails/")
    assert storage.get_path(record.object_key).is_file()
    assert storage.get_path(record.thumbnail_key).is_file()


def test_media_upload_cleans_objects_when_metadata_commit_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", ADMIN_SECRET)
    session = _Session(error=OperationalError("INSERT", {}, RuntimeError("db down")))
    service = create_app(session_provider=_provider(session))
    storage = Storage(tmp_path)
    monkeypatch.setattr(service.state, "storage", storage)

    response = TestClient(service).post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {_admin_token()}"},
        files={"file": ("dish.jpg", _image_bytes(), "image/jpeg")},
        data={
            "dish_slug": "kung-pao-chicken",
            "source_url": "https://example.test/source",
            "license_name": "CC0",
            "attribution": "Example Author",
        },
    )

    assert response.status_code == 503
    assert session.records
    record = session.records[0]
    assert not (storage.root / record.object_key).exists()
    assert not (storage.root / record.thumbnail_key).exists()


def test_media_delivery_requires_approved_unexpired_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ADMIN_JWT_SECRET", ADMIN_SECRET)
    storage = Storage(tmp_path)
    content = _image_bytes()
    key = storage.put(content)
    session = _Session()
    session.metadata = CatalogDishImage(
        dish_slug="kung-pao-chicken",
        object_key=key,
        source_url="https://example.test/source",
        license_name="CC0",
        attribution="Example Author",
        review_status="pending",
        width=100,
        height=80,
    )
    service = create_app(session_provider=_provider(session))
    monkeypatch.setattr(service.state, "storage", storage)
    client = TestClient(service)

    pending = client.get(storage.url(key))
    assert pending.status_code == 404

    session.metadata.review_status = "approved"
    session.metadata.license_expires_at = datetime.now(UTC).replace(tzinfo=None)
    expired = client.get(storage.url(key))
    assert expired.status_code == 404

    session.metadata.license_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
    approved = client.get(storage.url(key))
    assert approved.status_code == 200
    assert approved.content == content
