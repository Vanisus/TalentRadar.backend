from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CandidateNoteBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    body: str = Field(..., min_length=1)


class CandidateNoteCreate(CandidateNoteBase):
    pass


class CandidateNoteRead(CandidateNoteBase):
    id: int
    candidate_id: int
    hr_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
