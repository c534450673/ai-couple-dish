import json
from pathlib import Path

BACKEND = Path(__file__).parents[2]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_each_route_has_exactly_one_owner() -> None:
    document = load_json(BACKEND / "contracts/migration-ownership.json")
    assert isinstance(document, dict)
    assert document["defaultOwner"] == "spring"
    assert document["fastapiRoutes"] == [
        "POST /api/challenge/accept/{challengeId}",
        "POST /api/challenge/cancel/{challengeId}",
        "POST /api/challenge/checkin",
        "GET /api/challenge/checkin-records/{challengeId}",
        "POST /api/challenge/create",
        "GET /api/challenge/detail/{challengeId}",
        "GET /api/challenge/list",
        "GET /api/challenge/pending",
        "POST /api/challenge/reject/{challengeId}",
        "POST /api/couple/bind",
        "GET /api/couple/codeInfo",
        "POST /api/couple/generateCode",
        "GET /api/couple/home",
        "GET /api/couple/info",
        "GET /api/couple/loveTimer",
        "POST /api/couple/recover",
        "GET /api/couple/recoverable",
        "POST /api/couple/refreshCode",
        "POST /api/couple/unbind/apply",
        "POST /api/couple/unbind/confirm",
        "POST /api/couple/unbind/reject",
        "GET /api/couple/validateCode",
        "POST /api/heartMoment/create",
        "DELETE /api/heartMoment/delete/{id}",
        "GET /api/heartMoment/list",
        "GET /api/heartMoment/random",
        "GET /api/mood/detail/{id}",
        "GET /api/mood/history",
        "POST /api/mood/read/{id}",
        "POST /api/mood/send",
        "GET /api/mood/stats",
        "GET /api/mood/today",
        "GET /api/mood/types",
        "GET /api/mood/unread/count",
        "DELETE /api/notification/delete/{id}",
        "GET /api/notification/list",
        "PUT /api/notification/read/{id}",
        "PUT /api/notification/readAll",
        "GET /api/notification/unreadCount",
        "POST /api/sweetBomb/answer/{id}",
        "GET /api/sweetBomb/detail/{id}",
        "POST /api/sweetBomb/generate",
        "GET /api/sweetBomb/history",
        "POST /api/sweetBomb/read/{id}",
        "GET /api/sweetBomb/unread",
        "GET /api/sweetBomb/unread/count",
        "POST /api/timeCapsule/create",
        "DELETE /api/timeCapsule/delete/{id}",
        "GET /api/timeCapsule/detail/{id}",
        "GET /api/timeCapsule/list",
        "GET /api/timeCapsule/pending",
        "POST /api/timeCapsule/unlock/{id}",
        "GET /api/user/info",
        "POST /api/user/login",
        "POST /api/user/logout",
        "POST /api/user/phoneLogin",
        "POST /api/user/register",
        "POST /api/user/sendCode",
        "PUT /api/user/update",
        "POST /api/wish/add",
        "DELETE /api/wish/delete/{id}",
        "GET /api/wish/detail/{id}",
        "POST /api/wish/fulfill/{id}",
        "GET /api/wish/list",
        "POST /api/wish/unfulfill/{id}",
        "PUT /api/wish/update/{id}",
    ]
    assert document["cutoverBatches"] == {
        "user-couple-notification-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "batch-1-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "wish-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "wish-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "heart-moment-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "heart-moment-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "challenge-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "challenge-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "mood-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "mood-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "time-capsule-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "time-capsule-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
        "sweet-bomb-v1": {
            "activeOwner": "fastapi",
            "rollbackOwner": "spring",
            "nginxLocation": "sweet-bomb-exact-contract-regex",
            "requires": [
                "real-mysql-redis-gates",
                "contract-route-owner-check",
                "nginx-config-check",
            ],
        },
    }
    assert document["integrationGatedRoutes"] == document["fastapiRoutes"]
    assert document["operationalFastapiRoutes"] == [
        "GET /api/health/live",
        "GET /api/health/ready",
        "GET /api/actuator/health",
    ]
    all_routes = document["fastapiRoutes"] + document["operationalFastapiRoutes"]
    assert len(all_routes) == len(set(all_routes))


def test_business_routes_have_one_declared_owner() -> None:
    routes = load_json(BACKEND / "contracts/routes.json")
    ownership = load_json(BACKEND / "contracts/migration-ownership.json")
    assert isinstance(routes, list)
    assert isinstance(ownership, dict)

    route_keys = {f"{route['method']} {route['path']}" for route in routes}
    fastapi_routes = set(ownership["fastapiRoutes"])

    assert len(routes) == 193
    assert len(route_keys) == 193
    assert fastapi_routes <= route_keys
    assert {route["owner"] for route in routes} == {"spring", "fastapi"}
    fastapi_route_keys = {
        f"{route['method']} {route['path']}"
        for route in routes
        if route["owner"] == "fastapi"
    }
    assert fastapi_route_keys == fastapi_routes
    assert len(route_keys - fastapi_routes) == 127


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
    unknown = next(case for case in cases if case["id"] == "fastapi-unknown-route")
    assert (unknown["method"], unknown["path"], unknown["executionTarget"]) == (
        "GET",
        "/api/__contract_unknown__",
        "fastapi",
    )
