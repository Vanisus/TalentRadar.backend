from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.candidate_profile import CandidateProfile
from app.models.vacancy import Vacancy
from app.services.resumes.resume_recommendations import analyze_resume_improvements


async def _get_candidate_profile(
    session: AsyncSession,
    user: User,
) -> CandidateProfile | None:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    return result.scalar_one_or_none()


def _calculate_profile_completion(profile: CandidateProfile | None) -> float:
    """
    Очень простой расчёт заполненности профиля по ключевым полям.
    """
    if profile is None:
        return 0.0

    fields = [
        profile.phone,
        profile.city,
        profile.desired_position,
        profile.desired_salary,
        profile.about_me,
    ]
    total = len(fields)
    filled = sum(1 for f in fields if f not in (None, "", []))

    # опыт, образование, навыки, портфолио как отдельные «слоты»
    extra_slots = 4
    total += extra_slots
    if profile.experiences:
        filled += 1
    if profile.educations:
        filled += 1
    if profile.skills:
        filled += 1
    if profile.portfolio_items:
        filled += 1

    return round((filled / total) * 100.0, 1) if total > 0 else 0.0


async def get_resume_summary_for_candidate(
    session: AsyncSession,
    candidate: User,
) -> Dict[str, Any]:
    # базовая инфа по резюме/профилю
    has_resume = candidate.resume_text is not None
    resume_text_length = len(candidate.resume_text or "")

    profile = await _get_candidate_profile(session=session, user=candidate)
    profile_completion = _calculate_profile_completion(profile)

    # считаем рекомендации только если есть резюме и есть вакансии
    recommendations: Dict[str, Any] | None = None
    if candidate.resume_text:
        v_result = await session.execute(
            select(Vacancy).where(Vacancy.is_active.is_(True))
        )
        vacancies = v_result.scalars().all()

        if vacancies:
            all_vacancy_skills = [v.required_skills for v in vacancies]
            recommendations = analyze_resume_improvements(
                resume_text=candidate.resume_text,
                all_vacancy_skills=all_vacancy_skills,
            )

    return {
        "has_resume": has_resume,
        "resume_path": candidate.resume_path,
        "resume_text_length": resume_text_length,
        "profile_completion_percent": profile_completion,
        "recommendations": recommendations,
    }
