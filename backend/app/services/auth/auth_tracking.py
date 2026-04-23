from datetime import timedelta
from typing import List, Dict, Any

from app.core.redis_client import redis_client

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
FAILED_ATTEMPT_TTL = timedelta(minutes=15)


async def record_failed_login(email: str) -> int:
    key = f"failed_login:{email}"
    count = await redis_client.incr(key)

    if count == 1:
        await redis_client.expire(
            key,
            int(FAILED_ATTEMPT_TTL.total_seconds()),
        )

    if count >= MAX_FAILED_ATTEMPTS:
        lockout_key = f"lockout:{email}"
        await redis_client.setex(
            lockout_key,
            int(LOCKOUT_DURATION.total_seconds()),
            "locked",
        )

    return count


async def clear_failed_login(email: str) -> None:
    key = f"failed_login:{email}"
    await redis_client.delete(key)


async def is_locked_out(email: str) -> bool:
    lockout_key = f"lockout:{email}"
    return (await redis_client.exists(lockout_key)) > 0


async def get_failed_attempts(email: str) -> int:
    key = f"failed_login:{email}"
    count = await redis_client.get(key)
    return int(count) if count else 0


async def get_suspicious_users(min_attempts: int = 3) -> List[Dict[str, Any]]:
    suspicious: List[Dict[str, Any]] = []

    async for key in redis_client.scan_iter(match="failed_login:*"):
        email = key.split(":", 1)[1]
        attempts = await get_failed_attempts(email)

        if attempts < min_attempts:
            continue

        is_locked = await is_locked_out(email)
        ttl = await redis_client.ttl(f"failed_login:{email}")

        suspicious.append(
            {
                "email": email,
                "failed_attempts": attempts,
                "is_locked": is_locked,
                "ttl_seconds": ttl if ttl and ttl > 0 else 0,
            }
        )

    suspicious.sort(key=lambda x: x["failed_attempts"], reverse=True)
    return suspicious
