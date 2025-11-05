from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pathlib import Path

from app.database import get_async_session
from app.dependencies import get_current_admin
from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.application import Application
from app.schemas.user import UserRead
from app.config import settings
from app.services.auth_tracking import get_suspicious_users

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

@router.get("/stats")
async def get_statistics(
        current_user: User = Depends(get_current_admin),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить общую статистику системы"""

    # Количество пользователей
    users_count = await session.execute(select(func.count(User.id)))
    total_users = users_count.scalar()

    # Количество пользователей по ролям
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

    # Количество заблокированных
    blocked_count = await session.execute(
        select(func.count(User.id)).where(User.is_blocked == True)
    )
    total_blocked = blocked_count.scalar()

    # Количество вакансий
    vacancies_count = await session.execute(select(func.count(Vacancy.id)))
    total_vacancies = vacancies_count.scalar()

    active_vacancies_count = await session.execute(
        select(func.count(Vacancy.id)).where(Vacancy.is_active == True)
    )
    total_active_vacancies = active_vacancies_count.scalar()

    # Количество заявок
    applications_count = await session.execute(select(func.count(Application.id)))
    total_applications = applications_count.scalar()

    return {
        "users": {
            "total": total_users,
            "candidates": total_candidates,
            "hr_managers": total_hr,
            "admins": total_admins,
            "blocked": total_blocked
        },
        "vacancies": {
            "total": total_vacancies,
            "active": total_active_vacancies
        },
        "applications": {
            "total": total_applications
        }
    }


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
