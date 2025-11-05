from datetime import timedelta
from app.services.redis_client import redis_client

# Настройки
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
FAILED_ATTEMPT_TTL = timedelta(minutes=15)


async def record_failed_login(email: str):
    """Записать неудачную попытку входа"""
    key = f"failed_login:{email}"

    # Увеличиваем счётчик
    count = await redis_client.incr(key)

    # Устанавливаем TTL при первой попытке
    if count == 1:
        await redis_client.expire(key, int(FAILED_ATTEMPT_TTL.total_seconds()))

    # Если превышен лимит - блокируем
    if count >= MAX_FAILED_ATTEMPTS:
        lockout_key = f"lockout:{email}"
        await redis_client.setex(
            lockout_key,
            int(LOCKOUT_DURATION.total_seconds()),
            "locked"
        )

    return count


async def clear_failed_login(email: str):
    """Очистить счётчик при успешном входе"""
    key = f"failed_login:{email}"
    await redis_client.delete(key)


async def is_locked_out(email: str) -> bool:
    """Проверить, заблокирован ли пользователь"""
    lockout_key = f"lockout:{email}"
    return await redis_client.exists(lockout_key) > 0


async def get_failed_attempts(email: str) -> int:
    """Получить количество неудачных попыток"""
    key = f"failed_login:{email}"
    count = await redis_client.get(key)
    return int(count) if count else 0


async def get_suspicious_users(min_attempts: int = 3) -> list[dict]:
    """Получить список пользователей с множественными неудачными попытками"""
    suspicious = []

    # Сканируем все ключи failed_login:*
    async for key in redis_client.scan_iter(match="failed_login:*"):
        email = key.split(":", 1)[1]
        attempts = await get_failed_attempts(email)

        if attempts >= min_attempts:
            is_locked = await is_locked_out(email)
            ttl = await redis_client.ttl(f"failed_login:{email}")

            suspicious.append({
                "email": email,
                "failed_attempts": attempts,
                "is_locked": is_locked,
                "ttl_seconds": ttl if ttl > 0 else 0
            })

    # Сортируем по количеству попыток
    suspicious.sort(key=lambda x: x["failed_attempts"], reverse=True)
    return suspicious
