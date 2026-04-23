# app/api/v1.py
import json
import re

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


class ParseResumeRequest(BaseModel):
    resume_text: str

class ParseResumeResponse(BaseModel):
    raw_output: str
    parsed_json: dict | None = None


def extract_score(raw: str) -> float | None:
    first_line = raw.splitlines()[0] if raw else ""
    m = re.search(r"Оценка:\s*([01](?:[.,]\d{1,2})?)", first_line)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
        return max(0.0, min(1.0, val))
    except ValueError:
        return None


def extract_json(raw: str) -> dict | None:
    if not raw:
        return None

    raw = raw.strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    text = infer(req.vacancy_text, req.resume_text)
    score = extract_score(text)
    return AnalyzeResponse(raw_output=text, score=score)


@router.post("/parse-resume", response_model=ParseResumeResponse)
async def parse_resume(req: ParseResumeRequest):
    from app.core.model import infer_parse
    raw = infer_parse(req.resume_text)
    parsed_json = extract_json(raw)
    return ParseResumeResponse(raw_output=raw, parsed_json=parsed_json)