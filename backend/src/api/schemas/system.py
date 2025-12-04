"""
System Monitoring Schemas
Spec: 015-real-system-monitoring

Pydantic модели для API мониторинга системы.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class SystemMetricsResponse(BaseModel):
    """Метрики системы (psutil + pg_stat_activity)."""
    
    cpu_percent: float = Field(..., ge=0, le=100, description="Загрузка CPU в %")
    ram_percent: float = Field(..., ge=0, le=100, description="Использование RAM в %")
    disk_percent: float = Field(..., ge=0, le=100, description="Использование диска в %")
    db_connections_active: int = Field(..., ge=0, description="Активные подключения к БД")
    db_connections_idle: int = Field(..., ge=0, description="Неактивные подключения к БД")
    uptime_seconds: int = Field(..., ge=0, description="Uptime системы в секундах")
    collected_at: datetime = Field(..., description="Время сбора метрик (ISO 8601)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cpu_percent": 23.5,
                "ram_percent": 45.2,
                "disk_percent": 67.8,
                "db_connections_active": 3,
                "db_connections_idle": 2,
                "uptime_seconds": 86400,
                "collected_at": "2025-01-15T10:30:00Z"
            }
        }
    )


class ActivityEventResponse(BaseModel):
    """Событие активности системы."""
    
    id: int = Field(..., description="Уникальный ID события")
    type: str = Field(..., description="Тип события")
    message: str = Field(..., description="Текст сообщения")
    user_email: Optional[str] = Field(None, description="Email пользователя (если есть)")
    details: Optional[dict[str, Any]] = Field(None, description="Дополнительные данные")
    created_at: datetime = Field(..., description="Время создания события (ISO 8601)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "user_login",
                "message": "Пользователь вошёл в систему",
                "user_email": "user@example.com",
                "details": {"ip": "192.168.1.1"},
                "created_at": "2025-01-15T10:30:00Z"
            }
        }
    )


class ActivityEventsListResponse(BaseModel):
    """Список событий активности с пагинацией."""
    
    events: list[ActivityEventResponse] = Field(..., description="Список событий")
    total: int = Field(..., ge=0, description="Общее количество событий")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [
                    {
                        "id": 1,
                        "type": "stream_start",
                        "message": "Стрим запущен",
                        "user_email": "admin@example.com",
                        "details": None,
                        "created_at": "2025-01-15T10:30:00Z"
                    }
                ],
                "total": 42
            }
        }
    )


class ActivityEventCreate(BaseModel):
    """Создание нового события активности (внутреннее использование)."""
    
    type: str = Field(..., min_length=1, max_length=50, description="Тип события")
    message: str = Field(..., min_length=1, max_length=500, description="Текст сообщения")
    user_email: Optional[str] = Field(None, max_length=255, description="Email пользователя")
    details: Optional[dict[str, Any]] = Field(None, description="Дополнительные данные")
