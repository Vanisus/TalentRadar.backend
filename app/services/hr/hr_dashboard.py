from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.notification import Notification
from app.models.user import User
from app.models.vacancy import Vacancy


async def get_hr_dashboard(
    session: AsyncSession,
    hr: User,
    days_new: int = 1,
    days_stale: int = 7,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    since_new = now - timedelta(days=days_new)
    since_stale = now - timedelta(days=days_stale)

    # 1) новые отклики за период на вакансии HR
    result = await session.execute(
        select(
            Application.id,
            Application.vacancy_id,
            Application.candidate_id,
            Application.status,
            Application.created_at,
            Vacancy.title,
        )
        .join(Vacancy, Vacancy.id == Application.vacancy_id)
        .where(
            Vacancy.hr_id == hr.id,
            Application.created_at >= since_new,
        )
        .order_by(Application.created_at.desc())
    )
    new_applications_rows = result.all()
    new_applications: List[Dict[str, Any]] = [
        {
            "application_id": r.id,
            "vacancy_id": r.vacancy_id,
            "vacancy_title": r.title,
            "candidate_id": r.candidate_id,
            "status": r.status.value,
            "created_at": r.created_at,
        }
        for r in new_applications_rows
    ]

    # 2) непрочитанные уведомления HR
    notif_result = await session.execute(
        select(Notification)
        .where(
            Notification.user_id == hr.id,
            Notification.is_read.is_(False),
        )
        .order_by(Notification.created_at.desc())
    )
    unread_notifications = [
        {
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at,
        }
        for n in notif_result.scalars().all()
    ]

    # 3) вакансии HR без новых откликов N дней
    # 3.1 все вакансии HR
    vacancies_result = await session.execute(
        select(Vacancy).where(Vacancy.hr_id == hr.id)
    )
    vacancies = vacancies_result.scalars().all()
    vacancy_ids = [v.id for v in vacancies]

    stale_vacancies: List[Dict[str, Any]] = []
    if vacancy_ids:
        # 3.2 последняя заявка по каждой вакансии
        last_app_result = await session.execute(
            select(
                Application.vacancy_id,
                func.max(Application.created_at).label("last_app_created_at"),
            )
            .where(Application.vacancy_id.in_(vacancy_ids))
            .group_by(Application.vacancy_id)
        )
        last_apps_map = {
            row.vacancy_id: row.last_app_created_at for row in last_app_result.all()
        }

        for v in vacancies:
            last_app_dt = last_apps_map.get(v.id)
            # stale, если не было заявок вообще или последняя старше days_stale
            is_stale = (
                last_app_dt is None
                or last_app_dt < since_stale
            )
            if not is_stale:
                continue

            stale_vacancies.append(
                {
                    "vacancy_id": v.id,
                    "title": v.title,
                    "is_active": v.is_active,
                    "created_at": v.created_at,
                    "last_application_at": last_app_dt,
                }
            )

    return {
        "now": now,
        "new_applications": new_applications,
        "unread_notifications": unread_notifications,
        "stale_vacancies": stale_vacancies,
        "config": {
            "days_new": days_new,
            "days_stale": days_stale,
        },
    }
