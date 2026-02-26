from typing import List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.services.match_score import calculate_match_score
from app.schemas.candidate_search import CandidateSearchResult


class VacancyNotFoundError(Exception):
    pass


async def search_candidates_for_hr(
    session: AsyncSession,
    skills: Optional[list[str]] = None,
    has_resume: Optional[bool] = None,
    is_active: Optional[bool] = None,
    is_blocked: Optional[bool] = None,
    vacancy_id: Optional[int] = None,
    min_match_score: Optional[float] = None,
    search_text: Optional[str] = None,
) -> list[CandidateSearchResult]:
    # Базовый запрос: только кандидаты
    query = select(User).where(User.role == UserRole.CANDIDATE)

    # Фильтр по наличию резюме
    if has_resume is not None:
        if has_resume:
            query = query.where(User.resume_text.isnot(None))
        else:
            query = query.where(User.resume_text.is_(None))

    # Фильтр по активности
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Фильтр по блокировке
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)

    # Поиск по тексту (резюме, ФИО, email)
    if search_text:
        search_lower = search_text.lower()
        query = query.where(
            or_(
                func.lower(User.email).contains(search_lower),
                func.lower(User.full_name).contains(search_lower),
                func.lower(User.resume_text).contains(search_lower),
            )
        )

    result = await session.execute(query)
    candidates = result.scalars().all()

    # Если нужно считать match_score — подготовим вакансию
    vacancy: Optional[Vacancy] = None
    if vacancy_id is not None:
        vacancy_result = await session.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        if vacancy is None:
            raise VacancyNotFoundError()

    results: list[CandidateSearchResult] = []

    for candidate in candidates:
        # Фильтр по навыкам
        if skills:
            if not candidate.resume_text:
                continue

            resume_lower = candidate.resume_text.lower()
            has_any_skill = any(skill.lower() in resume_lower for skill in skills)
            if not has_any_skill:
                continue

        match_score: Optional[float] = None
        if vacancy and candidate.resume_text:
            match_score = calculate_match_score(
                resume_text=candidate.resume_text,
                required_skills=vacancy.required_skills,
            )
            if min_match_score is not None and match_score < min_match_score:
                continue

        # Превью резюме
        resume_preview = None
        if candidate.resume_text:
            preview_length = 200
            resume_preview = candidate.resume_text[:preview_length]
            if len(candidate.resume_text) > preview_length:
                resume_preview += "..."

        results.append(
            CandidateSearchResult(
                id=candidate.id,
                email=candidate.email,
                full_name=candidate.full_name,
                has_resume=candidate.resume_text is not None,
                is_active=candidate.is_active,
                is_blocked=candidate.is_blocked,
                match_score=match_score,
                resume_preview=resume_preview,
            )
        )

    # Сортировка
    if vacancy_id is not None:
        results.sort(
            key=lambda x: x.match_score if x.match_score is not None else 0.0,
            reverse=True,
        )
    else:
        results.sort(key=lambda x: x.email)

    return results
