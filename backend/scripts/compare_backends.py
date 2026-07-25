from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_CASES = BACKEND / "contracts/cases/foundation.json"
DEFAULT_ROUTES = BACKEND / "contracts/routes.json"
DEFAULT_OWNERSHIP = BACKEND / "contracts/migration-ownership.json"
CREDENTIAL_ENV = "CONTRACT_TEST_TOKEN"
ISOLATION_ENV = "CONTRACT_ISOLATED_DATABASE"


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
            "equal": self.equal,
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
        "errorCode": observation.get("errorCode"),
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


async def _request_case(
    client: httpx.AsyncClient,
    case: Mapping[str, Any],
    *,
    token: str | None,
) -> dict[str, Any]:
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
    ignored = case.get("ignoredJsonPaths", [])
    if not isinstance(ignored, list) or not all(isinstance(path, str) for path in ignored):
        raise ContractConfigurationError("ignoredJsonPaths must contain strings")
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
    spring = await _request_case(spring_client, case, token=token)
    fastapi = await _request_case(fastapi_client, case, token=token)
    return Comparison(
        case_id=str(case["id"]),
        equal=spring == fastapi,
        spring=spring,
        fastapi=fastapi,
        method=str(case["method"]),
        route=str(case["path"]),
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
        "errorCode": observation.get("errorCode"),
    }


def _route_key(value: Mapping[str, Any]) -> str:
    return f"{value['method']} {value['path']}"


def _route_summary(routes: list[dict[str, Any]], ownership: dict[str, Any]) -> dict[str, int]:
    fastapi_routes = set(ownership.get("fastapiRoutes", []))
    route_keys = {_route_key(route) for route in routes}
    unknown_fastapi = fastapi_routes - route_keys
    if unknown_fastapi:
        raise ContractConfigurationError("fastapi ownership contains an unknown business route")
    for route in routes:
        expected_owner = "fastapi" if _route_key(route) in fastapi_routes else "spring"
        if route.get("owner") != expected_owner:
            raise ContractConfigurationError("route owner disagrees with migration ownership")
    return {
        "total": len(routes),
        "fastapi": len(fastapi_routes),
        "springSkipped": len(routes) - len(fastapi_routes),
        "operationalFastapi": len(ownership.get("operationalFastapiRoutes", [])),
    }


def _safe_failed_comparison(case: Mapping[str, Any], error_code: str) -> dict[str, Any]:
    return Comparison(
        case_id=str(case["id"]),
        equal=False,
        spring={"httpStatus": None, "errorCode": error_code},
        fastapi={"httpStatus": None, "errorCode": error_code},
        method=str(case["method"]),
        route=str(case["path"]),
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
    allow_side_effects: bool = False,
    isolated_database: bool = False,
    log_events: bool = False,
) -> dict[str, Any]:
    started = perf_counter()
    route_summary = _route_summary(routes, ownership)
    operational_routes = set(ownership.get("operationalFastapiRoutes", []))
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
            try:
                outcome = await execute_fastapi_case(case, fastapi_client, token=token)
            except SideEffectRejected:
                outcome = {"passed": False, "errorCode": "SIDE_EFFECT_REJECTED"}
            if outcome["passed"]:
                case_summary["externalPassed"] += 1
                case_result = "passed"
            else:
                case_summary["externalFailed"] += 1
                case_result = "failed"
                differences.append(_safe_failed_comparison(case, str(outcome["errorCode"])))
            if route_key in operational_routes:
                operational["passed" if outcome["passed"] else "failed"] += 1
        elif target == "dual":
            owner = owners.get(route_key)
            if owner is None:
                case_summary["externalFailed"] += 1
                case_result = "failed"
                differences.append(_safe_failed_comparison(case, "UNKNOWN_ROUTE"))
            elif owner == "spring":
                case_result = "spring_skipped"
            else:
                try:
                    comparison = await compare_case(
                        case,
                        spring_client,
                        fastapi_client,
                        owner=owner,
                        token=token,
                        allow_side_effects=allow_side_effects,
                        isolated_database=isolated_database,
                    )
                except SideEffectRejected:
                    differences.append(_safe_failed_comparison(case, "SIDE_EFFECT_REJECTED"))
                    case_summary["externalFailed"] += 1
                    case_result = "rejected"
                else:
                    case_summary["dualCompared"] += 1
                    if comparison.equal:
                        case_summary["externalPassed"] += 1
                        case_result = "passed"
                    else:
                        case_summary["externalFailed"] += 1
                        differences.append(comparison.safe_difference())
                        case_result = "failed"
        else:
            case_summary["externalFailed"] += 1
            case_result = "failed"
            differences.append(_safe_failed_comparison(case, "UNKNOWN_EXECUTION_TARGET"))
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
    isolated_database = environ.get(ISOLATION_ENV, "").lower() in {"1", "true", "yes"}
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
                allow_side_effects=bool(args.allow_side_effects),
                isolated_database=isolated_database,
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
