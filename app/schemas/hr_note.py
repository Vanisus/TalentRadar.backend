from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CandidateNoteBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    body: str = Field(..., min_length=1)


class CandidateNoteCreate(CandidateNoteBase):
    pass


class CandidateNoteAuthor(BaseModel):
    id: int
    full_name: str | None

    class Config:
        from_attributes = True


class CandidateNoteRead(BaseModel):
    id: int
    title: str | None
    body: str
    created_at: datetime
    updated_at: datetime
    hr: CandidateNoteAuthor

    class Config:
        from_attributes = True
