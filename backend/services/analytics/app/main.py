from fastapi import FastAPI

app = FastAPI(title="Analytics Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytics"}
