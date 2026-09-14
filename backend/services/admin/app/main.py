from fastapi import FastAPI

app = FastAPI(title="Admin Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "admin"}
