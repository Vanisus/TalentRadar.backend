import time
import logging
from pathlib import Path
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("recruitment_api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех HTTP запросов
    Логирует: время, метод, путь, статус, user_id (если авторизован), время выполнения
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Получаем user_id если есть (из состояния request после auth)
        user_id = getattr(request.state, "user_id", None)

        # Выполняем запрос
        response = await call_next(request)

        # Вычисляем время выполнения
        process_time = time.time() - start_time

        # Формируем лог
        log_message = (
            f"{request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"User: {user_id or 'anonymous'} | "
            f"Time: {process_time:.3f}s"
        )

        # Логируем
        if response.status_code >= 500:
            logger.error(log_message)
        elif response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        return response
