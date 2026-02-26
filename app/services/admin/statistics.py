from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.schemas.statistics import (
    PlatformStatistics,
    UserStatistics,
    VacancyStatistics,
    ApplicationStatistics,
    NotificationStatistics,
)


async def get_platform_statistics(
    session: AsyncSession,
) -> PlatformStatistics:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ===== Пользователи =====
    total_users = (
        await session.execute(select(func.count(User.id)))
    ).scalar()

    total_candidates = (
        await session.execute(
            select(func.count(User.id)).where(User.role == UserRole.CANDIDATE)
        )
    ).scalar()

    total_hr = (
        await session.execute(
            select(func.count(User.id)).where(User.role == UserRole.HR)
        )
    ).scalar()

    total_admins = (
        await session.execute(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN)
        )
    ).scalar()

    total_blocked = (
        await session.execute(
            select(func.count(User.id)).where(User.is_blocked.is_(True))
        )
    ).scalar()

    total_with_resume = (
        await session.execute(
            select(func.count(User.id)).where(
                User.role == UserRole.CANDIDATE,
                User.resume_text.isnot(None),
            )
        )
    ).scalar()

    total_verified = (
        await session.execute(
            select(func.count(User.id)).where(User.is_verified.is_(True))
        )
    ).scalar()

    total_active_users = (
        await session.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
    ).scalar()

    # ===== Вакансии =====
    total_vacancies = (
        await session.execute(select(func.count(Vacancy.id)))
    ).scalar()

    total_active_vacancies = (
        await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.is_active.is_(True))
        )
    ).scalar()

    total_inactive_vacancies = (
        await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.is_active.is_(False))
        )
    ).scalar()

    total_vacancies_today = (
        await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.created_at >= today_start)
        )
    ).scalar()

    total_vacancies_week = (
        await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.created_at >= week_start)
        )
    ).scalar()

    total_vacancies_month = (
        await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.created_at >= month_start)
        )
    ).scalar()

    # ===== Заявки =====
    total_applications = (
        await session.execute(select(func.count(Application.id)))
    ).scalar()

    total_new_apps = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.status == ApplicationStatus.NEW
            )
        )
    ).scalar()

    total_under_review = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.status == ApplicationStatus.UNDER_REVIEW
            )
        )
    ).scalar()

    total_rejected = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.status == ApplicationStatus.REJECTED
            )
        )
    ).scalar()

    total_accepted = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.status == ApplicationStatus.ACCEPTED
            )
        )
    ).scalar()

    average_match_score_raw = (
        await session.execute(
            select(func.avg(Application.match_score))
        )
    ).scalar()
    average_match_score = float(average_match_score_raw or 0.0)

    total_apps_today = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.created_at >= today_start
            )
        )
    ).scalar()

    total_apps_week = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.created_at >= week_start
            )
        )
    ).scalar()

    total_apps_month = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.created_at >= month_start
            )
        )
    ).scalar()

    # ===== Уведомления =====
    total_notifications = (
        await session.execute(select(func.count(Notification.id)))
    ).scalar()

    total_unread = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.is_read.is_(False)
            )
        )
    ).scalar()

    total_read = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.is_read.is_(True)
            )
        )
    ).scalar()

    total_notifications_today = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.created_at >= today_start
            )
        )
    ).scalar()

    # ===== Топ навыков =====
    all_vacancies = (
        await session.execute(select(Vacancy))
    ).scalars().all()

    all_skills: List[str] = []
    for vacancy in all_vacancies:
        all_skills.extend(vacancy.required_skills or [])

    skills_counter = Counter(all_skills)
    vacancies_count = len(all_vacancies)

    top_skills = [
        {
            "skill": skill,
            "count": count,
            "percentage": round(
                (count / vacancies_count) * 100.0, 2
            ) if vacancies_count else 0.0,
        }
        for skill, count in skills_counter.most_common(10)
    ]

    return PlatformStatistics(
        timestamp=now,
        users=UserStatistics(
            total=total_users or 0,
            candidates=total_candidates or 0,
            hr_managers=total_hr or 0,
            admins=total_admins or 0,
            blocked=total_blocked or 0,
            with_resume=total_with_resume or 0,
            verified=total_verified or 0,
            active=total_active_users or 0,
        ),
        vacancies=VacancyStatistics(
            total=total_vacancies or 0,
            active=total_active_vacancies or 0,
            inactive=total_inactive_vacancies or 0,
            created_today=total_vacancies_today or 0,
            created_this_week=total_vacancies_week or 0,
            created_this_month=total_vacancies_month or 0,
        ),
        applications=ApplicationStatistics(
            total=total_applications or 0,
            new=total_new_apps or 0,
            under_review=total_under_review or 0,
            rejected=total_rejected or 0,
            accepted=total_accepted or 0,
            average_match_score=round(average_match_score, 2),
            created_today=total_apps_today or 0,
            created_this_week=total_apps_week or 0,
            created_this_month=total_apps_month or 0,
        ),
        notifications=NotificationStatistics(
            total=total_notifications or 0,
            unread=total_unread or 0,
            read=total_read or 0,
            created_today=total_notifications_today or 0,
        ),
        top_skills=top_skills,
    )
