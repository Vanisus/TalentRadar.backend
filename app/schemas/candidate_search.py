from typing import Optional
from pydantic import BaseModel, Field


class CandidateSearchFilters(BaseModel):
    skills: Optional[list[str]] = Field(None, description="Список навыков для поиска в резюме (кандидат должен иметь хотя бы один)")
    has_resume: Optional[bool] = Field(None, description="Только кандидаты с загруженным резюме")
    is_active: Optional[bool] = Field(None, description="Только активные кандидаты")
    is_blocked: Optional[bool] = Field(None, description="Только заблокированные кандидаты (обычно False)")
    vacancy_id: Optional[int] = Field(None, description="ID вакансии для расчета match_score")
    min_match_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Минимальный match_score с указанной вакансией (требует vacancy_id)")
    search_text: Optional[str] = Field(None, description="Поиск по тексту в резюме, имени или email")


class CandidateSearchResult(BaseModel):
    user_id: int
    email: str
    full_name: Optional[str] = None
    has_resume: bool = Field(..., description="Есть ли загруженное резюме")
    is_active: bool
    is_blocked: bool
    match_score: Optional[float] = Field(None, description="Процент совпадения с указанной вакансией (если vacancy_id был указан)")
    resume_preview: Optional[str] = Field(None, description="Короткий предпросмотр резюме (первые 200 символов)")

