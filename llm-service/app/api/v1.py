# app/api/v1.py
import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.model import infer, infer_parse

router = APIRouter()

# Один executor с 1 воркером — модель одна, запросы идут по очереди,
# но event loop не блокируется и может принимать новые соединения.
_executor = ThreadPoolExecutor(max_workers=1)


async def run_in_thread(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, partial(fn, *args))


# ─── Schemas ──────────────────────────────────────────────────────────────────

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


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    text = await run_in_thread(infer, req.vacancy_text, req.resume_text)
    score = extract_score(text)
    return AnalyzeResponse(raw_output=text, score=score)


@router.post("/parse-resume", response_model=ParseResumeResponse)
async def parse_resume(req: ParseResumeRequest):
    raw = await run_in_thread(infer_parse, req.resume_text)
    parsed_json = extract_json(raw)
    print(f"[parse-resume] parsed_json keys: {list(parsed_json.keys()) if parsed_json else None}", flush=True)
    return ParseResumeResponse(raw_output=raw, parsed_json=parsed_json)
