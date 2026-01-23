"""
System Monitoring API Router
Spec: 015-real-system-monitoring

FRAMEWORKS LAYER
Dependencies: Infrastructure ✅ (metrics_service, activity_service)

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
    "/tls/config",
    summary="Получить TLS/HTTPS конфигурацию",
    description="""
    Возвращает текущую TLS/HTTPS конфигурацию приложения:
    - TLS статус (enabled/disabled)
    - Пути к сертификатам
    - Настройки HSTS
    - Security headers статус
    - Валидность сертификата

    Используется для верификации TLS конфигурации и compliance reporting.
    """,
    responses={
        200: {
            "description": "TLS конфигурация получена",
            "content": {
                "application/json": {
                    "example": {
                        "production_mode": False,
                        "tls_enabled": False,
                        "tls_cert_path": None,
                        "tls_key_path": None,
                        "https_enforced": False,
                        "hsts_enabled": False,
                        "security_headers_enabled": True
                    }
                }
            }
        }
    }
)
async def get_tls_config():
    """
    Получает текущую TLS/HTTPS конфигурацию приложения.
    """
    from src.frameworks.http.middleware.tls_security import get_tls_config_info
    return get_tls_config_info()


@router.get(
    "/tls/certificate",
    summary="Проверить TLS сертификат",
    description="""
    Проверяет валидность TLS сертификата если он настроен:
    - Срок действия (valid from/until)
    - Дней до истечения
    - Статус (valid/expiring/expired)
    - Информация об издателе и субъекте
    - Предупреждения если сертификат истекает или недействителен

    Используется для мониторинга сертификатов и compliance reporting.
    """,
    responses={
        200: {
            "description": "Информация о сертификате",
            "content": {
                "application/json": {
                    "example": {
                        "valid_from": "2025-01-01T00:00:00Z",
                        "valid_until": "2026-01-01T00:00:00Z",
                        "days_until_expiry": 365,
                        "is_expired": False,
                        "is_not_yet_valid": False,
                        "is_valid": True,
                        "status": "valid",
                        "warning": None,
                        "issuer": "CN=Example CA",
                        "subject": "CN=example.com"
                    }
                }
            }
        },
        404: {
            "description": "Сертификат не настроен или файл не найден",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Certificate file not found"
                    }
                }
            }
        }
    }
)
async def check_tls_certificate():
    """
    Проверяет валидность TLS сертификата.
    """
    from src.core.config import settings
    from src.lib.tls_validator import check_cert_expiry, TLSCertificateError

    if not settings.TLS_ENABLED:
        return {
            "tls_enabled": False,
            "message": "TLS is not enabled in configuration"
        }

    try:
        cert_info = check_cert_expiry(settings.TLS_CERT_PATH)
        cert_info["tls_enabled"] = True
        cert_info["cert_path"] = settings.TLS_CERT_PATH
        return cert_info
    except TLSCertificateError as e:
        return {
            "tls_enabled": True,
            "error": str(e),
            "cert_path": settings.TLS_CERT_PATH
        }


@router.get(
    "/tls/status",
    summary="Комплексный статус TLS безопасности",
    description="""
    Возвращает комплексный статус TLS/HTTPS безопасности включая:
    - Конфигурацию TLS
    - Валидность сертификата
    - Проверку цепочки сертификатов
    - Предупреждения и рекомендации
    - Статус compliance

    Используется для security dashboard и compliance reporting.
    """,
    responses={
        200: {
            "description": "Статус TLS безопасности",
            "content": {
                "application/json": {
                    "example": {
                        "tls_enabled": False,
                        "environment": "development",
                        "certificate_valid": None,
                        "certificate_expiry": None,
                        "warnings": [],
                        "recommendations": []
                    }
                }
            }
        }
    }
)
async def get_tls_security_status():
    """
    Получает комплексный статус TLS/HTTPS безопасности.
    """
    from src.lib.tls_validator import get_tls_configuration_status
    return get_tls_configuration_status()


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
