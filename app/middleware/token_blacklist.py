from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_client import redis_client


class TokenBlacklistMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки токенов в blacklist
    """

    async def dispatch(self, request: Request, call_next):
        # Проверяем только защищённые эндпоинты
        if request.url.path.startswith(("/users", "/hr", "/candidates", "/admin")):
            auth_header = request.headers.get("authorization")

            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

                # Проверяем blacklist
                is_blacklisted = await redis_client.exists(f"blacklist:{token}")

                if is_blacklisted:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked"
                    )

        response = await call_next(request)
        return response
