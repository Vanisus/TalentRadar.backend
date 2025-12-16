from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str = Field(..., description="Статус компонента (healthy/unhealthy)")
    message: str = Field(..., description="Сообщение о состоянии компонента")


class SystemMetrics(BaseModel):
    cpu: Optional[Dict[str, Any]] = Field(None, description="Метрики CPU")
    memory: Optional[Dict[str, Any]] = Field(None, description="Метрики памяти")
    disk: Optional[Dict[str, Any]] = Field(None, description="Метрики диска")
    error: Optional[str] = Field(None, description="Ошибка при получении метрик")
    message: Optional[str] = Field(None, description="Информационное сообщение")


class HealthStatus(BaseModel):
    status: str = Field(..., description="Общий статус системы (healthy/unhealthy)")
    timestamp: str = Field(..., description="Время проверки")
    components: Dict[str, ComponentHealth] = Field(..., description="Статусы компонентов")
    system_metrics: SystemMetrics = Field(..., description="Системные метрики")

