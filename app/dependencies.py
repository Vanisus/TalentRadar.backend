from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.core.users import current_active_user


async def get_current_hr(
    current_user: User = Depends(current_active_user),
) -> User:
    """Проверка, что текущий пользователь - HR"""
    if current_user.role != UserRole.HR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR managers can access this resource"
        )
    return current_user


async def get_current_candidate(
    current_user: User = Depends(current_active_user),
) -> User:
    """Проверка, что текущий пользователь - кандидат"""
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this resource"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(current_active_user),
) -> User:
    """Проверка, что текущий пользователь - админ"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access this resource"
        )
    return current_user
