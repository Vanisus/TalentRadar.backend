from typing import Any, Dict, Optional

from pydantic import BaseModel


class ResumeSummary(BaseModel):
    has_resume: bool
    resume_path: Optional[str]
    resume_text_length: int
    profile_completion_percent: float
    recommendations: Optional[Dict[str, Any]] = None
