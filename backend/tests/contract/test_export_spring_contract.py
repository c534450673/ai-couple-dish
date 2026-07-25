from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from scripts.export_spring_contract import (
    ContractExportError,
    _safe_source,
    export_contract,
    normalize_openapi,
    route_inventory,
)

BACKEND = Path(__file__).parents[2]
REPOSITORY = BACKEND.parent
CONTRACTS = BACKEND / "contracts"
FIXTURE = Path(__file__).parent / "fixtures" / "openapi-minimal.json"
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
EXPECTED_ERROR_CODES = {
    400,
    401,
    429,
    *range(1001, 1007),
    *range(2001, 2009),
    *range(3001, 3004),
    *range(4001, 4003),
    *range(5001, 5004),
    *range(6001, 6005),
    *range(7001, 7004),
    *range(8001, 8004),
    *range(8501, 8503),
    *range(8601, 8604),
    *range(8701, 8703),
    *range(8801, 8805),
    *range(8901, 8904),
    *range(8951, 8954),
    *range(9001, 9008),
    9999,
}
EXPECTED_REDIS_PATTERNS = {
    "logout:blacklist:<jti>",
    "user:verify:code:<phone>",
    "user:verify:expire:<phone>",
    "couple:code:<8-char-code>",
    "couple:code:user:<userId>",
    "ai:session:msg:<userId>:<sessionId>",
    "ai:session:pending:<userId>:<sessionId>",
    "rate_limit:<scope>:<identityHmac>",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_js_arguments(arguments: str) -> list[str]:
    values: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, character in enumerate(arguments):
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
        elif character == "," and depth == 0:
            values.append(arguments[start:index].strip())
            start = index + 1
    values.append(arguments[start:].strip())
    return values


def _call_arguments(source: str, opening_parenthesis: int) -> list[str]:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(opening_parenthesis, len(source)):
        character = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return _split_js_arguments(source[opening_parenthesis + 1 : index])
    raise AssertionError("JavaScript call is not balanced")


def _parameter_names(signature: str) -> list[str]:
    return [
        parameter.split("=", maxsplit=1)[0].strip()
        for parameter in _split_js_arguments(signature)
        if parameter.strip()
    ]


def _query_parameters(config: str, public_parameters: list[str]) -> list[str]:
    object_match = re.search(r"\bparams\s*:\s*\{([^}]*)\}", config, re.DOTALL)
    if object_match:
        return re.findall(r"\b[A-Za-z_$][\w$]*\b", object_match.group(1))
    value_match = re.search(r"\bparams\s*:\s*([A-Za-z_$][\w$]*)", config)
    if value_match:
        value = value_match.group(1)
        if "params" in public_parameters and value.lower().endswith("params"):
            return ["params"]
        return [value]
    if re.search(r"[{,]\s*params\s*[,}]", config):
        return ["params"]
    return []


def _normalize_js_path(expression: str) -> str:
    path = expression.strip().strip("'\"`")
    path = re.sub(r"\$\{(?:data\.)?(\w+)\}", r"{\1}", path)
    return f"/api{path}"


def _extract_axios_consumers(source: str) -> list[dict[str, Any]]:
    consumers: list[dict[str, Any]] = []
    export_name: str | None = None
    function_name: str | None = None
    public_parameters: list[str] = []
    function_start = 0
    offset = 0
    for line_number, line in enumerate(source.splitlines(keepends=True), start=1):
        export_match = re.match(r"export const (\w+) = \{", line)
        if export_match:
            export_name = export_match.group(1)
        elif export_name and line.startswith("}"):
            export_name = None
            function_name = None
        function_match = re.match(r"  (\w+)\((.*?)\) \{", line)
        if function_match:
            function_name = function_match.group(1)
            public_parameters = _parameter_names(function_match.group(2))
            function_start = offset
        call = re.search(r"return api\.(get|post|put|delete|patch)\(", line)
        if call and export_name is not None and function_name is not None:
            method = call.group(1).upper()
            opening_parenthesis = offset + call.end() - 1
            arguments = _call_arguments(source, opening_parenthesis)
            path = _normalize_js_path(arguments[0])
            path_parameters = re.findall(r"\{([^}]+)\}", path)
            config_index = 1 if method == "GET" else 2
            config = arguments[config_index] if len(arguments) > config_index else ""
            query_parameters = _query_parameters(config, public_parameters)
            body: list[str] = []
            multipart: list[str] = []
            if method in {"POST", "PUT", "PATCH"} and len(arguments) > 1:
                body_argument = arguments[1]
                if body_argument == "formData":
                    multipart = re.findall(
                        r"formData\.append\(['\"]([^'\"]+)", source[function_start:offset]
                    )
                elif body_argument not in {"", "null", "undefined"}:
                    body = [body_argument]
            consumers.append(
                {
                    "sourceFile": "frontend-h5/src/api/index.js",
                    "exportName": export_name,
                    "functionName": function_name,
                    "method": method,
                    "path": path,
                    "sourceLine": line_number,
                    "transport": "axios",
                    "parameters": {
                        "path": path_parameters,
                        "query": query_parameters,
                        "body": body,
                        "multipart": multipart,
                    },
                }
            )
        offset += len(line)
    return consumers


def _extract_ai_consumers(source: str) -> list[dict[str, Any]]:
    helper = re.search(
        r"async function postJson\([^)]*\) \{(?P<body>.*?)^}",
        source,
        re.DOTALL | re.MULTILINE,
    )
    assert helper is not None
    helper_method = re.search(r"method:\s*['\"]([A-Z]+)['\"]", helper.group("body"))
    assert helper_method is not None

    stream = re.search(
        r"export async function streamChat\([^)]*\) \{(?P<body>.*?)^}",
        source,
        re.DOTALL | re.MULTILINE,
    )
    assert stream is not None
    stream_fetch = re.search(
        r"fetch\(`\$\{BASE_URL\}(?P<path>[^`]+)`\s*,\s*\{(?P<options>.*?)\n\s*}\)",
        stream.group("body"),
        re.DOTALL,
    )
    assert stream_fetch is not None
    stream_method = re.search(r"method:\s*['\"]([A-Z]+)['\"]", stream_fetch.group("options"))
    stream_body = re.search(r"body:\s*JSON\.stringify\((\w+)\)", stream_fetch.group("options"))
    assert stream_method is not None and stream_body is not None
    method_offset = stream.start("body") + stream_fetch.start("options") + stream_method.start()
    consumers = [
        {
            "sourceFile": "frontend-h5/src/api/ai.js",
            "exportName": "namedExport",
            "functionName": "streamChat",
            "method": stream_method.group(1),
            "path": f"/api{stream_fetch.group('path')}",
            "sourceLine": source.count("\n", 0, method_offset) + 1,
            "transport": "fetch",
            "parameters": {
                "path": [],
                "query": [],
                "body": [stream_body.group(1)],
                "multipart": [],
            },
        }
    ]

    wrapper_pattern = re.compile(
        r"export function (?P<name>\w+)\([^)]*\) \{\n"
        r"(?P<indent>\s*)return postJson\((?P<arguments>[^\n]+)\)\n}",
    )
    for wrapper in wrapper_pattern.finditer(source):
        arguments = _split_js_arguments(wrapper.group("arguments"))
        body = re.findall(r"\b[A-Za-z_$][\w$]*\b", arguments[1])
        return_offset = wrapper.start("indent") + len(wrapper.group("indent"))
        consumers.append(
            {
                "sourceFile": "frontend-h5/src/api/ai.js",
                "exportName": "namedExport",
                "functionName": wrapper.group("name"),
                "method": helper_method.group(1),
                "path": f"/api{arguments[0].strip(chr(39) + chr(34))}",
                "sourceLine": source.count("\n", 0, return_offset) + 1,
                "transport": "fetch",
                "parameters": {"path": [], "query": [], "body": body, "multipart": []},
            }
        )
    return consumers


def test_normalization_removes_environment_noise_and_is_idempotent() -> None:
    normalized = normalize_openapi(load_json(FIXTURE))

    assert not ({"servers", "host", "basePath", "schemes"} & normalized.keys())
    assert list(normalized["paths"]) == sorted(normalized["paths"])
    parameters = normalized["paths"]["/zeta/items"]["post"]["parameters"]
    assert [parameter["name"] for parameter in parameters] == ["payload"]
    assert normalize_openapi(normalized) == normalized


def test_normalization_supports_openapi_3_and_sorts_operations() -> None:
    source = {
        "openapi": "3.0.3",
        "servers": [{"url": "http://runtime.invalid/api"}],
        "paths": {
            "/user": {
                "post": {"tags": ["用户模块"]},
                "get": {"tags": ["用户模块"]},
            }
        },
    }

    normalized = normalize_openapi(source)

    assert "servers" not in normalized
    assert list(normalized["paths"]["/user"]) == ["get", "post"]


def test_route_inventory_sorts_prefixes_and_excludes_basic_error_controller() -> None:
    routes = route_inventory(load_json(FIXTURE))

    assert [(route["method"], route["path"]) for route in routes] == [
        ("GET", "/api/alpha/items/{id}"),
        ("POST", "/api/zeta/items"),
    ]
    assert all(route["owner"] == "spring" for route in routes)
    assert not any(route["path"] == "/api/error" for route in routes)


def test_route_inventory_does_not_duplicate_api_prefix() -> None:
    source = {
        "swagger": "2.0",
        "paths": {"/api/user/info": {"get": {"tags": ["用户模块"]}}},
    }

    assert route_inventory(source)[0]["path"] == "/api/user/info"


def test_export_is_deterministic_and_uses_atomic_outputs(tmp_path: Path) -> None:
    source = load_json(FIXTURE)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=source))
    openapi_output = tmp_path / "spring-openapi.json"
    routes_output = tmp_path / "routes.json"

    for _ in range(2):
        export_contract(
            "http://spring.invalid/api/v2/api-docs",
            openapi_output,
            routes_output,
            transport=transport,
        )
        hashes = tuple(
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (openapi_output, routes_output)
        )
        if _ == 0:
            first_hashes = hashes

    assert first_hashes == hashes
    assert not list(tmp_path.glob(".*.tmp"))
    assert openapi_output.read_bytes().endswith(b"\n")


def test_export_restores_both_outputs_when_second_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = load_json(FIXTURE)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=source))
    openapi_output = tmp_path / "spring-openapi.json"
    routes_output = tmp_path / "routes.json"
    openapi_output.write_bytes(b"old-openapi\n")
    routes_output.write_bytes(b"old-routes\n")
    real_replace = os.replace
    published_targets: list[Path] = []

    def fail_second_publish(source_path: str | Path, destination: str | Path) -> None:
        source = Path(source_path)
        target = Path(destination)
        if source.suffix == ".tmp" and target in {openapi_output, routes_output}:
            published_targets.append(target)
            if target == routes_output:
                raise OSError("second publish failed")
        real_replace(source, target)

    monkeypatch.setattr("scripts.export_spring_contract.os.replace", fail_second_publish)

    with pytest.raises(ContractExportError):
        export_contract(
            "http://spring.invalid/api/v2/api-docs",
            openapi_output,
            routes_output,
            transport=transport,
        )

    assert published_targets == [openapi_output, routes_output]
    assert openapi_output.read_bytes() == b"old-openapi\n"
    assert routes_output.read_bytes() == b"old-routes\n"
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".*.bak"))


@pytest.mark.parametrize(
    ("response", "forbidden"),
    [
        (httpx.Response(503, text="private response body"), "private response body"),
        (httpx.Response(200, text="not-json-private-body"), "not-json-private-body"),
    ],
)
def test_export_http_and_json_errors_do_not_leak_query_or_body(
    tmp_path: Path,
    response: httpx.Response,
    forbidden: str,
) -> None:
    transport = httpx.MockTransport(lambda _request: response)

    with pytest.raises(ContractExportError) as raised:
        export_contract(
            "http://spring.invalid/api/v2/api-docs?token=private-query",
            tmp_path / "spring-openapi.json",
            tmp_path / "routes.json",
            transport=transport,
        )

    message = str(raised.value)
    assert "private-query" not in message
    assert forbidden not in message


def test_export_write_errors_do_not_leak_os_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = load_json(FIXTURE)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=source))

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("private disk mount detail")

    monkeypatch.setattr("scripts.export_spring_contract.os.replace", fail_replace)

    with pytest.raises(ContractExportError) as raised:
        export_contract(
            "http://spring.invalid/api/v2/api-docs",
            tmp_path / "spring-openapi.json",
            tmp_path / "routes.json",
            transport=transport,
        )

    assert "private disk mount detail" not in str(raised.value)


def test_safe_source_removes_userinfo_query_and_fragment() -> None:
    source = _safe_source(
        "https://private-user:private-password@spring.invalid:8443/api/v2/api-docs"
        "?token=private-query#private-fragment"
    )

    assert source == "https://spring.invalid:8443/api/v2/api-docs"
    assert "private-user" not in source
    assert "private-password" not in source
    assert "private-query" not in source


def test_spring_routes_are_complete_unique_and_sorted() -> None:
    routes = load_json(CONTRACTS / "routes.json")

    assert len(routes) == 193
    assert routes == sorted(routes, key=lambda item: (item["path"], item["method"]))
    assert len({(route["method"], route["path"]) for route in routes}) == 193
    assert all(route["method"] in HTTP_METHODS for route in routes)
    assert all(route["path"].startswith("/api/") for route in routes)
    assert all(route["owner"] == "spring" for route in routes)
    assert len({route["controller"] for route in routes}) == 27
    assert all(route["controller"].endswith("Controller") for route in routes)
    assert all(route["migrationBatch"] in {1, 2, 3, 4, 5} for route in routes)
    assert all(isinstance(route["sideEffect"], bool) for route in routes)


def test_real_swagger_reconciliation_excludes_only_five_framework_operations() -> None:
    document = load_json(CONTRACTS / "spring-openapi.json")
    operations = [
        (method, path, operation)
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if method.lower() in {item.lower() for item in HTTP_METHODS}
    ]
    framework_operations = [
        (method, path, operation["operationId"])
        for method, path, operation in operations
        if "basic-error-controller" in operation.get("tags", [])
    ]

    assert len(operations) == 198
    assert framework_operations == [
        ("delete", "/api/error", "errorUsingDELETE"),
        ("get", "/api/error", "errorUsingGET"),
        ("patch", "/api/error", "errorUsingPATCH"),
        ("post", "/api/error", "errorUsingPOST"),
        ("put", "/api/error", "errorUsingPUT"),
    ]


def test_route_migration_batches_cover_every_controller() -> None:
    routes = load_json(CONTRACTS / "routes.json")
    batches_by_controller: dict[str, set[int]] = {}
    for route in routes:
        batches_by_controller.setdefault(route["controller"], set()).add(route["migrationBatch"])

    assert all(len(batches) == 1 for batches in batches_by_controller.values())
    assert {batch for batches in batches_by_controller.values() for batch in batches} == {
        1,
        2,
        3,
        4,
        5,
    }


def test_get_side_effect_exceptions_are_explicit() -> None:
    routes = load_json(CONTRACTS / "routes.json")
    side_effecting_gets = {
        route["path"]
        for route in routes
        if route["method"] == "GET" and route["sideEffect"]
    }

    assert side_effecting_gets == {
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


def test_h5_consumers_match_current_source_calls() -> None:
    consumers = load_json(CONTRACTS / "h5-consumers.json")
    index_source = (REPOSITORY / "frontend-h5/src/api/index.js").read_text(encoding="utf-8")
    ai_source = (REPOSITORY / "frontend-h5/src/api/ai.js").read_text(encoding="utf-8")

    extracted = _extract_axios_consumers(index_source) + _extract_ai_consumers(ai_source)

    assert len(extracted) == 78
    assert consumers == extracted


def test_h5_axios_entries_are_independently_extracted_from_source() -> None:
    consumers = load_json(CONTRACTS / "h5-consumers.json")
    source = (REPOSITORY / "frontend-h5/src/api/index.js").read_text(encoding="utf-8")

    extracted = _extract_axios_consumers(source)
    recorded = [item for item in consumers if item["transport"] == "axios"]

    assert len(extracted) == 74
    assert recorded == extracted


def test_every_h5_consumer_has_a_spring_wire_route() -> None:
    consumers = load_json(CONTRACTS / "h5-consumers.json")
    routes = load_json(CONTRACTS / "routes.json")

    def wire_path(path: str) -> str:
        return re.sub(r"\{[^}]+\}", "{}", path)

    spring_routes = {(route["method"], wire_path(route["path"])) for route in routes}
    assert {
        (item["method"], wire_path(item["path"]))
        for item in consumers
    }.issubset(spring_routes)


def test_error_codes_are_full_unique_and_preserve_ambiguity() -> None:
    entries = load_json(CONTRACTS / "error-codes.json")
    codes = [entry["code"] for entry in entries]

    assert set(codes) == EXPECTED_ERROR_CODES
    assert len(codes) == len(set(codes)) == 60
    expected_fields = {"code", "httpStatus", "message", "ambiguousUsages"}
    assert all(set(entry) == expected_fields for entry in entries)
    assert all(isinstance(entry["httpStatus"], int) for entry in entries)
    assert all(isinstance(entry["message"], str) and entry["message"] for entry in entries)
    ambiguous = {entry["code"]: entry["ambiguousUsages"] for entry in entries}
    assert all(ambiguous[code] for code in range(9001, 9006))


def test_redis_keys_are_exact_and_unique() -> None:
    entries = load_json(CONTRACTS / "redis-keys.json")
    patterns = [entry["pattern"] for entry in entries]

    assert set(patterns) == EXPECTED_REDIS_PATTERNS
    assert len(patterns) == len(set(patterns)) == 8
    assert all(set(entry) == {"pattern", "ttl", "sensitive"} for entry in entries)


def test_contracts_contain_no_concrete_secrets_or_personal_data() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(CONTRACTS.glob("*"))
        if path.is_file()
    )
    forbidden_patterns = {
        "bearer token": r"(?i)Bearer\s+[A-Za-z0-9._-]{20,}",
        "JWT": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "mainland phone": r"(?<!\d)1[3-9]\d{9}(?!\d)",
        "API key": r"(?i)(?:sk|stitch)[-_][A-Za-z0-9_-]{16,}",
    }

    assert {
        name: pattern
        for name, pattern in forbidden_patterns.items()
        if re.search(pattern, text)
    } == {}
