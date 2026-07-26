import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app import main
from app.core.config import Settings
from app.main import create_app

BASE = {
    "DB_PASSWORD": "db-secret",
    "JWT_SECRET": "x" * 64,
}


@pytest.mark.parametrize(
    ("base_url", "public_path"),
    [
        ("/api/uploads", "/api/uploads"),
        ("https://api.example.com/uploads", "/uploads"),
    ],
)
def test_poster_public_path_accepts_only_matching_publish_urls(
    base_url: str, public_path: str
) -> None:
    settings = Settings(
        _env_file=None,
        FILE_BASE_URL=base_url,
        FILE_PUBLIC_PATH=public_path,
        **BASE,
    )

    assert settings.file_public_path == public_path
    app = create_app(settings)
    assert any(route.path == public_path and route.name == "uploads" for route in app.routes)


@pytest.mark.parametrize(
    ("base_url", "public_path"),
    [
        ("https://api.example.com/uploads?token=secret", "/uploads"),
        ("https://api.example.com/uploads#fragment", "/uploads"),
        ("ftp://api.example.com/uploads", "/uploads"),
        ("https://api.example.com/uploads", "/api/uploads"),
        ("//api.example.com/uploads", "/uploads"),
        ("/api/uploads/../private", "/api/private"),
        ("/api/uploads", "api/uploads"),
    ],
)
def test_poster_public_path_rejects_unsafe_or_mismatched_values(
    base_url: str, public_path: str
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            FILE_BASE_URL=base_url,
            FILE_PUBLIC_PATH=public_path,
            **BASE,
        )


@pytest.mark.parametrize(
    ("base_url", "public_path"),
    [
        ("/api//uploads", "/api//uploads"),
        ("/api/./uploads", "/api/./uploads"),
        ("/api/uploads/../private", "/api/uploads/../private"),
    ],
)
def test_poster_public_path_rejects_raw_empty_and_dot_segments(
    base_url: str, public_path: str
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            FILE_BASE_URL=base_url,
            FILE_PUBLIC_PATH=public_path,
            **BASE,
        )


@pytest.mark.parametrize("concurrency", [1, 2, 4])
def test_poster_render_concurrency_is_bounded(concurrency: int) -> None:
    settings = Settings(
        _env_file=None,
        POSTER_RENDER_CONCURRENCY=concurrency,
        **BASE,
    )
    app = create_app(settings)

    assert settings.poster_render_concurrency == concurrency
    assert app.state.poster_render_semaphore._value == concurrency


@pytest.mark.parametrize("concurrency", [0, 5])
def test_poster_render_concurrency_rejects_out_of_range(concurrency: int) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            POSTER_RENDER_CONCURRENCY=concurrency,
            **BASE,
        )


def test_app_creation_fails_when_vendored_fonts_are_missing(monkeypatch) -> None:
    def missing_fonts() -> None:
        raise RuntimeError("font validation failed")

    monkeypatch.setattr(main.poster_renderer, "validate_font_assets", missing_fonts)

    with pytest.raises(RuntimeError, match="font validation failed"):
        create_app(Settings(_env_file=None, **BASE))
