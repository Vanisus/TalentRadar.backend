from datetime import datetime
from pydantic import BaseModel

from app.models.application import ApplicationStatus


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

    class Config:
        from_attributes = True


class ApplicationWithVacancy(ApplicationRead):
    vacancy_title: str


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
