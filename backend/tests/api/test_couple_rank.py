import os

from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.main import create_app


def settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET="x" * 64)  # noqa: S106


async def test_couple_rank_routes_require_authentication() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = (
            await client.get("/api/coupleRank/info"),
            await client.get("/api/coupleRank/rankList"),
            await client.get("/api/coupleRank/rewards"),
            await client.post("/api/coupleRank/claim/bronze"),
        )

    assert all(response.status_code == 401 for response in responses)
    assert all(response.json()["code"] == 401 for response in responses)


async def test_couple_rank_claim_requires_authentication_before_path_processing() -> None:
    app = create_app(settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/coupleRank/claim/not-a-rank")

    assert response.status_code == 401
    assert "not-a-rank" not in response.text
