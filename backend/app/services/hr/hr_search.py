from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.application import Application, ApplicationStatus
from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.candidate_profile import CandidateProfile
from app.services.analytics.match_score import calculate_match_score


async def _get_hr_vacancy_or_404(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> Vacancy:
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.hr_id == hr.id,
        )
    )
    vacancy = result.scalar_one_or_none()
    if vacancy is None:
        raise NotFoundError(
            message="Vacancy not found",
            code="VACANCY_NOT_FOUND",
            details={"vacancy_id": vacancy_id},
        )
    return vacancy


async def get_hr_vacancy_with_stats(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> Dict[str, Any]:
    vacancy = await _get_hr_vacancy_or_404(
        session=session,
        hr=hr,
        vacancy_id=vacancy_id,
    )

    result = await session.execute(
        select(Application.status).where(
            Application.vacancy_id == vacancy.id,
        )
    )
    statuses: List[ApplicationStatus] = result.scalars().all()

    total_applications = len(statuses)
    accepted = sum(1 for s in statuses if s == ApplicationStatus.ACCEPTED)
    rejected = sum(1 for s in statuses if s == ApplicationStatus.REJECTED)

    return {
        "id": vacancy.id,
        "title": vacancy.title,
        "is_active": vacancy.is_active,
        "created_at": vacancy.created_at,
        "updated_at": vacancy.updated_at,
        "total_applications": total_applications,
        "accepted_applications": accepted,
        "rejected_applications": rejected,
    }


async def search_hr_vacancies(
    session: AsyncSession,
    hr: User,
    query: str,
) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.hr_id == hr.id,
            Vacancy.title.ilike(f"%{query}%"),
        )
    )
    vacancies = result.scalars().all()

    return [
        {
            "id": v.id,
            "title": v.title,
            "is_active": v.is_active,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
        }
        for v in vacancies
    ]


async def search_candidates_for_hr(
    session: AsyncSession,
    skills: Optional[List[str]] = None,
    has_resume: Optional[bool] = None,
    is_active: Optional[bool] = None,
    is_blocked: Optional[bool] = False,
    vacancy_id: Optional[int] = None,
    min_match_score: Optional[float] = None,
    search_text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Поиск кандидатов для HR по базовым критериям + опциональный match_score с вакансией.
    """
    query = (
        select(User, CandidateProfile)
        .join(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(User.role == UserRole.CANDIDATE)
    )

    if has_resume is True:
        query = query.where(User.resume_text.isnot(None))
    elif has_resume is False:
        query = query.where(User.resume_text.is_(None))

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)

    if search_text:
        pattern = f"%{search_text.lower()}%"
        query = query.where(
            func.or_(
                func.lower(User.full_name).like(pattern),
                func.lower(User.email).like(pattern),
                func.lower(func.coalesce(User.resume_text, "")).like(pattern),
            )
        )

    if skills:
        for skill in skills:
            pattern = f"%{skill.lower()}%"
            query = query.where(
                func.lower(func.coalesce(User.resume_text, "")).like(pattern)
            )

    result = await session.execute(query)
    rows = result.all()

    vacancy: Optional[Vacancy] = None
    if vacancy_id is not None:
        v_res = await session.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id, Vacancy.is_active.is_(True))
        )
        vacancy = v_res.scalar_one_or_none()
        if vacancy is None:
            raise NotFoundError(
                message="Vacancy not found",
                code="VACANCY_NOT_FOUND",
                details={"vacancy_id": vacancy_id},
            )

    candidates: List[Dict[str, Any]] = []

    for user, profile in rows:
        match_score: Optional[float] = None
        if vacancy and user.resume_text:
            match_score = calculate_match_score(
                resume_text=user.resume_text,
                required_skills=vacancy.required_skills,
            )
            if min_match_score is not None and match_score < min_match_score:
                continue

        candidates.append(
            {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "city": profile.city,
                "has_resume": user.resume_text is not None,
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "match_score": match_score,
            }
        )

    if vacancy_id is not None:
        candidates.sort(
            key=lambda c: (c["match_score"] is None, -(c["match_score"] or 0.0))
        )

    return candidates
