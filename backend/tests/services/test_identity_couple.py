from pathlib import Path

from services.identity_couple.app.main import create_app


def test_identity_couple_contract_routes_are_registered() -> None:
    app = create_app(jwt_secret="identity-test-secret-" + "x" * 64)
    paths = {route.path for route in app.routes}

    assert {
        "/health",
        "/api/user/login",
        "/api/user/profile",
        "/api/couple/generateCode",
        "/api/couple/bind",
    } <= paths


def test_identity_couple_does_not_expose_a_process_memory_store() -> None:
    source = (Path(__file__).parents[2] / "services/identity_couple/app/main.py").read_text(
        encoding="utf-8"
    )
    assert "users = {}" not in source
    assert "codes = {}" not in source
    assert "couples = {}" not in source
