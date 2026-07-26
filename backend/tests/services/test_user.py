from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.errors import BusinessError
from app.db.models import User
from app.schemas.business import PhoneLoginRequest
from app.services import user as user_service

PHONE = "13800138000"
CODE = "123456"


class FakeRedis:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.locks: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return CODE if key == f"user:verify:code:{PHONE}" else None

    async def delete(self, key: str) -> None:
        self.deleted.append(key)

    async def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool:
        del ex
        if nx and key in self.locks:
            return False
        self.locks[key] = value
        return True

    async def eval(self, _script: str, _count: int, key: str, value: str) -> int:
        if self.locks.get(key) == value:
            del self.locks[key]
            return 1
        return 0


def request_context(redis: FakeRedis) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                redis=SimpleNamespace(raw=redis),
                settings=Settings(
                    **{"_env_file": None, "DB_PASSWORD": "db-secret", "JWT_SECRET": "x" * 64}
                ),
            )
        ),
    )


def request_payload() -> PhoneLoginRequest:
    return PhoneLoginRequest(phone=PHONE, verifyCode=CODE)


async def test_invalid_phone_does_not_create_operation_lock() -> None:
    redis = FakeRedis()
    payload = PhoneLoginRequest.model_construct(phone="123", verify_code=CODE)

    with pytest.raises(BusinessError) as error:
        await user_service.phone_login(request_context(redis), object(), payload)

    assert error.value.code == 1004
    assert redis.locks == {}


async def test_existing_user_registration_does_not_consume_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    monkeypatch.setattr(
        user_service,
        "_find_user",
        AsyncMock(return_value=User(id=7, phone=PHONE, is_deleted=0)),
    )

    with pytest.raises(BusinessError) as error:
        await user_service.register_by_phone(request_context(redis), object(), request_payload())

    assert error.value.code == 1005
    assert redis.deleted == []
    assert redis.locks == {}


async def test_unknown_user_login_keeps_code_for_registration_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    monkeypatch.setattr(user_service, "_find_user", AsyncMock(return_value=None))

    with pytest.raises(BusinessError) as error:
        await user_service.phone_login(request_context(redis), object(), request_payload())

    assert error.value.code == 1006
    assert redis.deleted == []
    assert redis.locks == {}


async def test_successful_phone_registration_consumes_code_after_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    new_user = User(id=8, openid=f"phone_{PHONE}", phone=PHONE, is_deleted=0)
    monkeypatch.setattr(user_service, "_find_user", AsyncMock(return_value=None))
    monkeypatch.setattr(user_service, "_commit_new_user", AsyncMock(return_value=new_user))

    response = await user_service.register_by_phone(
        request_context(redis), object(), request_payload()
    )

    assert response["userInfo"]["id"] == 8
    assert redis.deleted == [f"user:verify:code:{PHONE}", f"user:verify:expire:{PHONE}"]
    assert redis.locks == {}


async def test_concurrent_phone_operation_cannot_reuse_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    redis.locks[f"lock:user:phone:{PHONE}"] = "first-operation"
    find_user = AsyncMock(return_value=User(id=7, phone=PHONE, is_deleted=0))
    monkeypatch.setattr(user_service, "_find_user", find_user)

    with pytest.raises(BusinessError) as error:
        await user_service.phone_login(request_context(redis), object(), request_payload())

    assert error.value.code == 9005
    assert find_user.await_count == 0
    assert redis.deleted == []
    assert redis.locks == {f"lock:user:phone:{PHONE}": "first-operation"}
