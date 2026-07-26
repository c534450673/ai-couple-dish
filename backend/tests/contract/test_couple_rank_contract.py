import json
from pathlib import Path

BACKEND = Path(__file__).parents[2]


def test_couple_rank_routes_match_spring_contract_and_remain_spring_owned() -> None:
    routes = json.loads((BACKEND / "contracts/routes.json").read_text(encoding="utf-8"))
    ownership = json.loads(
        (BACKEND / "contracts/migration-ownership.json").read_text(encoding="utf-8")
    )
    expected = {
        "GET /api/coupleRank/info": True,
        "GET /api/coupleRank/rankList": False,
        "GET /api/coupleRank/rewards": True,
        "POST /api/coupleRank/claim/{rank}": True,
    }
    selected = {
        f"{item['method']} {item['path']}": item["sideEffect"]
        for item in routes
        if item["controller"] == "CoupleRankController"
    }
    assert selected == expected
    assert not set(expected).intersection(ownership["fastapiRoutes"])
