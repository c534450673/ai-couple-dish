import json
from pathlib import Path

BACKEND = Path(__file__).parents[2]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_each_route_has_exactly_one_owner() -> None:
    document = load_json(BACKEND / "contracts/migration-ownership.json")
    assert isinstance(document, dict)
    assert document["defaultOwner"] == "spring"
    assert document["fastapiRoutes"] == []
    assert document["operationalFastapiRoutes"] == [
        "GET /api/health/live",
        "GET /api/health/ready",
        "GET /api/actuator/health",
    ]
    all_routes = document["fastapiRoutes"] + document["operationalFastapiRoutes"]
    assert len(all_routes) == len(set(all_routes))


def test_all_193_business_routes_remain_spring_owned_and_skipped() -> None:
    routes = load_json(BACKEND / "contracts/routes.json")
    ownership = load_json(BACKEND / "contracts/migration-ownership.json")
    assert isinstance(routes, list)
    assert isinstance(ownership, dict)

    route_keys = {f"{route['method']} {route['path']}" for route in routes}
    fastapi_routes = set(ownership["fastapiRoutes"])

    assert len(routes) == 193
    assert len(route_keys) == 193
    assert all(route["owner"] == "spring" for route in routes)
    assert fastapi_routes.isdisjoint(route_keys)
    assert len(route_keys - fastapi_routes) == 193


def test_foundation_cases_have_required_safe_fields() -> None:
    document = load_json(BACKEND / "contracts/cases/foundation.json")
    assert isinstance(document, dict)
    cases = document["cases"]
    required = {
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

    assert len(cases) == 7
    assert len({case["id"] for case in cases}) == 7
    assert all(required <= set(case) for case in cases)
    assert all(case["sideEffect"] is False for case in cases)
    assert all(case["headers"] == {} for case in cases)
    assert {case["id"] for case in cases if case["executionTarget"] == "testApp"} == {
        "test-app-no-token",
        "test-app-invalid-json",
        "test-app-invalid-field",
    }
