from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_CASES = BACKEND / "contracts/cases/foundation.json"
DEFAULT_ROUTES = BACKEND / "contracts/routes.json"
DEFAULT_OWNERSHIP = BACKEND / "contracts/migration-ownership.json"
CREDENTIAL_ENV = "CONTRACT_TEST_TOKEN"
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
OPERATIONAL_ROUTES = (
    "GET /api/health/live",
    "GET /api/health/ready",
    "GET /api/actuator/health",
)
UNKNOWN_ROUTE = "GET /api/__contract_unknown__"
TEST_APP_CASES = {
    "test-app-no-token": "GET /api/__contract/protected",
    "test-app-invalid-json": "POST /api/__contract/validate",
    "test-app-invalid-field": "POST /api/__contract/validate",
}


class ContractConfigurationError(RuntimeError):
    """Raised when contract inputs cannot be executed safely."""


class RouteOwnershipError(ContractConfigurationError):
    """Raised when a dual comparison is attempted for a Spring-owned route."""


class SideEffectRejected(ContractConfigurationError):
    """Raised unless both side-effect safety gates are enabled."""


@dataclass(frozen=True)
class Comparison:
    case_id: str
    equal: bool
    spring: dict[str, Any]
    fastapi: dict[str, Any]
    method: str = ""
    route: str = ""

    def safe_difference(self) -> dict[str, Any]:
        spring_paths = _json_paths(self.spring.get("body"))
        fastapi_paths = _json_paths(self.fastapi.get("body"))
        return {
            "caseId": self.case_id,
            "method": self.method,
            "route": self.route,
            "spring": _safe_status(self.spring),
            "fastapi": _safe_status(self.fastapi),
            "missingJsonPaths": sorted(spring_paths - fastapi_paths),
            "additionalJsonPaths": sorted(fastapi_paths - spring_paths),
        }


def normalize_response(
    status: int,
    body: dict[str, Any],
    *,
    ignored_json_paths: list[str],
) -> dict[str, Any]:
    if set(body) != {"code", "message", "data"}:
        raise ValueError("response is not a Result envelope")
    normalized_body = copy.deepcopy(body)
    for path in ignored_json_paths:
        _remove_path(normalized_body, path.split("."))
    return {"httpStatus": status, "body": normalized_body}


def _remove_path(value: dict[str, Any], parts: list[str]) -> None:
    current: Any = value
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


def _json_paths(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        paths: set[str] = set()
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.add(child_prefix)
            paths.update(_json_paths(child, child_prefix))
        return paths
    if isinstance(value, list):
        paths = set()
        for child in value:
            paths.update(_json_paths(child, f"{prefix}[]"))
        return paths
    return set()


def _safe_status(observation: Mapping[str, Any]) -> dict[str, Any]:
    body = observation.get("body")
    code = body.get("code") if isinstance(body, dict) else None
    return {
        "httpStatus": observation.get("httpStatus"),
        "code": code,
    }


def collect_observation(
    response: httpx.Response,
    *,
    ignored_json_paths: list[str],
) -> dict[str, Any]:
    try:
        body = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"httpStatus": response.status_code, "errorCode": "INVALID_JSON_RESPONSE"}
    if not isinstance(body, dict):
        return {"httpStatus": response.status_code, "errorCode": "INVALID_RESULT_ENVELOPE"}
    try:
        return normalize_response(
            response.status_code,
            body,
            ignored_json_paths=ignored_json_paths,
        )
    except ValueError:
        return {"httpStatus": response.status_code, "errorCode": "INVALID_RESULT_ENVELOPE"}


def _validate_case_headers(case: Mapping[str, Any]) -> dict[str, str]:
    raw_headers = case.get("headers", {})
    if not isinstance(raw_headers, dict):
        raise ContractConfigurationError("case headers must be an object")
    headers = {str(key): str(value) for key, value in raw_headers.items()}
    if any(key.lower() == "authorization" for key in headers):
        raise ContractConfigurationError("authorization must come from the environment")
    return headers


def _validate_method(value: Any) -> str:
    if not isinstance(value, str) or value not in ALLOWED_METHODS:
        raise ContractConfigurationError("route method is invalid")
    return value


def _validate_route_path(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractConfigurationError("route path is invalid")
    parsed = urlsplit(value)
    decoded = unquote(value)
    if (
        not value.startswith("/api/")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path != value
        or decoded != value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded)
    ):
        raise ContractConfigurationError("route path is invalid")
    return value


def _validate_case(case: Mapping[str, Any]) -> str:
    required = {
        "id",
        "executionTarget",
        "method",
        "path",
        "headers",
        "query",
        "json",
        "expectedHttpStatus",
        "expectedCode",
        "ignoredJsonPaths",
        "sideEffect",
    }
    if not required <= set(case):
        raise ContractConfigurationError("case fields are incomplete")
    if not isinstance(case["id"], str) or not case["id"]:
        raise ContractConfigurationError("case id is invalid")
    if case["executionTarget"] not in {"dual", "fastapi", "testApp"}:
        raise ContractConfigurationError("case execution target is invalid")
    if not isinstance(case["query"], dict):
        raise ContractConfigurationError("case query must be an object")
    if type(case["sideEffect"]) is not bool:
        raise ContractConfigurationError("case sideEffect must be boolean")
    ignored = case["ignoredJsonPaths"]
    if not isinstance(ignored, list) or not all(isinstance(path, str) for path in ignored):
        raise ContractConfigurationError("ignoredJsonPaths must contain strings")
    _validate_case_headers(case)
    return f"{_validate_method(case['method'])} {_validate_route_path(case['path'])}"


async def _request_case(
    client: httpx.AsyncClient,
    case: Mapping[str, Any],
    *,
    token: str | None,
) -> dict[str, Any]:
    _validate_case(case)
    headers = _validate_case_headers(case)
    if case.get("requiresToken"):
        if not token:
            return {"httpStatus": None, "errorCode": "TOKEN_ENV_MISSING"}
        headers["Authorization"] = f"Bearer {token}"
    request_arguments: dict[str, Any] = {
        "headers": headers,
        "params": case.get("query", {}),
    }
    if case.get("requestBodyMode") == "invalidJson":
        request_arguments["content"] = b"{"
        headers["Content-Type"] = "application/json"
    elif case.get("json") is not None:
        request_arguments["json"] = case["json"]
    try:
        path = str(case["path"])
        request_url = path if client.base_url.is_absolute_url else f"http://contract.invalid{path}"
        response = await client.request(
            str(case["method"]),
            request_url,
            **request_arguments,
        )
    except httpx.HTTPError:
        return {"httpStatus": None, "errorCode": "NETWORK_ERROR"}
    ignored = case["ignoredJsonPaths"]
    return collect_observation(response, ignored_json_paths=ignored)


def _check_side_effect_gate(
    case: Mapping[str, Any],
    *,
    allow_side_effects: bool,
    isolated_database: bool,
) -> None:
    if case.get("sideEffect") and not (allow_side_effects and isolated_database):
        raise SideEffectRejected(
            "side-effect case requires --allow-side-effects and an isolated database"
        )


async def compare_case(
    case: dict[str, Any],
    spring_client: httpx.AsyncClient,
    fastapi_client: httpx.AsyncClient,
    *,
    owner: str = "fastapi",
    token: str | None = None,
    allow_side_effects: bool = False,
    isolated_database: bool = False,
) -> Comparison:
    if owner != "fastapi":
        raise RouteOwnershipError("dual comparison requires owner=fastapi")
    _check_side_effect_gate(
        case,
        allow_side_effects=allow_side_effects,
        isolated_database=isolated_database,
    )
    route_key = _validate_case(case)
    spring = await _request_case(spring_client, case, token=token)
    fastapi = await _request_case(fastapi_client, case, token=token)
    return Comparison(
        case_id=str(case["id"]),
        equal=spring == fastapi,
        spring=spring,
        fastapi=fastapi,
        method=route_key.partition(" ")[0],
        route=route_key.partition(" ")[2],
    )


async def execute_fastapi_case(
    case: dict[str, Any],
    fastapi_client: httpx.AsyncClient,
    *,
    token: str | None = None,
) -> dict[str, Any]:
    _check_side_effect_gate(case, allow_side_effects=False, isolated_database=False)
    observation = await _request_case(fastapi_client, case, token=token)
    body = observation.get("body")
    code = body.get("code") if isinstance(body, dict) else None
    expected_code = case.get("expectedCode")
    passed = observation.get("httpStatus") == case.get("expectedHttpStatus") and (
        expected_code is None or code == expected_code
    )
    return {
        "passed": passed,
        "httpStatus": observation.get("httpStatus"),
        "code": code,
    }


def _route_key(value: Mapping[str, Any]) -> str:
    return f"{_validate_method(value.get('method'))} {_validate_route_path(value.get('path'))}"


def _normalize_route_key(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractConfigurationError("ownership route is invalid")
    method, separator, path = value.partition(" ")
    if not separator or " " in path:
        raise ContractConfigurationError("ownership route is invalid")
    normalized = f"{_validate_method(method)} {_validate_route_path(path)}"
    if normalized != value:
        raise ContractConfigurationError("ownership route is invalid")
    return normalized


def _validate_contract(
    cases: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    ownership: dict[str, Any],
) -> dict[str, int]:
    if ownership.get("defaultOwner") != "spring":
        raise ContractConfigurationError("default route owner must be spring")
    raw_fastapi_routes = ownership.get("fastapiRoutes")
    raw_integration_gated_routes = ownership.get("integrationGatedRoutes", [])
    raw_operational_routes = ownership.get("operationalFastapiRoutes")
    if (
        not isinstance(raw_fastapi_routes, list)
        or not isinstance(raw_integration_gated_routes, list)
        or not isinstance(raw_operational_routes, list)
    ):
        raise ContractConfigurationError("ownership routes must be arrays")
    fastapi_route_values = [_normalize_route_key(value) for value in raw_fastapi_routes]
    integration_gated_values = [
        _normalize_route_key(value) for value in raw_integration_gated_routes
    ]
    operational_route_values = [_normalize_route_key(value) for value in raw_operational_routes]
    if operational_route_values != list(OPERATIONAL_ROUTES):
        raise ContractConfigurationError("operational routes must match the fixed health set")
    if len(fastapi_route_values) != len(set(fastapi_route_values)):
        raise ContractConfigurationError("fastapi business routes must be unique")
    if len(integration_gated_values) != len(set(integration_gated_values)):
        raise ContractConfigurationError("integration-gated routes must be unique")
    fastapi_routes = set(fastapi_route_values)
    integration_gated_routes = set(integration_gated_values)
    route_keys = [_route_key(route) for route in routes]
    if len(route_keys) != len(set(route_keys)):
        raise ContractConfigurationError("business routes must be unique")
    inventory = dict(zip(route_keys, routes, strict=True))
    if fastapi_routes - inventory.keys():
        raise ContractConfigurationError("fastapi ownership contains an unknown business route")
    if integration_gated_routes - fastapi_routes:
        raise ContractConfigurationError("integration-gated route is not FastAPI-owned")
    if any(type(route.get("sideEffect")) is not bool for route in routes):
        raise ContractConfigurationError("inventory sideEffect must be boolean")
    if any(
        route.get("owner") != ("fastapi" if route_key in fastapi_routes else "spring")
        for route_key, route in inventory.items()
    ):
        raise ContractConfigurationError("route owner disagrees with migration ownership")
    fastapi_integration_gated_routes = integration_gated_routes

    ids: set[str] = set()
    operational_counts: Counter[str] = Counter()
    test_app_counts: Counter[str] = Counter()
    business_counts: Counter[str] = Counter()
    unknown_count = 0

    for case in cases:
        route_key = _validate_case(case)
        case_id = case["id"]
        if case_id in ids:
            raise ContractConfigurationError("case ids must be unique")
        ids.add(case_id)
        target = case["executionTarget"]

        if case_id in TEST_APP_CASES:
            if route_key != TEST_APP_CASES[case_id] or target != "testApp" or case["sideEffect"]:
                raise ContractConfigurationError("test app cases must match the fixed whitelist")
            test_app_counts[case_id] += 1
            continue

        inventory_route = inventory.get(route_key)
        if inventory_route is not None:
            if target != "dual":
                raise ContractConfigurationError("business cases must use dual execution")
            if inventory_route["sideEffect"] or case["sideEffect"]:
                raise SideEffectRejected("business side effects are forbidden by the CLI contract")
            business_counts[route_key] += 1
            if business_counts[route_key] > 1:
                raise ContractConfigurationError("business cases must be unique")
            continue

        if route_key in OPERATIONAL_ROUTES:
            if target != "fastapi" or case["sideEffect"]:
                raise ContractConfigurationError("operational cases must be FastAPI read checks")
            operational_counts[route_key] += 1
            continue

        if route_key == UNKNOWN_ROUTE and case_id == "fastapi-unknown-route":
            if target != "fastapi" or case["sideEffect"]:
                raise ContractConfigurationError("unknown-route case must be a FastAPI read check")
            unknown_count += 1
            continue

        raise ContractConfigurationError("case route is outside the execution inventory")

    if not fastapi_routes <= business_counts.keys() | fastapi_integration_gated_routes:
        raise ContractConfigurationError(
            "each FastAPI business route requires a dual case or an integration gate"
        )
    if operational_counts != Counter(OPERATIONAL_ROUTES):
        raise ContractConfigurationError("each operational route requires exactly one case")
    if test_app_counts != Counter(TEST_APP_CASES.keys()):
        raise ContractConfigurationError("each test app case requires exactly one fixture")
    if unknown_count != 1:
        raise ContractConfigurationError("the fixed unknown-route case is required exactly once")
    return {
        "total": len(routes),
        "fastapi": len(fastapi_routes),
        "springSkipped": len(routes) - len(fastapi_routes),
        "fastapiIntegrationGated": len(fastapi_integration_gated_routes),
        "operationalFastapi": len(OPERATIONAL_ROUTES),
    }


def _safe_failed_comparison(case: Mapping[str, Any]) -> dict[str, Any]:
    route_key = _validate_case(case)
    return Comparison(
        case_id=str(case["id"]),
        equal=False,
        spring={"httpStatus": None},
        fastapi={"httpStatus": None},
        method=route_key.partition(" ")[0],
        route=route_key.partition(" ")[2],
    ).safe_difference()


def _emit_log(event: str, operation: str, result: str, duration_ms: int, **counts: int) -> None:
    document: dict[str, Any] = {
        "event": event,
        "module": "contract_compare",
        "operation": operation,
        "result": result,
        "durationMs": duration_ms,
    }
    document.update(counts)
    print(json.dumps(document, ensure_ascii=False, sort_keys=True), file=sys.stderr)


async def run_contract(
    cases: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    ownership: dict[str, Any],
    spring_client: httpx.AsyncClient,
    fastapi_client: httpx.AsyncClient,
    *,
    token: str | None = None,
    log_events: bool = False,
) -> dict[str, Any]:
    started = perf_counter()
    route_summary = _validate_contract(cases, routes, ownership)
    operational_routes = set(OPERATIONAL_ROUTES)
    case_summary = {
        "total": len(cases),
        "externalPassed": 0,
        "externalFailed": 0,
        "dualCompared": 0,
        "testAppSkipped": 0,
    }
    operational = {"total": len(operational_routes), "passed": 0, "failed": 0}
    differences: list[dict[str, Any]] = []
    owners = {_route_key(route): str(route["owner"]) for route in routes}

    for case in cases:
        case_started = perf_counter()
        target = case.get("executionTarget")
        route_key = _route_key(case)
        case_result = "skipped"
        if target == "testApp":
            case_summary["testAppSkipped"] += 1
        elif target == "fastapi":
            outcome = await execute_fastapi_case(case, fastapi_client, token=token)
            if outcome["passed"]:
                case_summary["externalPassed"] += 1
                case_result = "passed"
            else:
                case_summary["externalFailed"] += 1
                case_result = "failed"
                differences.append(_safe_failed_comparison(case))
            if route_key in operational_routes:
                operational["passed" if outcome["passed"] else "failed"] += 1
        elif target == "dual":
            owner = owners.get(route_key)
            if owner == "spring":
                case_result = "spring_skipped"
            else:
                comparison = await compare_case(
                    case,
                    spring_client,
                    fastapi_client,
                    owner=str(owner),
                    token=token,
                )
                case_summary["dualCompared"] += 1
                if comparison.equal:
                    case_summary["externalPassed"] += 1
                    case_result = "passed"
                else:
                    case_summary["externalFailed"] += 1
                    differences.append(comparison.safe_difference())
                    case_result = "failed"
        if log_events:
            _emit_log(
                "contract_case_completed",
                "execute_case",
                case_result,
                round((perf_counter() - case_started) * 1000),
                completedCaseCount=(
                    case_summary["externalPassed"]
                    + case_summary["externalFailed"]
                    + case_summary["testAppSkipped"]
                ),
                differenceCount=len(differences),
            )

    result = "failed" if differences else "passed"
    if log_events:
        _emit_log(
            "contract_comparison_completed",
            "run_contract",
            result,
            round((perf_counter() - started) * 1000),
            totalCaseCount=len(cases),
            passedCaseCount=case_summary["externalPassed"],
            failedCaseCount=case_summary["externalFailed"],
            skippedCaseCount=(case_summary["testAppSkipped"] + route_summary["springSkipped"]),
            differenceCount=len(differences),
        )
    return {
        "result": result,
        "routes": route_summary,
        "cases": case_summary,
        "operational": operational,
        "differences": differences,
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractConfigurationError("contract file cannot be loaded") from error


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Spring and FastAPI black-box contracts")
    parser.add_argument("--spring")
    parser.add_argument("--fastapi")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--ownership", type=Path, default=DEFAULT_OWNERSHIP)
    parser.add_argument("--allow-side-effects", action="store_true")
    return parser.parse_args(argv)


async def _run_cli(
    args: argparse.Namespace,
    environ: Mapping[str, str],
    transport: httpx.AsyncBaseTransport | None,
) -> dict[str, Any]:
    spring_base_url = args.spring or environ.get("SPRING_BASE_URL")
    fastapi_base_url = args.fastapi or environ.get("FASTAPI_BASE_URL")
    if not spring_base_url or not fastapi_base_url:
        raise ContractConfigurationError("both backend base URLs are required")
    if args.allow_side_effects:
        raise ContractConfigurationError("side effects are forbidden by the CLI contract")
    cases_document = _load_json(args.cases)
    cases = cases_document.get("cases") if isinstance(cases_document, dict) else None
    routes = _load_json(args.routes)
    ownership = _load_json(args.ownership)
    if (
        not isinstance(cases, list)
        or not isinstance(routes, list)
        or not isinstance(ownership, dict)
    ):
        raise ContractConfigurationError("contract documents have invalid shapes")
    token = environ.get(CREDENTIAL_ENV)
    async with httpx.AsyncClient(
        base_url=spring_base_url,
        transport=transport,
        timeout=10,
    ) as spring_client:
        async with httpx.AsyncClient(
            base_url=fastapi_base_url,
            transport=transport,
            timeout=10,
        ) as fastapi_client:
            return await run_contract(
                cases,
                routes,
                ownership,
                spring_client,
                fastapi_client,
                token=token,
                log_events=True,
            )


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    args = _parse_args(argv)
    active_environment = os.environ if environ is None else environ
    started = perf_counter()
    try:
        report = asyncio.run(_run_cli(args, active_environment, transport))
    except ContractConfigurationError:
        report = {
            "result": "failed",
            "errorCode": "CONTRACT_CONFIGURATION_ERROR",
            "differences": [],
        }
        _emit_log(
            "contract_comparison_failed",
            "main",
            "failed",
            round((perf_counter() - started) * 1000),
            differenceCount=0,
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
