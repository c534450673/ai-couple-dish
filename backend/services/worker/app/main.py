from fastapi import FastAPI

app = FastAPI(title="Worker Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "worker"}
