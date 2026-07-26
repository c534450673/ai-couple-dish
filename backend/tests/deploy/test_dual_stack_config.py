import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[3]
DOCKER_DIR = ROOT / "deploy/dev/docker"
BASE_COMPOSE = DOCKER_DIR / "docker-compose.yml"
OVERLAY_COMPOSE = DOCKER_DIR / "docker-compose.fastapi.yml"
NGINX_CONFIG = DOCKER_DIR / "nginx/conf.d/api-fastapi-foundation.conf"
OWNERSHIP = ROOT / "backend/contracts/migration-ownership.json"
ROUTES = ROOT / "backend/contracts/routes.json"


def _compose_config() -> dict:
    environment = os.environ.copy()
    environment["JWT_SECRET"] = "test-secret-" + "x" * 128
    docker_binary = shutil.which("docker")
    assert docker_binary is not None, "docker is required for Compose merge validation"
    result = subprocess.run(  # noqa: S603
        [
            docker_binary,
            "compose",
            "-f",
            str(BASE_COMPOSE),
            "-f",
            str(OVERLAY_COMPOSE),
            "config",
            "--format",
            "json",
        ],
        cwd=DOCKER_DIR,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(result.stdout)


def test_fastapi_overlay_does_not_replace_spring_writer() -> None:
    overlay = yaml.safe_load(OVERLAY_COMPOSE.read_text(encoding="utf-8"))
    service = overlay["services"]["fastapi-backend"]
    assert service["build"]["dockerfile"] == "Dockerfile.fastapi"
    assert service["expose"] == ["8000"]
    assert "ports" not in service
    assert "backend" not in overlay["services"]


def test_merged_compose_keeps_java_backend_and_resolves_context() -> None:
    document = _compose_config()
    backend = document["services"]["backend"]
    context = Path(backend["build"]["context"])
    assert document["services"]["fastapi-backend"]["build"]["context"].endswith("/backend")
    assert context / backend["build"]["dockerfile"] == ROOT / "backend/Dockerfile"
    assert (context / backend["build"]["dockerfile"]).is_file()


def test_nginx_routes_cutover_batch_to_fastapi_and_defaults_unknown_to_spring() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    assert "location = /api/health/live" in config
    assert "location = /api/health/ready" in config
    assert "location = /api/actuator/health" in config
    assert "location /api/" in config
    assert config.count("proxy_pass http://fastapi_backend;") == 20
    assert config.count("proxy_pass http://spring_backend;") == 1
    assert "split_clients" not in config
    assert "mirror" not in config
    assert "proxy_pass http://fastapi_backend" not in config.split("location /api/", 1)[1]
    assert "FastAPI cutover batch 1" in config
    assert "location ~ ^/api/notification/(read|delete)/[0-9]+$" in config
    assert "FastAPI cutover batch 2" in config
    assert "location ~ ^/api/wish/(delete|detail|fulfill|unfulfill|update)/[0-9]+$" in config
    assert "FastAPI cutover batch 3" in config
    assert "location ~ ^/api/heartMoment/delete/[0-9]+$" in config
    assert "FastAPI cutover batch 4" in config
    assert (
        "location ~ ^/api/challenge/(accept|cancel|checkin-records|detail|reject)/[0-9]+$"
        in config
    )
    assert "FastAPI cutover batch 5" in config
    assert "location ~ ^/api/mood/(detail|read)/[0-9]+$" in config
    assert "FastAPI cutover batch 6" in config
    assert "location ~ ^/api/timeCapsule/(delete|detail|unlock)/[0-9]+$" in config
    assert "FastAPI cutover batch 7" in config
    assert "location ~ ^/api/sweetBomb/(answer|detail|read)/[0-9]+$" in config
    assert "FastAPI cutover batch 8" in config
    assert (
        "location ~ ^/api/invite/(code|info/[^/]+|rank|referrals|stats|use|validate)$"
        in config
    )
    assert "FastAPI cutover batch 9" in config
    assert (
        "location ~ ^/api/coupleTree/(info|nutrientLogs|skin/change|skins|water)$" in config
    )


def test_nginx_cutover_patterns_match_exact_owner_inventory() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    patterns = [re.compile(value) for value in re.findall(r"location ~ (\^.*?\$) \{", config)]
    ownership = json.loads(OWNERSHIP.read_text(encoding="utf-8"))
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))

    for route_key in ownership["fastapiRoutes"]:
        path = re.sub(r"\{[^/]+\}", "123", route_key.split(" ", 1)[1])
        assert sum(bool(pattern.fullmatch(path)) for pattern in patterns) == 1

    for route in routes:
        if route["owner"] != "spring":
            continue
        path = re.sub(r"\{[^/]+\}", "123", route["path"])
        assert not any(pattern.fullmatch(path) for pattern in patterns)


def test_nginx_forwards_required_headers_in_each_location() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    for header in (
        "Host $host",
        "Authorization $http_authorization",
        "X-Request-ID $api_request_id",
        "X-Forwarded-For $proxy_add_x_forwarded_for",
        "X-Forwarded-Proto $scheme",
        "X-Forwarded-Host $host",
    ):
        assert config.count(f"proxy_set_header {header};") == 21


def test_nginx_access_log_is_request_metadata_only() -> None:
    config = NGINX_CONFIG.read_text(encoding="utf-8")
    assert "access_log /var/log/nginx/access.log api_safe;" in config
    log_format = config.split("log_format api_safe", 1)[1].split(";", 1)[0]
    assert "$api_request_id" in log_format
    assert "$request_id" in config.split("map $http_x_request_id $api_request_id", 1)[1]
    assert "$request_method" in log_format
    assert "$uri" in log_format
    assert "$status" in log_format
    assert "$request_time" in log_format
    assert "$upstream_status" in log_format
    for forbidden in (
        '"$request"',
        '"$args"',
        "$remote_addr",
        "$http_authorization",
        "$request_body",
    ):
        assert forbidden not in log_format


def test_overlay_replaces_api_conf_mount() -> None:
    overlay = yaml.safe_load(OVERLAY_COMPOSE.read_text(encoding="utf-8"))
    mounts = overlay["services"]["nginx"]["volumes"]
    assert any(
        mount.endswith(":/etc/nginx/conf.d/api.conf:ro")
        for mount in mounts
        if isinstance(mount, str)
    )
