from pathlib import Path

import yaml

ROOT = Path(__file__).parents[3]
OVERLAY = ROOT / "deploy/dev/docker/docker-compose.fastapi.yml"
NGINX = ROOT / "deploy/dev/docker/nginx/conf.d/api-fastapi-foundation.conf"
DOCKERFILE = ROOT / "backend/Dockerfile.fastapi"
CONTAINER_SMOKE = ROOT / "backend/scripts/smoke_poster_container.sh"


def test_fastapi_overlay_uses_persistent_writable_upload_volume() -> None:
    document = yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))
    service = document["services"]["fastapi-backend"]

    assert service["environment"]["FILE_UPLOAD_PATH"] == "/app/uploads"
    assert service["environment"]["FILE_BASE_URL"] == "/api/uploads"
    assert service["environment"]["FILE_PUBLIC_PATH"] == "/api/uploads"
    assert "uploads_data:/app/uploads" in service["volumes"]
    assert service["depends_on"]["fastapi-uploads-init"]["condition"] == (
        "service_completed_successfully"
    )

    initializer = document["services"]["fastapi-uploads-init"]
    assert initializer["user"] == "0:0"
    assert "uploads_data:/app/uploads" in initializer["volumes"]
    assert "10001:10001" in " ".join(initializer["command"])


def test_nginx_only_exposes_exact_poster_static_prefix_to_fastapi() -> None:
    config = NGINX.read_text(encoding="utf-8")

    assert "location ^~ /api/uploads/poster/" in config
    static_block = config.split("location ^~ /api/uploads/poster/", 1)[1].split("}", 1)[0]
    assert "proxy_pass http://fastapi_backend;" in static_block
    business_block = config.split("location /api/", 1)[1].split("}", 1)[0]
    assert "proxy_pass http://spring_backend;" in business_block
    assert "proxy_pass http://fastapi_backend;" not in business_block
    assert "location /api/poster/" not in config


def test_fastapi_image_pins_non_root_identity_and_prepares_upload_directory() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "--gid 10001 app" in dockerfile
    assert "--uid 10001" in dockerfile
    assert "mkdir -p /app/uploads" in dockerfile
    assert "chown -R app:app /app" in dockerfile
    assert "USER app" in dockerfile


def test_poster_container_persistence_smoke_is_explicit_and_reproducible() -> None:
    script = CONTAINER_SMOKE.read_text(encoding="utf-8")

    assert "RUN_POSTER_CONTAINER_SMOKE" in script
    assert "docker build" in script
    assert 'features.check("freetype2")' in script
    assert 'features.check("webp")' in script
    assert "--lifespan off" in script
    assert "trap cleanup EXIT" in script
    assert "sameBytes" in script
