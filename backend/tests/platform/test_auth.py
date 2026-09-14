import pytest

from packages.platform.auth import decode_token, issue_user_token


def test_user_jwt_contains_required_claims() -> None:
    token = issue_user_token(user_id=42, secret="x" * 64, expires_ms=60_000)
    claims = decode_token(token, secret="x" * 64)
    assert claims["sub"] == "42"
    assert claims["userId"] == 42
    assert claims["jti"]


def test_short_secret_is_rejected() -> None:
    with pytest.raises(ValueError):
        issue_user_token(user_id=1, secret="short", expires_ms=1000)
