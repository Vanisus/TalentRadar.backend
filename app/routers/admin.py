from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pathlib import Path

from app.database import get_async_session
from app.dependencies import get_current_admin
from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.schemas.user import UserRead
from app.schemas.health import HealthStatus
from app.schemas.statistics import PlatformStatistics, UserStatistics, VacancyStatistics, ApplicationStatistics, NotificationStatistics
from app.config import settings
from app.services.auth_tracking import get_suspicious_users
from app.services.health_monitor import get_overall_health

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================

@router.get("/users", response_model=list[UserRead])
async def get_users(
        is_blocked: bool | None = Query(None, description="Фильтр по заблокированным"),
        role: UserRole | None = Query(None, description="Фильтр по роли"),
        current_user: User = Depends(get_current_admin),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить список пользователей с фильтрами"""
    query = select(User)

    # Применяем фильтры
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)

    if role is not None:
        query = query.where(User.role == role)

    result = await session.execute(query)
    users = result.scalars().all()
    return users


@router.post("/users/{user_id}/block", status_code=status.HTTP_200_OK)
async def block_user(
        user_id: int,
        current_user: User = Depends(get_current_admin),
        session: AsyncSession = Depends(get_async_session),
):
    """Заблокировать пользователя"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Нельзя заблокировать самого себя
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block yourself"
        )

    user.is_blocked = True
    await session.commit()

    return {"message": f"User {user.email} has been blocked"}


@router.post("/users/{user_id}/unblock", status_code=status.HTTP_200_OK)
async def unblock_user(
        user_id: int,
        current_user: User = Depends(get_current_admin),
        session: AsyncSession = Depends(get_async_session),
):
    """Разблокировать пользователя"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_blocked = False
    await session.commit()

    return {"message": f"User {user.email} has been unblocked"}


# ==================== СТАТИСТИКА ====================

@router.get("/stats", response_model=PlatformStatistics)
async def get_statistics(
        current_user: User = Depends(get_current_admin),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить детальную статистику платформы"""
    from datetime import datetime, timedelta, timezone
    from collections import Counter
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ========== ПОЛЬЗОВАТЕЛИ ==========
    users_count = await session.execute(select(func.count(User.id)))
    total_users = users_count.scalar()

    candidates_count = await session.execute(
        select(func.count(User.id)).where(User.role == UserRole.CANDIDATE)
    )
    total_candidates = candidates_count.scalar()

    hr_count = await session.execute(
        select(func.count(User.id)).where(User.role == UserRole.HR)
    )
    total_hr = hr_count.scalar()

    admins_count = await session.execute(
        select(func.count(User.id)).where(User.role == UserRole.ADMIN)
    )
    total_admins = admins_count.scalar()

    blocked_count = await session.execute(
        select(func.count(User.id)).where(User.is_blocked == True)
    )
    total_blocked = blocked_count.scalar()

    # Кандидаты с резюме
    candidates_with_resume = await session.execute(
        select(func.count(User.id)).where(
            User.role == UserRole.CANDIDATE,
            User.resume_text.isnot(None)
        )
    )
    total_with_resume = candidates_with_resume.scalar()

    # Верифицированные
    verified_count = await session.execute(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    total_verified = verified_count.scalar()

    # Активные
    active_users_count = await session.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total_active_users = active_users_count.scalar()

    # ========== ВАКАНСИИ ==========
    vacancies_count = await session.execute(select(func.count(Vacancy.id)))
    total_vacancies = vacancies_count.scalar()

    active_vacancies_count = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.is_active == True)
    )
    total_active_vacancies = active_vacancies_count.scalar()

    inactive_vacancies_count = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.is_active == False)
    )
    total_inactive_vacancies = inactive_vacancies_count.scalar()

    # Вакансии созданные сегодня
    vacancies_today = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.created_at >= today_start)
    )
    total_vacancies_today = vacancies_today.scalar()

    # Вакансии созданные на этой неделе
    vacancies_week = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.created_at >= week_start)
    )
    total_vacancies_week = vacancies_week.scalar()

    # Вакансии созданные в этом месяце
    vacancies_month = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.created_at >= month_start)
    )
    total_vacancies_month = vacancies_month.scalar()

    # ========== ЗАЯВКИ ==========
    applications_count = await session.execute(select(func.count(Application.id)))
    total_applications = applications_count.scalar()

    # Заявки по статусам
    new_applications = await session.execute(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.NEW)
    )
    total_new_apps = new_applications.scalar()

    under_review_apps = await session.execute(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.UNDER_REVIEW)
    )
    total_under_review = under_review_apps.scalar()

    rejected_apps = await session.execute(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.REJECTED)
    )
    total_rejected = rejected_apps.scalar()

    accepted_apps = await session.execute(
        select(func.count(Application.id)).where(Application.status == ApplicationStatus.ACCEPTED)
    )
    total_accepted = accepted_apps.scalar()

    # Средний match_score
    avg_score = await session.execute(
        select(func.avg(Application.match_score))
    )
    average_match_score = avg_score.scalar() or 0.0

    # Заявки созданные сегодня
    apps_today = await session.execute(
        select(func.count(Application.id)).where(Application.created_at >= today_start)
    )
    total_apps_today = apps_today.scalar()

    # Заявки созданные на этой неделе
    apps_week = await session.execute(
        select(func.count(Application.id)).where(Application.created_at >= week_start)
    )
    total_apps_week = apps_week.scalar()

    # Заявки созданные в этом месяце
    apps_month = await session.execute(
        select(func.count(Application.id)).where(Application.created_at >= month_start)
    )
    total_apps_month = apps_month.scalar()

    # ========== УВЕДОМЛЕНИЯ ==========
    notifications_count = await session.execute(select(func.count(Notification.id)))
    total_notifications = notifications_count.scalar()

    unread_notifications = await session.execute(
        select(func.count(Notification.id)).where(Notification.is_read == False)
    )
    total_unread = unread_notifications.scalar()

    read_notifications = await session.execute(
        select(func.count(Notification.id)).where(Notification.is_read == True)
    )
    total_read = read_notifications.scalar()

    notifications_today = await session.execute(
        select(func.count(Notification.id)).where(Notification.created_at >= today_start)
    )
    total_notifications_today = notifications_today.scalar()

    # ========== ТОП НАВЫКОВ ==========
    # Получаем все вакансии с их навыками
    all_vacancies = await session.execute(select(Vacancy))
    vacancies_list = all_vacancies.scalars().all()
    
    all_skills = []
    for vacancy in vacancies_list:
        all_skills.extend(vacancy.required_skills)
    
    # Подсчитываем частоту навыков
    skills_counter = Counter(all_skills)
    top_skills = [
        {"skill": skill, "count": count, "percentage": round((count / len(vacancies_list)) * 100, 2) if vacancies_list else 0}
        for skill, count in skills_counter.most_common(10)
    ]

    return PlatformStatistics(
        timestamp=now,
        users=UserStatistics(
            total=total_users,
            candidates=total_candidates,
            hr_managers=total_hr,
            admins=total_admins,
            blocked=total_blocked,
            with_resume=total_with_resume,
            verified=total_verified,
            active=total_active_users
        ),
        vacancies=VacancyStatistics(
            total=total_vacancies,
            active=total_active_vacancies,
            inactive=total_inactive_vacancies,
            created_today=total_vacancies_today,
            created_this_week=total_vacancies_week,
            created_this_month=total_vacancies_month
        ),
        applications=ApplicationStatistics(
            total=total_applications,
            new=total_new_apps,
            under_review=total_under_review,
            rejected=total_rejected,
            accepted=total_accepted,
            average_match_score=round(float(average_match_score), 2),
            created_today=total_apps_today,
            created_this_week=total_apps_week,
            created_this_month=total_apps_month
        ),
        notifications=NotificationStatistics(
            total=total_notifications,
            unread=total_unread,
            read=total_read,
            created_today=total_notifications_today
        ),
        top_skills=top_skills
    )


# ==================== ЛОГИ ====================

@router.get("/logs")
async def get_logs(
        lines: int = Query(100, ge=1, le=1000, description="Количество последних строк"),
        current_user: User = Depends(get_current_admin),
):
    """Получить последние N строк из лога"""
    log_file = Path(settings.LOG_DIR) / "app.log"

    if not log_file.exists():
        return {
            "message": "Log file not found",
            "logs": []
        }

    # Читаем последние N строк
    with open(log_file, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        last_lines = all_lines[-lines:]

    return {
        "total_lines": len(all_lines),
        "returned_lines": len(last_lines),
        "logs": [line.strip() for line in last_lines]
    }


# ==================== ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ ====================

@router.get("/suspicious")
async def get_suspicious_activity(
        min_attempts: int = Query(3, ge=1, description="Минимальное количество попыток"),
        current_user: User = Depends(get_current_admin),
):
    """
    Список пользователей с множественными неудачными попытками входа
    """
    suspicious = await get_suspicious_users(min_attempts=min_attempts)

    return {
        "total": len(suspicious),
        "users": suspicious
    }


# ==================== МОНИТОРИНГ ====================

@router.get("/health", response_model=HealthStatus)
async def get_platform_health(
        current_user: User = Depends(get_current_admin),
):
    """Получить статус работоспособности платформы и всех компонентов"""
    health_status = await get_overall_health()
    return health_status
