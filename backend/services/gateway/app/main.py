from fastapi import FastAPI

app = FastAPI(title="AI Couple Dish Gateway")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}
