from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

import httpx
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response
from pydantic import BaseModel

from app.core.auth import current_user_id
from app.core.errors import install_exception_handlers
from scripts.compare_backends import (
    RouteOwnershipError,
    SideEffectRejected,
    collect_observation,
    compare_case,
    execute_fastapi_case,
    main,
    normalize_response,
    run_contract,
)

BACKEND = Path(__file__).parents[2]
FOUNDATION = BACKEND / "contracts/cases/foundation.json"
ROUTES = BACKEND / "contracts/routes.json"
OWNERSHIP = BACKEND / "contracts/migration-ownership.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def result_response(*, status: int = 200, code: int = 200, data: Any = None) -> Response:
    return Response(
        status,
        json={"code": code, "message": "操作成功", "data": data},
    )


def dual_case(**overrides: Any) -> dict[str, Any]:
    case: dict[str, Any] = {
        "id": "read-demo",
        "executionTarget": "dual",
        "method": "GET",
        "path": "/api/demo",
        "headers": {},
        "query": {},
        "json": None,
        "expectedHttpStatus": 200,
        "expectedCode": 200,
        "ignoredJsonPaths": [],
        "sideEffect": False,
    }
    case.update(overrides)
    return case


def test_response_normalization_preserves_contract_fields() -> None:
    body = {"code": 200, "message": "操作成功", "data": {"id": 1}}

    normalized = normalize_response(
        200,
        body,
        ignored_json_paths=["data.createTime"],
    )

    assert normalized == {
        "httpStatus": 200,
        "body": {"code": 200, "message": "操作成功", "data": {"id": 1}},
    }
    assert normalized["body"] is not body


def test_response_normalization_deep_copies_and_removes_ignored_paths() -> None:
    body: dict[str, Any] = {
        "code": 200,
        "message": "操作成功",
        "data": {"profile": {"name": "safe", "updatedAt": "dynamic"}},
    }

    normalized = normalize_response(
        200,
        body,
        ignored_json_paths=["data.profile.updatedAt", "data.missing"],
    )

    assert normalized["body"]["data"] == {"profile": {"name": "safe"}}
    assert body["data"]["profile"]["updatedAt"] == "dynamic"


def test_normalization_rejects_non_result_body() -> None:
    with pytest.raises(ValueError, match="Result envelope"):
        normalize_response(422, {"detail": []}, ignored_json_paths=[])


def test_response_json_parse_failure_becomes_safe_observation() -> None:
    response = Response(502, content=b"private upstream body is not json")

    observation = collect_observation(response, ignored_json_paths=[])

    assert observation == {"httpStatus": 502, "errorCode": "INVALID_JSON_RESPONSE"}
    assert "private" not in json.dumps(observation)


async def test_compare_case_reports_equal_dual_implementation() -> None:
    async def handler(_: Request) -> Response:
        return result_response(data={"id": 1})

    async with AsyncClient(transport=MockTransport(handler)) as spring_client:
        async with AsyncClient(transport=MockTransport(handler)) as fastapi_client:
            comparison = await compare_case(
                dual_case(),
                spring_client,
                fastapi_client,
                owner="fastapi",
            )

    assert comparison.equal is True
    assert comparison.spring == comparison.fastapi


async def test_compare_case_reports_unequal_without_exposing_response_data() -> None:
    async def handler(request: Request) -> Response:
        if request.url.host == "spring.invalid":
            return result_response(data={"id": 1, "private": "spring-secret"})
        return result_response(data={"id": 2, "private": "fastapi-secret"})

    async with AsyncClient(
        transport=MockTransport(handler), base_url="http://spring.invalid"
    ) as spring_client:
        async with AsyncClient(
            transport=MockTransport(handler), base_url="http://fastapi.invalid"
        ) as fastapi_client:
            comparison = await compare_case(
                dual_case(ignoredJsonPaths=["data.private"]),
                spring_client,
                fastapi_client,
                owner="fastapi",
            )

    assert comparison.equal is False
    serialized = json.dumps(comparison.safe_difference(), ensure_ascii=False)
    assert "spring-secret" not in serialized
    assert "fastapi-secret" not in serialized
    assert set(comparison.safe_difference()) == {
        "caseId",
        "method",
        "route",
        "equal",
        "spring",
        "fastapi",
        "missingJsonPaths",
        "additionalJsonPaths",
    }


async def test_compare_case_refuses_spring_owned_route_without_requests() -> None:
    request_count = 0

    async def handler(_: Request) -> Response:
        nonlocal request_count
        request_count += 1
        return result_response()

    async with AsyncClient(transport=MockTransport(handler)) as spring_client:
        async with AsyncClient(transport=MockTransport(handler)) as fastapi_client:
            with pytest.raises(RouteOwnershipError, match="owner=fastapi"):
                await compare_case(dual_case(), spring_client, fastapi_client, owner="spring")

    assert request_count == 0


@pytest.mark.parametrize(
    ("allow_side_effects", "isolated_database"),
    [(False, False), (True, False), (False, True)],
)
async def test_side_effect_case_requires_flag_and_isolated_database(
    allow_side_effects: bool,
    isolated_database: bool,
) -> None:
    request_count = 0

    async def handler(_: Request) -> Response:
        nonlocal request_count
        request_count += 1
        return result_response()

    async with AsyncClient(transport=MockTransport(handler)) as spring_client:
        async with AsyncClient(transport=MockTransport(handler)) as fastapi_client:
            with pytest.raises(SideEffectRejected, match="isolated"):
                await compare_case(
                    dual_case(sideEffect=True),
                    spring_client,
                    fastapi_client,
                    owner="fastapi",
                    allow_side_effects=allow_side_effects,
                    isolated_database=isolated_database,
                )

    assert request_count == 0


async def test_side_effect_case_runs_only_with_both_gates() -> None:
    request_count = 0

    async def handler(_: Request) -> Response:
        nonlocal request_count
        request_count += 1
        return result_response()

    async with AsyncClient(transport=MockTransport(handler)) as spring_client:
        async with AsyncClient(transport=MockTransport(handler)) as fastapi_client:
            comparison = await compare_case(
                dual_case(sideEffect=True),
                spring_client,
                fastapi_client,
                owner="fastapi",
                allow_side_effects=True,
                isolated_database=True,
            )

    assert comparison.equal is True
    assert request_count == 2


class ContractPayload(BaseModel):
    quantity: int


def contract_test_app() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/__contract/protected")
    async def protected(_: int = Depends(current_user_id)) -> dict[str, Any]:
        return {"code": 200, "message": "操作成功", "data": None}

    @app.post("/__contract/validate")
    async def validate(payload: ContractPayload) -> dict[str, Any]:
        return {"code": 200, "message": "操作成功", "data": payload.model_dump()}

    return app


@pytest.mark.parametrize(
    "case_id",
    ["test-app-no-token", "test-app-invalid-json", "test-app-invalid-field"],
)
async def test_test_app_only_cases_reuse_foundation_document(case_id: str) -> None:
    cases = load_json(FOUNDATION)["cases"]
    case = next(item for item in cases if item["id"] == case_id)
    assert case["executionTarget"] == "testApp"

    async with AsyncClient(
        transport=ASGITransport(app=contract_test_app()), base_url="http://test"
    ) as client:
        outcome = await execute_fastapi_case(case, client)

    assert outcome["passed"] is True
    assert outcome["httpStatus"] == case["expectedHttpStatus"]
    assert outcome["code"] == case["expectedCode"]


async def test_real_fastapi_self_check_counts_operational_and_test_app_cases() -> None:
    from app.core.config import Settings
    from app.main import create_app

    settings = Settings(
        _env_file=None,
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET="x" * 64,  # noqa: S106
    )
    app = create_app(settings)
    cases = load_json(FOUNDATION)["cases"]
    routes = load_json(ROUTES)
    ownership = load_json(OWNERSHIP)

    async with AsyncClient(
        transport=MockTransport(lambda _: result_response()),
        base_url="http://spring.invalid",
    ) as spring_client:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://fastapi.test"
        ) as fastapi_client:
            report = await run_contract(
                cases,
                routes,
                ownership,
                spring_client,
                fastapi_client,
            )

    assert report["result"] == "passed"
    assert report["routes"] == {
        "total": 193,
        "fastapi": 0,
        "springSkipped": 193,
        "operationalFastapi": 3,
    }
    assert report["cases"] == {
        "total": 7,
        "externalPassed": 4,
        "externalFailed": 0,
        "dualCompared": 0,
        "testAppSkipped": 3,
    }
    assert report["operational"] == {"total": 3, "passed": 3, "failed": 0}


async def test_network_failure_is_safe_and_does_not_leak_error_text() -> None:
    unsafe_error_text = "network-secret-must-not-leak"

    async def spring_handler(request: Request) -> Response:
        raise httpx.ConnectError(unsafe_error_text, request=request)

    async def fastapi_handler(_: Request) -> Response:
        return result_response()

    async with AsyncClient(transport=MockTransport(spring_handler)) as spring_client:
        async with AsyncClient(transport=MockTransport(fastapi_handler)) as fastapi_client:
            comparison = await compare_case(
                dual_case(),
                spring_client,
                fastapi_client,
                owner="fastapi",
            )

    serialized = json.dumps(comparison.safe_difference())
    assert comparison.equal is False
    assert comparison.spring == {"httpStatus": None, "errorCode": "NETWORK_ERROR"}
    assert unsafe_error_text not in serialized


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_cli_injects_token_from_env_and_emits_safe_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    credential_value = "token-value-that-must-never-appear-anywhere"
    cases_path = tmp_path / "cases.json"
    routes_path = tmp_path / "routes.json"
    ownership_path = tmp_path / "ownership.json"
    write_json(cases_path, {"version": 1, "cases": [dual_case(requiresToken=True)]})
    write_json(
        routes_path,
        [
            {
                "method": "GET",
                "path": "/api/demo",
                "controller": "DemoController",
                "sideEffect": False,
                "owner": "fastapi",
                "migrationBatch": 1,
            }
        ],
    )
    write_json(
        ownership_path,
        {
            "defaultOwner": "spring",
            "fastapiRoutes": ["GET /api/demo"],
            "operationalFastapiRoutes": [],
        },
    )

    async def handler(request: Request) -> Response:
        assert request.headers["Authorization"] == f"Bearer {credential_value}"
        return result_response(data={"private": "never-serialize-complete-data"})

    exit_code = main(
        [
            "--spring",
            "http://spring.invalid",
            "--fastapi",
            "http://fastapi.invalid",
            "--cases",
            str(cases_path),
            "--routes",
            str(routes_path),
            "--ownership",
            str(ownership_path),
        ],
        environ={"CONTRACT_TEST_TOKEN": credential_value},
        transport=MockTransport(handler),
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert exit_code == 0
    assert json.loads(captured.out)["result"] == "passed"
    assert credential_value not in output
    assert "never-serialize-complete-data" not in output
    assert "Authorization" not in output


def test_cli_returns_failure_with_only_allowlisted_difference_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cases_path = tmp_path / "cases.json"
    routes_path = tmp_path / "routes.json"
    ownership_path = tmp_path / "ownership.json"
    write_json(cases_path, {"version": 1, "cases": [dual_case()]})
    write_json(
        routes_path,
        [
            {
                "method": "GET",
                "path": "/api/demo",
                "controller": "DemoController",
                "sideEffect": False,
                "owner": "fastapi",
                "migrationBatch": 1,
            }
        ],
    )
    write_json(
        ownership_path,
        {
            "defaultOwner": "spring",
            "fastapiRoutes": ["GET /api/demo"],
            "operationalFastapiRoutes": [],
        },
    )

    async def handler(request: Request) -> Response:
        identifier = 1 if request.url.host == "spring.invalid" else 2
        return result_response(data={"id": identifier, "private": "do-not-print"})

    exit_code = main(
        [
            "--spring",
            "http://spring.invalid",
            "--fastapi",
            "http://fastapi.invalid",
            "--cases",
            str(cases_path),
            "--routes",
            str(routes_path),
            "--ownership",
            str(ownership_path),
        ],
        environ={},
        transport=MockTransport(handler),
    )

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 1
    assert document["result"] == "failed"
    assert len(document["differences"]) == 1
    assert set(document["differences"][0]) == {
        "caseId",
        "method",
        "route",
        "equal",
        "spring",
        "fastapi",
        "missingJsonPaths",
        "additionalJsonPaths",
    }
    assert "do-not-print" not in captured.out + captured.err
