import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[3]
COMPOSE = ROOT / "deploy/dev/docker/docker-compose.python.yml"
NGINX = ROOT / "deploy/dev/docker/nginx/conf.d/api-python-microservices.conf"
EXPECTED_SERVICES = {
    "gateway",
    "identity",
    "catalog",
    "dining",
    "media",
    "admin",
    "analytics",
    "worker",
}


def _config() -> dict:
    docker = shutil.which("docker")
    assert docker, "docker is required for Python Compose validation"
    environment = os.environ.copy()
    environment.update(
        {
            "JWT_SECRET": "j" * 96,
            "ADMIN_JWT_SECRET": "a" * 96,
            "ADMIN_PASSWORD_HASH": "$2b$12$C6UzMDM.H6dfI/f/IKcEe.",
        }
    )
    result = subprocess.run(  # noqa: S603
        [docker, "compose", "-f", str(COMPOSE), "config", "--format", "json"],
        cwd=COMPOSE.parent,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(result.stdout)


def test_python_compose_declares_all_runtime_services() -> None:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = set(document["services"])
    assert EXPECTED_SERVICES <= services
    assert {"mysql", "redis", "migration", "uploads-init", "nginx"} <= services


def test_python_compose_merges_to_distinct_ports_and_migration_gate() -> None:
    document = _config()
    services = document["services"]
    ports = {
        service: services[service]["command"][services[service]["command"].index("--port") + 1]
        for service in EXPECTED_SERVICES
    }
    assert ports == {
        "gateway": "8000",
        "identity": "8001",
        "catalog": "8002",
        "dining": "8003",
        "media": "8004",
        "admin": "8005",
        "analytics": "8006",
        "worker": "8007",
    }
    for service in EXPECTED_SERVICES - {"worker"}:
        assert services[service]["depends_on"]["migration"]["condition"] == (
            "service_completed_successfully"
        )


def test_python_compose_routes_gateway_through_nginx_without_java_fallback() -> None:
    document = _config()
    assert document["services"]["nginx"]["depends_on"]["gateway"]["condition"] == (
        "service_healthy"
    )
    config = NGINX.read_text(encoding="utf-8")
    assert "server gateway:8000;" in config
    assert "proxy_pass http://python_gateway;" in config
    assert "spring_backend" not in config


def test_python_compose_uses_isolated_volumes_and_non_root_runtime() -> None:
    document = _config()
    assert "python_mysql_data" in document["volumes"]
    assert "python_redis_data" in document["volumes"]
    assert "python_uploads_data" in document["volumes"]
    dockerfile = (ROOT / "backend/Dockerfile.fastapi").read_text(encoding="utf-8")
    assert "USER app" in dockerfile
