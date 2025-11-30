"""
System Monitoring API Router
Spec: 015-real-system-monitoring

Эндпоинты для получения системных метрик и событий активности.
Используется Dashboard компонентами SystemHealth и ActivityTimeline.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.api.schemas.system import (
    SystemMetricsResponse,
    ActivityEventsListResponse,
)
from src.services.metrics_service import get_metrics_service
from src.services.activity_service import get_activity_service


router = APIRouter()


@router.get(
    "/metrics",
    response_model=SystemMetricsResponse,
    summary="Получить системные метрики",
    description="""
    Возвращает текущие метрики системы:
    - CPU usage (%)
    - RAM usage (%)
    - Disk usage (%)
    - Активные/неактивные подключения к БД
    - Uptime приложения
    
    Используется компонентом SystemHealth на Dashboard.
    """,
    responses={
        200: {
            "description": "Системные метрики успешно получены",
            "content": {
                "application/json": {
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
            }
        }
    }
)
async def get_system_metrics(
    db: Session = Depends(get_db)
) -> SystemMetricsResponse:
    """
    Получает актуальные системные метрики через psutil и pg_stat_activity.
    """
    service = get_metrics_service(db)
    return service.collect_metrics()


@router.get(
    "/activity",
    response_model=ActivityEventsListResponse,
    summary="Получить события активности",
    description="""
    Возвращает список событий активности с пагинацией и фильтрацией.
    
    Типы событий:
    - user_login, user_logout — авторизация
    - stream_start, stream_stop, stream_error — стриминг
    - track_added, track_removed, playlist_updated — плейлист
    - system_warning, system_error — системные события
    
    Используется компонентом ActivityTimeline на Dashboard.
    """,
    responses={
        200: {
            "description": "Список событий успешно получен",
            "content": {
                "application/json": {
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
            }
        }
    }
)
async def get_activity_events(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Количество записей на странице (1-100)"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Смещение для пагинации"
    ),
    type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Фильтр по типу события (user_login, stream_start, etc.)"
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Поиск по тексту сообщения"
    ),
    db: Session = Depends(get_db)
) -> ActivityEventsListResponse:
    """
    Получает список событий активности с поддержкой пагинации и фильтрации.
    """
    service = get_activity_service(db)
    return service.get_events(
        limit=limit,
        offset=offset,
        event_type=type,
        search=search
    )
