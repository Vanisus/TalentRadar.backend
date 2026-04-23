# app/services/llm/client.py
import httpx
from app.config import settings


async def call_llm_service(vacancy_text: str, resume_text: str) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.LLM_SERVICE_URL}/api/v1/analyze",
            json={
                "vacancy_text": vacancy_text,
                "resume_text": resume_text,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def call_llm_parse_resume(resume_text: str) -> dict:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{settings.LLM_SERVICE_URL}/api/v1/parse-resume",
            json={"resume_text": resume_text},
        )
        resp.raise_for_status()
        return resp.json()