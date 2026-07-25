import pytest

from app.core.errors import BusinessError
from app.core.passwords import hash_password, verify_password


def test_bcrypt_hash_never_contains_plaintext() -> None:
    password = "correct horse battery staple"  # noqa: S105
    encoded = hash_password(password)
    assert encoded.startswith("$2")
    assert "correct horse" not in encoded
    assert verify_password(password, encoded)
    assert not verify_password("wrong", encoded)


def test_hash_password_uses_bcrypt_cost_12() -> None:
    encoded = hash_password("valid-password")
    assert encoded.split("$")[2] == "12"


@pytest.mark.parametrize("password", ["", "a" * 73, "界" * 25])
def test_hash_password_rejects_empty_or_more_than_72_utf8_bytes(password: str) -> None:
    with pytest.raises(BusinessError) as caught:
        hash_password(password)
    assert caught.value.code == 400
    assert caught.value.http_status == 400
    if password:
        assert password not in caught.value.message


def test_hash_password_accepts_exactly_72_utf8_bytes() -> None:
    password = "界" * 24
    assert verify_password(password, hash_password(password))


@pytest.mark.parametrize(
    ("password", "encoded_hash"),
    [
        ("valid-password", "damaged-hash"),
        ("a" * 73, "$2b$12$invalid-but-ascii"),
        ("valid-password", "哈希"),
    ],
)
def test_verify_password_returns_false_for_invalid_input(
    password: str, encoded_hash: str
) -> None:
    assert verify_password(password, encoded_hash) is False
