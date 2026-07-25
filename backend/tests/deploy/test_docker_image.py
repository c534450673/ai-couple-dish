from pathlib import Path

ROOT = Path(__file__).parents[3]
DOCKERFILE = ROOT / "backend/Dockerfile.fastapi"


def test_fastapi_dockerfile_uses_pinned_uv_python_and_frozen_production_sync() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "ghcr.io/astral-sh/uv:0.11.21" in dockerfile
    assert "FROM python:3.12-slim-bookworm AS builder" in dockerfile
    assert "FROM python:3.12-slim-bookworm AS runtime" in dockerfile
    assert "uv sync --frozen --no-dev --no-install-project" in dockerfile
    assert "uv sync --frozen --dev" not in dockerfile
    assert "COPY ." not in dockerfile
    assert "COPY .env" not in dockerfile
    assert "COPY tests" not in dockerfile
    assert "COPY contracts" not in dockerfile


def test_fastapi_dockerfile_keeps_build_tools_out_of_runtime() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    builder, runtime = dockerfile.split("FROM python:3.12-slim-bookworm AS runtime", 1)
    assert "apt-get install" in builder
    assert "gcc" in builder
    assert "COPY --from=builder /app/.venv /app/.venv" in runtime
    assert "COPY app ./app" in runtime
    assert "gcc" not in runtime
    assert "apt-get install" not in runtime
    assert "COPY --from=uv-bin" not in runtime
    assert "uv sync" not in runtime


def test_fastapi_dockerfile_runs_as_non_root_with_healthcheck_and_command() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "groupadd --system app" in dockerfile
    assert "useradd --system --gid app --home /app app" in dockerfile
    assert "USER app" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/api/health/live" in dockerfile
    assert '"uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"' in dockerfile


def test_fastapi_dockerfile_does_not_embed_secrets_or_test_assets() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    forbidden = ("JWT_SECRET=", "DB_PASSWORD=", "REDIS_PASSWORD=", "tests/", "contracts/")
    assert all(value not in dockerfile for value in forbidden)
