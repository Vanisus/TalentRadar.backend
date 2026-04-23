from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.database import get_async_session
from app.dependencies import get_current_admin
from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.notification import Notification
from app.schemas.user import UserRead
from app.schemas.health import HealthStatus
from app.schemas.statistics import PlatformStatistics
from app.config import settings
from app.services.admin.logs import read_last_log_lines
from app.services.auth.auth_tracking import get_suspicious_users
from app.core.health_monitor import get_overall_health
from app.services.admin.statistics import get_platform_statistics  # NEW

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserRead])
async def get_users(
    is_blocked: bool | None = Query(None, description="Фильтр по заблокированным"),
    role: UserRole | None = Query(None, description="Фильтр по роли"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(User)
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)
    if role is not None:
        query = query.where(User.role == role)

    result = await session.execute(query)
    return result.scalars().all()


@router.post("/users/{user_id}/block", status_code=status.HTTP_200_OK)
async def block_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block yourself",
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
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_blocked = False
    await session.commit()

    return {"message": f"User {user.email} has been unblocked"}


@router.get("/stats", response_model=PlatformStatistics)
async def get_statistics(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить детальную статистику платформы."""
    return await get_platform_statistics(session=session)


@router.get("/logs")
async def get_logs(
    lines: int = Query(100, ge=1, le=1000, description="Количество последних строк"),
    current_user: User = Depends(get_current_admin),
):
    """Получить последние N строк из лога."""
    result = read_last_log_lines(lines=lines)

    if not result["exists"]:
        return {
            "message": "Log file not found",
            "logs": [],
        }

    return {
        "total_lines": result["total_lines"],
        "returned_lines": result["returned_lines"],
        "logs": result["logs"],
    }


@router.get("/suspicious")
async def get_suspicious_activity(
    min_attempts: int = Query(
        3, ge=1, description="Минимальное количество попыток"
    ),
    current_user: User = Depends(get_current_admin),
):
    suspicious = await get_suspicious_users(min_attempts=min_attempts)
    return {
        "total": len(suspicious),
        "users": suspicious,
    }


@router.get("/health", response_model=HealthStatus)
async def get_platform_health(
    current_user: User = Depends(get_current_admin),
):
    return await get_overall_health()
