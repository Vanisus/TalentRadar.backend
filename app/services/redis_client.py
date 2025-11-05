import redis.asyncio as redis
from app.config import settings

# Асинхронный клиент Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis():
    """Dependency для получения Redis клиента"""
    return redis_client
