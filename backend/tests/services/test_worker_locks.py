import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from services.worker.app.main import InMemoryLease, create_app


@pytest.mark.asyncio
async def test_worker_requires_enabled_and_rejects_duplicate_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_TRIGGER_TOKEN", "internal-only")
    entered = asyncio.Event()
    complete = asyncio.Event()

    async def job() -> None:
        entered.set()
        await complete.wait()

    app = create_app(enabled=True, lock_backend=InMemoryLease(), handlers={"reports": job})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = asyncio.create_task(
            client.post(
                "/api/worker/run",
                json={"job": "reports"},
                headers={"X-Worker-Token": "internal-only"},
            )
        )
        await entered.wait()
        duplicate = await client.post(
            "/api/worker/run", json={"job": "reports"}, headers={"X-Worker-Token": "internal-only"}
        )
        assert duplicate.status_code == 409
        complete.set()
        assert (await first).status_code == 200
        assert (
            await client.post(
                "/api/worker/run",
                json={"job": "reports"},
                headers={"X-Worker-Token": "internal-only"},
            )
        ).status_code == 200


def test_worker_without_trigger_token_cannot_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv("WORKER_TRIGGER_TOKEN", "internal-only")
    app = create_app(
        enabled=True, lock_backend=InMemoryLease(), handlers={"reports": lambda: asyncio.sleep(0)}
    )
    assert TestClient(app).post("/api/worker/run", json={"job": "reports"}).status_code == 403
