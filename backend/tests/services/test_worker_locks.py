from fastapi.testclient import TestClient

from services.worker.app.main import create_app


def test_worker_requires_enabled_and_rejects_duplicate_lock() -> None:
    client = TestClient(create_app(enabled=True))
    first = client.post("/api/worker/run", json={"job": "reports"})
    assert first.status_code == 200
    second = client.post("/api/worker/run", json={"job": "reports"})
    assert second.status_code == 409
