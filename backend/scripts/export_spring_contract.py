from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

import httpx

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
ENVIRONMENT_KEYS = {"servers", "host", "basePath", "schemes"}
ENVIRONMENT_HEADERS = {
    "forwarded",
    "host",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-port",
    "x-forwarded-proto",
}
EXCLUDED_TAGS = {"basic-error-controller"}
CONTROLLER_BY_MODULE = {
    "ai": "AiChatController",
    "anniversary": "AnniversaryController",
    "cart": "CartController",
    "challenge": "ChallengeController",
    "couple": "CoupleController",
    "coupleRank": "CoupleRankController",
    "coupleTree": "CoupleTreeController",
    "dailyGreeting": "DailyGreetingController",
    "dailyTask": "DailyTaskController",
    "deepQa": "DeepQaController",
    "feed": "FeedController",
    "heartMoment": "HeartMomentController",
    "invite": "InviteController",
    "loveCalendar": "LoveCalendarController",
    "menu": "MenuController",
    "mood": "MoodRecordController",
    "note": "NoteController",
    "notification": "NotificationController",
    "order": "OrderController",
    "poster": "PosterController",
    "recipe": "RecipeController",
    "relationshipWeather": "RelationshipWeatherController",
    "sweetBomb": "SweetBombController",
    "timeCapsule": "TimeCapsuleController",
    "upload": "UploadController",
    "user": "UserController",
    "wish": "WishController",
}
MIGRATION_BATCH_BY_MODULE = {
    "user": 1,
    "couple": 1,
    "anniversary": 2,
    "feed": 2,
    "menu": 2,
    "note": 2,
    "notification": 2,
    "recipe": 2,
    "upload": 2,
    "wish": 2,
    "ai": 3,
    "challenge": 4,
    "coupleRank": 4,
    "coupleTree": 4,
    "dailyGreeting": 4,
    "dailyTask": 4,
    "deepQa": 4,
    "heartMoment": 4,
    "loveCalendar": 4,
    "mood": 4,
    "relationshipWeather": 4,
    "sweetBomb": 4,
    "cart": 5,
    "invite": 5,
    "order": 5,
    "poster": 5,
    "timeCapsule": 5,
}
SIDE_EFFECTING_GETS = {
    "/api/coupleRank/info",
    "/api/coupleRank/rewards",
    "/api/coupleTree/info",
    "/api/coupleTree/skins",
    "/api/dailyTask/today",
    "/api/deepQa/current",
    "/api/deepQa/progress",
    "/api/invite/code",
    "/api/relationshipWeather/current",
    "/api/relationshipWeather/forecast",
    "/api/relationshipWeather/suggestions",
}

LOGGER = logging.getLogger("spring_contract_export")


class ContractExportError(RuntimeError):
    """An export failure whose message is safe to display or persist."""


def _sort_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json(item) for item in value]
    return value


def _is_environment_parameter(parameter: Any) -> bool:
    return (
        isinstance(parameter, dict)
        and parameter.get("in") == "header"
        and str(parameter.get("name", "")).lower() in ENVIRONMENT_HEADERS
    )


def normalize_openapi(document: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime-only metadata and return a recursively sorted API document."""
    normalized = deepcopy(document)
    for key in ENVIRONMENT_KEYS:
        normalized.pop(key, None)

    paths: dict[str, Any] = {}
    for path, raw_item in normalized.get("paths", {}).items():
        if not isinstance(raw_item, dict):
            continue
        item = deepcopy(raw_item)
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            if isinstance(operation.get("parameters"), list):
                operation["parameters"] = [
                    parameter
                    for parameter in operation["parameters"]
                    if not _is_environment_parameter(parameter)
                ]
        paths[path] = item
    normalized["paths"] = paths
    return cast(dict[str, Any], _sort_json(normalized))


def _contract_path(path: str) -> str:
    if path == "/api" or path.startswith("/api/"):
        return path
    return f"/api{path if path.startswith('/') else f'/{path}'}"


def _module_name(path: str) -> str:
    parts = path.removeprefix("/api/").split("/", maxsplit=1)
    return parts[0]


def route_inventory(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the owned Spring route inventory from Swagger 2 or OpenAPI 3 paths."""
    routes: list[dict[str, Any]] = []
    for path, item in normalize_openapi(document).get("paths", {}).items():
        if not isinstance(item, dict):
            continue
        contract_path = _contract_path(path)
        module = _module_name(contract_path)
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            tags = operation.get("tags") or []
            if EXCLUDED_TAGS.intersection(tags):
                continue
            upper_method = method.upper()
            routes.append(
                {
                    "method": upper_method,
                    "path": contract_path,
                    "controller": CONTROLLER_BY_MODULE.get(
                        module, str(tags[0]) if tags else "UnknownController"
                    ),
                    "sideEffect": upper_method != "GET" or contract_path in SIDE_EFFECTING_GETS,
                    "owner": "spring",
                    "migrationBatch": MIGRATION_BATCH_BY_MODULE.get(module),
                }
            )
    return sorted(routes, key=lambda route: (route["path"], route["method"]))


def _safe_source(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _fetch_document(url: str, transport: httpx.BaseTransport | None) -> dict[str, Any]:
    LOGGER.info("event=spring_contract_fetch_started source=%s", _safe_source(url))
    try:
        with httpx.Client(transport=transport, timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        LOGGER.error(
            "event=spring_contract_fetch_failed category=http status=%s",
            exc.response.status_code,
        )
        raise ContractExportError(
            f"Spring API 文档请求失败（HTTP {exc.response.status_code}）"
        ) from None
    except httpx.HTTPError as exc:
        LOGGER.error(
            "event=spring_contract_fetch_failed category=network errorType=%s",
            type(exc).__name__,
        )
        raise ContractExportError("Spring API 文档请求失败（网络错误）") from None

    try:
        raw_document: object = response.json()
    except ValueError:
        LOGGER.error("event=spring_contract_fetch_failed category=json")
        raise ContractExportError("Spring API 文档不是有效 JSON") from None
    if not isinstance(raw_document, dict):
        LOGGER.error("event=spring_contract_fetch_failed category=shape")
        raise ContractExportError("Spring API 文档顶层必须是 JSON object")
    document = cast(dict[str, Any], raw_document)
    LOGGER.info(
        "event=spring_contract_fetch_completed status=%s bytes=%s pathCount=%s",
        response.status_code,
        len(response.content),
        len(document.get("paths", {})),
    )
    return document


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        LOGGER.error("event=spring_contract_write_failed file=%s", path.name)
        raise ContractExportError(f"合同文件写入失败: {path.name}") from None
    LOGGER.info("event=spring_contract_write_completed file=%s bytes=%s", path.name, len(content))


def export_contract(
    url: str,
    output: Path,
    routes: Path,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[int, int]:
    """Fetch, normalize, inventory and atomically write the Spring contracts."""
    document = _fetch_document(url, transport)
    normalized = normalize_openapi(document)
    inventory = route_inventory(normalized)
    _atomic_write(output, _json_bytes(normalized))
    _atomic_write(routes, _json_bytes(inventory))
    LOGGER.info(
        "event=spring_contract_export_completed pathCount=%s routeCount=%s",
        len(normalized.get("paths", {})),
        len(inventory),
    )
    return len(normalized.get("paths", {})), len(inventory)


def main() -> None:
    parser = argparse.ArgumentParser(description="导出确定性的 Spring API 合同")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s level=%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        export_contract(args.url, args.output, args.routes)
    except ContractExportError as exc:
        LOGGER.error("event=spring_contract_export_failed message=%s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
