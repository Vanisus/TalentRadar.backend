from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user import User
from app.services.users import get_user_manager, current_active_user
from app.services.auth_tracking import (
    record_failed_login,
    clear_failed_login,
    is_locked_out
)
from app.services.redis_client import redis_client
from fastapi_users.manager import BaseUserManager

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login_with_tracking(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_async_session),
        user_manager: BaseUserManager = Depends(get_user_manager),
):
    """
    Логин с отслеживанием неудачных попыток
    """
    email = form_data.username

    # Проверяем блокировку
    if await is_locked_out(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 15 minutes."
        )

    # Получаем пользователя
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    # Проверяем пароль
    if not user or not user_manager.password_helper.verify_and_update(
            form_data.password, user.hashed_password
    )[0]:
        await record_failed_login(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Проверяем блокировку в БД
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked by administrator"
        )

    # Успешный вход - очищаем счётчик
    await clear_failed_login(email)

    # Генерируем токен
    from app.services.users import auth_backend
    token = await auth_backend.get_strategy().write_token(user)

    # Сохраняем токен в Redis (для logout)
    await redis_client.setex(
        f"token:{token}",
        60 * 60 * 24,  # 24 часа
        str(user.id)
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
        authorization: str = Header(...),
        current_user: User = Depends(current_active_user),
):
    """
    Выход из системы (инвалидация токена)
    """
    # Извлекаем токен из заголовка
    try:
        token = authorization.split(" ")[1]  # "Bearer <token>"
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )

    # Удаляем токен из Redis (инвалидация)
    await redis_client.delete(f"token:{token}")

    # Добавляем в blacklist
    await redis_client.setex(
        f"blacklist:{token}",
        60 * 60 * 24,  # 24 часа
        "revoked"
    )

    return {"message": "Successfully logged out"}
