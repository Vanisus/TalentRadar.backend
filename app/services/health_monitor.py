from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os

from app.services.redis_client import redis_client
from app.config import settings

# Опциональный импорт psutil для системных метрик
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


async def check_database_health() -> Dict[str, Any]:
    """Проверка работоспособности базы данных"""
    try:
        from app.database import async_session_maker
        async with async_session_maker() as session:
            # Простой запрос для проверки подключения
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            await result.fetchone()
            return {
                "status": "healthy",
                "message": "Database connection is working"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }


async def check_redis_health() -> Dict[str, Any]:
    """Проверка работоспособности Redis"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "message": "Redis connection is working"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }


def check_filesystem_health() -> Dict[str, Any]:
    """Проверка работоспособности файловой системы"""
    issues = []
    
    # Проверка директории uploads
    upload_dir = Path(settings.UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        # Проверка на возможность записи
        test_file = upload_dir / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        issues.append(f"Uploads directory issue: {str(e)}")
    
    # Проверка директории logs
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Проверка на возможность записи
        test_file = log_dir / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        issues.append(f"Logs directory issue: {str(e)}")
    
    if issues:
        return {
            "status": "unhealthy",
            "message": "; ".join(issues)
        }
    
    return {
        "status": "healthy",
        "message": "Filesystem is working properly"
    }


def get_system_metrics() -> Dict[str, Any]:
    """Получение системных метрик"""
    if not PSUTIL_AVAILABLE:
        return {
            "message": "System metrics unavailable (psutil not installed)"
        }
    
    try:
        # Использование CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Использование памяти
        memory = psutil.virtual_memory()
        
        # Использование диска (для текущей директории или корневой)
        try:
            disk = psutil.disk_usage('.')
        except:
            disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "status": "healthy" if cpu_percent < 90 else "warning" if cpu_percent < 95 else "critical"
            },
            "memory": {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "percent": memory.percent,
                "status": "healthy" if memory.percent < 85 else "warning" if memory.percent < 95 else "critical"
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "percent": round((disk.used / disk.total) * 100, 2),
                "status": "healthy" if (disk.used / disk.total) * 100 < 85 else "warning" if (disk.used / disk.total) * 100 < 95 else "critical"
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to get system metrics: {str(e)}"
        }


async def get_overall_health() -> Dict[str, Any]:
    """Получение общей информации о работоспособности системы"""
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    fs_health = check_filesystem_health()
    system_metrics = get_system_metrics()
    
    # Определяем общий статус
    all_healthy = all([
        db_health.get("status") == "healthy",
        redis_health.get("status") == "healthy",
        fs_health.get("status") == "healthy"
    ])
    
    overall_status = "healthy" if all_healthy else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": db_health,
            "redis": redis_health,
            "filesystem": fs_health
        },
        "system_metrics": system_metrics
    }

