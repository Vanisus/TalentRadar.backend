# app/api/v1.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.model import infer

router = APIRouter()


class AnalyzeRequest(BaseModel):
    vacancy_text: str
    resume_text: str


class AnalyzeResponse(BaseModel):
    raw_output: str
    score: float | None = None


def extract_score(raw: str) -> float | None:
    """
    Парсим первую строку 'Оценка: X.XX' и достаём число.
    """
    import re

    first_line = raw.splitlines()[0] if raw else ""
    m = re.search(r"Оценка:\s*([01](?:\.\d{1,2})?)", first_line)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
        # safety clip
        return max(0.0, min(1.0, val))
    except ValueError:
        return None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    text = infer(req.vacancy_text, req.resume_text)
    score = extract_score(text)
    return AnalyzeResponse(raw_output=text, score=score)