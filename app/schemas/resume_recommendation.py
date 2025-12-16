from typing import List, Optional
from pydantic import BaseModel, Field


class MissingSkill(BaseModel):
    skill: str = Field(..., description="Название навыка")
    frequency: int = Field(..., description="Количество вакансий, в которых упоминается этот навык")
    percentage_of_vacancies: float = Field(..., description="Процент вакансий, требующих этот навык")


class PopularSkill(BaseModel):
    skill: str = Field(..., description="Название навыка")
    frequency: int = Field(..., description="Количество вакансий, в которых упоминается этот навык")


class ResumeStats(BaseModel):
    length: int = Field(..., description="Длина резюме в символах")
    word_count: int = Field(..., description="Количество слов в резюме")
    has_contact_info: bool = Field(..., description="Наличие контактной информации")
    has_experience: bool = Field(..., description="Наличие информации об опыте работы")
    has_education: bool = Field(..., description="Наличие информации об образовании")
    has_skills_section: bool = Field(..., description="Наличие раздела с навыками")


class GeneralRecommendation(BaseModel):
    type: str = Field(..., description="Тип рекомендации (length, contact, experience, education, skills_section, missing_skills)")
    priority: str = Field(..., description="Приоритет рекомендации (high, medium, low)")
    message: str = Field(..., description="Текст рекомендации")
    details: str = Field(..., description="Дополнительные детали и объяснение")


class ResumeRecommendation(BaseModel):
    missing_skills: List[MissingSkill] = Field(..., description="Список навыков, которых нет в резюме, но они популярны в вакансиях")
    popular_skills: List[PopularSkill] = Field(..., description="Список самых популярных навыков в вакансиях")
    resume_stats: ResumeStats = Field(..., description="Статистика резюме")
    general_recommendations: List[GeneralRecommendation] = Field(..., description="Общие рекомендации по улучшению резюме")

