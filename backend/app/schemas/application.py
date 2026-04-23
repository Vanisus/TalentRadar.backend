from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus


class ApplicationHRUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=0, le=5)
    pipeline_stage: Optional[str] = Field(None, max_length=50)
    match_summary: Optional[str] = None


class ApplicationCreate(BaseModel):
    vacancy_id: int


class ApplicationRead(BaseModel):
    id: int
    vacancy_id: int
    candidate_id: int
    status: ApplicationStatus
    match_score: float
    created_at: datetime
    updated_at: datetime
    rating: Optional[int] = None
    pipeline_stage: Optional[str] = None
    match_summary: Optional[str] = None

    class Config:
        from_attributes = True


class ApplicationWithVacancy(ApplicationRead):
    vacancy_title: str


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
