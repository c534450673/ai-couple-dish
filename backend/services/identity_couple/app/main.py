from fastapi import FastAPI

app = FastAPI(title="Identity Couple Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "identity_couple"}
