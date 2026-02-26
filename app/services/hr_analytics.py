from datetime import datetime
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.candidate_analysis import (
    VacancyApplicationsAnalysis,
    ApplicationAnalysis,
    CandidateMatchAnalysis,
)
from app.services.candidate_analysis import analyze_candidate_match


class VacancyNotFoundError(Exception):
    pass


async def ensure_hr_vacancy(
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
        raise VacancyNotFoundError()
    return vacancy


async def get_vacancy_analytics_data(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> dict:
    vacancy = await ensure_hr_vacancy(session=session, hr=hr, vacancy_id=vacancy_id)

    # Общее количество откликов
    total_applications_q = await session.execute(
        select(func.count(Application.id)).where(Application.vacancy_id == vacancy_id)
    )
    total_count = total_applications_q.scalar() or 0

    # Средний match_score
    avg_score_q = await session.execute(
        select(func.avg(Application.match_score)).where(Application.vacancy_id == vacancy_id)
    )
    average_match_score = avg_score_q.scalar() or 0.0

    # Распределение по статусам
    status_distribution_q = await session.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.vacancy_id == vacancy_id)
        .group_by(Application.status)
    )

    status_counts = {
        "new": 0,
        "under_review": 0,
        "rejected": 0,
        "accepted": 0,
    }
    for status, count in status_distribution_q.all():
        status_counts[status.value] = count

    # Время до первого отклика
    first_app_q = await session.execute(
        select(Application.created_at)
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.asc())
        .limit(1)
    )
    first_app_time: datetime | None = first_app_q.scalar()

    time_to_first_response = None
    if first_app_time:
        delta = first_app_time - vacancy.created_at
        time_to_first_response = {
            "days": delta.days,
            "hours": delta.seconds // 3600,
            "minutes": (delta.seconds % 3600) // 60,
            "total_seconds": int(delta.total_seconds()),
        }

    return {
        "vacancy": vacancy,
        "total_applications": total_count,
        "average_match_score": float(average_match_score),
        "status_counts": status_counts,
        "time_to_first_response": time_to_first_response,
    }


async def get_vacancy_applications_analysis_data(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> VacancyApplicationsAnalysis:
    vacancy = await ensure_hr_vacancy(session=session, hr=hr, vacancy_id=vacancy_id)

    result = await session.execute(
        select(Application, User)
        .join(User, Application.candidate_id == User.id)
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.desc())
    )

    applications_data: List[ApplicationAnalysis] = []
    passing_count = 0
    not_passing_count = 0
    without_resume_count = 0

    for application, candidate in result.all():
        match_analysis = None
        error = None

        if not candidate.resume_text:
            without_resume_count += 1
            error = "У кандидата отсутствует резюме, невозможно провести анализ соответствия"
        else:
            analysis_dict = analyze_candidate_match(
                resume_text=candidate.resume_text,
                required_skills=vacancy.required_skills,
            )
            match_analysis = CandidateMatchAnalysis(**analysis_dict)

            if match_analysis.passes:
                passing_count += 1
            else:
                not_passing_count += 1

        applications_data.append(
            ApplicationAnalysis(
                application_id=application.id,
                candidate_id=candidate.id,
                candidate_email=candidate.email,
                candidate_full_name=candidate.full_name,
                has_resume=candidate.resume_text is not None,
                application_status=application.status.value,
                match_analysis=match_analysis,
                error=error,
            )
        )

    return VacancyApplicationsAnalysis(
        vacancy_id=vacancy_id,
        vacancy_title=vacancy.title,
        total_applications=len(applications_data),
        passing_candidates=passing_count,
        not_passing_candidates=not_passing_count,
        applications_without_resume=without_resume_count,
        applications=applications_data,
    )
