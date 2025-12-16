from typing import List, Optional
from pydantic import BaseModel, Field


class CandidateMatchAnalysis(BaseModel):
    passes: bool = Field(..., description="Проходит ли кандидат на вакансию (совпадение >= 50%)")
    match_score: float = Field(..., description="Процент совпадения (0-100)")
    matched_skills: List[str] = Field(..., description="Навыки, которые есть у кандидата")
    missing_skills: List[str] = Field(..., description="Навыки, которых нет у кандидата")
    matched_skills_count: int = Field(..., description="Количество найденных навыков")
    missing_skills_count: int = Field(..., description="Количество отсутствующих навыков")
    total_required_skills: int = Field(..., description="Общее количество требуемых навыков")
    explanation: str = Field(..., description="Объяснение соответствия кандидата требованиям вакансии")


class ApplicationAnalysis(BaseModel):
    application_id: int = Field(..., description="ID заявки")
    candidate_id: int = Field(..., description="ID кандидата")
    candidate_email: str = Field(..., description="Email кандидата")
    candidate_full_name: Optional[str] = Field(None, description="ФИО кандидата")
    has_resume: bool = Field(..., description="Есть ли резюме у кандидата")
    application_status: str = Field(..., description="Статус заявки")
    match_analysis: Optional[CandidateMatchAnalysis] = Field(None, description="Детальный анализ соответствия")
    error: Optional[str] = Field(None, description="Ошибка при анализе (например, если нет резюме)")


class VacancyApplicationsAnalysis(BaseModel):
    vacancy_id: int = Field(..., description="ID вакансии")
    vacancy_title: str = Field(..., description="Название вакансии")
    total_applications: int = Field(..., description="Общее количество заявок")
    passing_candidates: int = Field(..., description="Количество кандидатов, которые проходят на вакансию")
    not_passing_candidates: int = Field(..., description="Количество кандидатов, которые не проходят")
    applications_without_resume: int = Field(..., description="Количество заявок без резюме")
    applications: List[ApplicationAnalysis] = Field(..., description="Детальный анализ каждой заявки")

