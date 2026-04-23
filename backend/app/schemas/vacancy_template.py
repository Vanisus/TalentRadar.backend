from datetime import datetime
from pydantic import BaseModel, Field


class VacancyTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название шаблона")
    title: str = Field(..., min_length=1, max_length=200, description="Заголовок вакансии")
    description: str = Field(..., min_length=1, description="Описание вакансии")
    required_skills: list[str] = Field(..., min_items=1, description="Список требуемых навыков")


class VacancyTemplateCreate(VacancyTemplateBase):
    pass


class VacancyTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200, description="Название шаблона")
    title: str | None = Field(None, min_length=1, max_length=200, description="Заголовок вакансии")
    description: str | None = Field(None, min_length=1, description="Описание вакансии")
    required_skills: list[str] | None = Field(None, min_items=1, description="Список требуемых навыков")


class VacancyTemplateRead(VacancyTemplateBase):
    id: int
    hr_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

