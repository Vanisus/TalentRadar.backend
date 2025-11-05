from datetime import datetime
from pydantic import BaseModel, Field


class VacancyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    required_skills: list[str] = Field(..., min_items=1)


class VacancyCreate(VacancyBase):
    pass


class VacancyUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    required_skills: list[str] | None = Field(None, min_items=1)
    is_active: bool | None = None


class VacancyRead(VacancyBase):
    id: int
    hr_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
