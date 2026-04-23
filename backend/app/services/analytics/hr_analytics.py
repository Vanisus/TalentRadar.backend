from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.application import Application, ApplicationStatus
from app.models.user import User
from app.models.vacancy import Vacancy


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


async def get_vacancy_analytics_for_hr(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
    days: int = 30,
) -> Dict[str, Any]:
    vacancy = await _get_hr_vacancy_or_404(
        session=session,
        hr=hr,
        vacancy_id=vacancy_id,
    )

    since = datetime.utcnow() - timedelta(days=days)

    # Общее количество откликов за период
    total_query = await session.execute(
        select(func.count(Application.id)).where(
            Application.vacancy_id == vacancy.id,
            Application.created_at >= since,
        )
    )
    total_applications = total_query.scalar() or 0

    # Разбивка по статусам
    status_query = await session.execute(
        select(
            Application.status,
            func.count(Application.id),
        ).where(
            Application.vacancy_id == vacancy.id,
            Application.created_at >= since,
        ).group_by(Application.status)
    )
    status_counts_raw = status_query.all()

    status_counts = {
        status.value: count for status, count in status_counts_raw
    }

    # Средний match_score
    match_score_query = await session.execute(
        select(func.avg(Application.match_score)).where(
            Application.vacancy_id == vacancy.id,
            Application.created_at >= since,
        )
    )
    avg_match_score = match_score_query.scalar()
    if avg_match_score is not None:
        avg_match_score = float(avg_match_score)

    return {
        "vacancy_id": vacancy.id,
        "vacancy_title": vacancy.title,
        "period_days": days,
        "total_applications": total_applications,
        "status_counts": status_counts,
        "avg_match_score": avg_match_score,
        "since": since,
    }


async def get_hr_overall_analytics(
    session: AsyncSession,
    hr: User,
    days: int = 30,
) -> Dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)

    # Все вакансии HR
    vacancies_result = await session.execute(
        select(Vacancy.id, Vacancy.title).where(Vacancy.hr_id == hr.id)
    )
    vacancies = vacancies_result.all()
    vacancy_ids = [v.id for v in vacancies]

    if not vacancy_ids:
        return {
            "hr_id": hr.id,
            "period_days": days,
            "total_vacancies": 0,
            "total_applications": 0,
            "avg_match_score": None,
            "vacancies": [],
        }

    # Общее количество откликов по всем вакансиям HR
    total_app_query = await session.execute(
        select(func.count(Application.id)).where(
            Application.vacancy_id.in_(vacancy_ids),
            Application.created_at >= since,
        )
    )
    total_applications = total_app_query.scalar() or 0

    # Средний match_score по всем вакансиям HR
    avg_match_query = await session.execute(
        select(func.avg(Application.match_score)).where(
            Application.vacancy_id.in_(vacancy_ids),
            Application.created_at >= since,
        )
    )
    avg_match_score = avg_match_query.scalar()
    if avg_match_score is not None:
        avg_match_score = float(avg_match_score)

    # Статусная разбивка по всем вакансиям HR
    status_query = await session.execute(
        select(
            Application.status,
            func.count(Application.id),
        ).where(
            Application.vacancy_id.in_(vacancy_ids),
            Application.created_at >= since,
        ).group_by(Application.status)
    )
    status_counts_raw = status_query.all()
    status_counts = {status.value: count for status, count in status_counts_raw}

    return {
        "hr_id": hr.id,
        "period_days": days,
        "total_vacancies": len(vacancies),
        "total_applications": total_applications,
        "avg_match_score": avg_match_score,
        "status_counts": status_counts,
        "since": since,
    }
