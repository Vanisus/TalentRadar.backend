# app/main.py
from fastapi import FastAPI
from app.api.v1 import router as api_router

app = FastAPI(title="TalentRadar LLM Service")

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}