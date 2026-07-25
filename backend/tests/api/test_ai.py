from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.errors import BusinessError
from app.schemas.business import AiGenerateRequest
from app.services import ai as ai_service


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> bool:
        self.values[key] = value
        self.expirations[key] = ex
        return True

    async def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


class FakeGateway:
    async def complete(self, messages: list[dict[str, object]], tools: object = None) -> dict[str, object]:
        return {"choices": [{"message": {"content": "ignored"}}]}

    async def stream(self, messages: list[dict[str, object]]):
        yield "你好"
        yield "，情侣。"


def request_context(gateway: object | None = None) -> SimpleNamespace:
    settings = Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)
    state = SimpleNamespace(redis=SimpleNamespace(raw=FakeRedis()), settings=settings)
    if gateway is not None:
        state.ai_gateway = gateway
    return SimpleNamespace(state=SimpleNamespace(request_id="request-1"), app=SimpleNamespace(state=state))


@pytest.mark.asyncio
async def test_chat_stream_emits_contract_events_and_scopes_session() -> None:
    request = request_context(FakeGateway())
    events = [
        event
        async for event in ai_service.chat_stream(request, object(), 7, "今天吃什么", None)  # type: ignore[arg-type]
    ]

    assert events[0].startswith("event: token\ndata: \"你好\"")
    assert "event: session\ndata: \"u7-" in events[-2]
    assert events[-1] == "event: done\ndata: {}\n\n"
    assert all("Authorization" not in event for event in events)
    redis = request.app.state.redis.raw
    assert any(key.startswith("ai:session:msg:7:u7-") for key in redis.values)
    assert not any(key.startswith("ai:session:msg:8:") for key in redis.values)


@pytest.mark.asyncio
async def test_session_store_rejects_key_injection() -> None:
    with pytest.raises(BusinessError) as error:
        ai_service.AiSessionStore.resolve(7, "other:user")
    assert error.value.code == 400


@pytest.mark.asyncio
async def test_generate_rejects_non_json_without_leaking_prompt() -> None:
    class InvalidGateway(FakeGateway):
        async def complete(self, messages: list[dict[str, object]], tools: object = None) -> dict[str, object]:
            return {"choices": [{"message": {"content": "not-json"}}]}

    request = request_context(InvalidGateway())
    with pytest.raises(BusinessError) as error:
        await ai_service.generate(request, 7, AiGenerateRequest(type="menu", prompt="私密提示词"))
    assert error.value.code == 9005
    assert "私密提示词" not in str(error.value)
