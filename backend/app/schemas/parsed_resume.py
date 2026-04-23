# app/schemas/parsed_resume.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ParsedResumeRead(BaseModel):
    id: int
    user_id: int
    source_resume_path: Optional[str] = None
    parse_status: str
    parser_version: str
    parsed_json: Optional[Dict[str, Any]] = None
    normalized_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
