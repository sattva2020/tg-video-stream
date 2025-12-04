# -*- coding: utf-8 -*-
"""
Sentry SDK интеграция для мониторинга ошибок и производительности.

Обеспечивает:
- Автоматический захват исключений
- Трейсинг запросов и транзакций
- Контекстная информация о пользователях
- Интеграция с FastAPI, Celery, SQLAlchemy
- Отслеживание производительности audio streaming

Пример использования:
    from src.instrumentation.sentry import init_sentry, capture_exception
    
    # В main.py при старте приложения
    init_sentry()
    
    # В коде для явного захвата ошибок
    try:
        risky_operation()
    except Exception as e:
        capture_exception(e, extra={"operation": "risky_operation"})
"""

import os
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Флаг инициализации Sentry
_sentry_initialized = False
_sentry_available = False

# Попытка импорта Sentry SDK
try:
    import sentry_sdk
    from sentry_sdk import capture_exception as _sentry_capture_exception
    from sentry_sdk import capture_message as _sentry_capture_message
    from sentry_sdk import set_user as _sentry_set_user
    from sentry_sdk import set_context as _sentry_set_context
    from sentry_sdk import add_breadcrumb as _sentry_add_breadcrumb
    from sentry_sdk import start_span as _sentry_start_span
    from sentry_sdk import configure_scope
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    _sentry_available = True
except ImportError:
    logger.warning("Sentry SDK не установлен. Мониторинг ошибок отключен.")
    _sentry_available = False


# Конфигурация по умолчанию
DEFAULT_CONFIG = {
    "dsn": None,
    "environment": "development",
    "release": None,
    "traces_sample_rate": 0.2,
    "profiles_sample_rate": 0.1,
    "send_default_pii": False,
    "max_breadcrumbs": 100,
    "attach_stacktrace": True,
    "in_app_include": ["src"],
    "in_app_exclude": ["venv", "site-packages"],
    "debug": False,
}


def get_sentry_config() -> Dict[str, Any]:
    """
    Получает конфигурацию Sentry из переменных окружения.
    
    Returns:
        Dict с настройками Sentry SDK
    """
    config = DEFAULT_CONFIG.copy()
    
    # DSN - обязательный для работы
    config["dsn"] = os.getenv("SENTRY_DSN")
    
    # Окружение
    config["environment"] = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    
    # Версия релиза
    config["release"] = os.getenv("SENTRY_RELEASE", os.getenv("APP_VERSION", "0.1.0"))
    
    # Частота трейсинга (0.0 - 1.0)
    traces_rate = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")
    try:
        config["traces_sample_rate"] = float(traces_rate)
    except ValueError:
        config["traces_sample_rate"] = 0.2
    
    # Частота профилирования
    profiles_rate = os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
    try:
        config["profiles_sample_rate"] = float(profiles_rate)
    except ValueError:
        config["profiles_sample_rate"] = 0.1
    
    # Отправка PII (личных данных)
    config["send_default_pii"] = os.getenv("SENTRY_SEND_PII", "false").lower() == "true"
    
    # Debug режим
    config["debug"] = os.getenv("SENTRY_DEBUG", "false").lower() == "true"
    
    return config


def traces_sampler(sampling_context: Dict[str, Any]) -> float:
    """
    Динамический семплер для транзакций.
    Позволяет настроить разную частоту для разных эндпоинтов.
    
    Args:
        sampling_context: Контекст транзакции
        
    Returns:
        Частота семплирования (0.0 - 1.0)
    """
    # Получаем информацию о транзакции
    transaction_name = sampling_context.get("transaction_context", {}).get("name", "")
    
    # Health check эндпоинты - не трейсим
    if "/health" in transaction_name or "/ready" in transaction_name:
        return 0.0
    
    # Metrics эндпоинты - минимальный трейсинг
    if "/metrics" in transaction_name:
        return 0.01
    
    # Audio streaming операции - более высокий приоритет
    audio_endpoints = ["/playback", "/radio", "/equalizer", "/queue", "/lyrics", "/shazam"]
    if any(ep in transaction_name for ep in audio_endpoints):
        return 0.5
    
    # WebSocket - средний приоритет
    if "/ws" in transaction_name:
        return 0.3
    
    # Остальное - стандартная частота из конфига
    return float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2"))


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Фильтр событий перед отправкой в Sentry.
    Позволяет модифицировать или отфильтровать события.
    
    Args:
        event: Событие для отправки
        hint: Дополнительная информация
        
    Returns:
        Модифицированное событие или None для отмены отправки
    """
    # Игнорируем ожидаемые исключения
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        
        # Пропускаем HTTP 4xx ошибки
        if exc_type.__name__ in ["HTTPException", "RequestValidationError"]:
            return None
        
        # Пропускаем отмены подключений
        if exc_type.__name__ in ["ConnectionResetError", "CancelledError"]:
            return None
    
    # Удаляем чувствительные данные из контекста запроса
    if "request" in event:
        request_data = event["request"]
        
        # Очищаем заголовки авторизации
        if "headers" in request_data:
            headers = request_data["headers"]
            sensitive_headers = ["Authorization", "Cookie", "X-API-Key", "X-Session-Token"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[Filtered]"
        
        # Очищаем cookies
        if "cookies" in request_data:
            request_data["cookies"] = "[Filtered]"
    
    return event


def before_send_transaction(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Фильтр транзакций перед отправкой.
    
    Args:
        event: Транзакция для отправки
        hint: Дополнительная информация
        
    Returns:
        Модифицированная транзакция или None для отмены
    """
    transaction_name = event.get("transaction", "")
    
    # Не отправляем транзакции health check
    if any(x in transaction_name for x in ["/health", "/ready", "/live"]):
        return None
    
    return event


def init_sentry(dsn: Optional[str] = None, **kwargs) -> bool:
    """
    Инициализирует Sentry SDK с заданной конфигурацией.
    
    Args:
        dsn: Sentry DSN (если не указан, берется из SENTRY_DSN)
        **kwargs: Дополнительные параметры конфигурации
        
    Returns:
        True если инициализация успешна, False иначе
    """
    global _sentry_initialized
    
    if not _sentry_available:
        logger.warning("Sentry SDK недоступен, мониторинг отключен")
        return False
    
    if _sentry_initialized:
        logger.debug("Sentry уже инициализирован")
        return True
    
    # Получаем конфигурацию
    config = get_sentry_config()
    
    # Переопределяем DSN если передан
    if dsn:
        config["dsn"] = dsn
    
    # Применяем дополнительные параметры
    config.update(kwargs)
    
    # Проверяем наличие DSN
    if not config["dsn"]:
        logger.info("SENTRY_DSN не задан, мониторинг ошибок отключен")
        return False
    
    try:
        # Настраиваем интеграции
        integrations = [
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ]
        
        # Инициализируем SDK
        sentry_sdk.init(
            dsn=config["dsn"],
            environment=config["environment"],
            release=config["release"],
            traces_sample_rate=config["traces_sample_rate"],
            profiles_sample_rate=config["profiles_sample_rate"],
            send_default_pii=config["send_default_pii"],
            max_breadcrumbs=config["max_breadcrumbs"],
            attach_stacktrace=config["attach_stacktrace"],
            in_app_include=config["in_app_include"],
            in_app_exclude=config["in_app_exclude"],
            debug=config["debug"],
            integrations=integrations,
            traces_sampler=traces_sampler,
            before_send=before_send,
            before_send_transaction=before_send_transaction,
        )
        
        _sentry_initialized = True
        logger.info(f"Sentry инициализирован: env={config['environment']}, release={config['release']}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации Sentry: {e}")
        return False


def capture_exception(
    exception: Optional[BaseException] = None,
    *,
    level: str = "error",
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    fingerprint: Optional[list] = None,
) -> Optional[str]:
    """
    Захватывает исключение и отправляет в Sentry.
    
    Args:
        exception: Исключение для захвата (None = текущее)
        level: Уровень серьезности (error, warning, info)
        extra: Дополнительные данные
        tags: Теги для фильтрации
        fingerprint: Кастомный fingerprint для группировки
        
    Returns:
        ID события в Sentry или None
    """
    if not _sentry_available or not _sentry_initialized:
        if exception:
            logger.exception(f"Exception (Sentry disabled): {exception}")
        return None
    
    with configure_scope() as scope:
        # Устанавливаем уровень
        scope.level = level
        
        # Добавляем дополнительные данные
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        # Добавляем теги
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Устанавливаем fingerprint
        if fingerprint:
            scope.fingerprint = fingerprint
        
        return _sentry_capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    *,
    extra: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Отправляет сообщение в Sentry.
    
    Args:
        message: Текст сообщения
        level: Уровень (info, warning, error)
        extra: Дополнительные данные
        tags: Теги для фильтрации
        
    Returns:
        ID события в Sentry или None
    """
    if not _sentry_available or not _sentry_initialized:
        logger.log(
            logging.ERROR if level == "error" else logging.WARNING if level == "warning" else logging.INFO,
            f"Message (Sentry disabled): {message}"
        )
        return None
    
    with configure_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        return _sentry_capture_message(message, level=level)


def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **extra_data,
) -> None:
    """
    Устанавливает контекст пользователя для последующих событий.
    
    Args:
        user_id: ID пользователя
        email: Email пользователя
        username: Имя пользователя
        **extra_data: Дополнительные данные о пользователе
    """
    if not _sentry_available or not _sentry_initialized:
        return
    
    user_data = {}
    if user_id:
        user_data["id"] = str(user_id)
    if email:
        user_data["email"] = email
    if username:
        user_data["username"] = username
    
    # Добавляем дополнительные данные
    user_data.update(extra_data)
    
    if user_data:
        _sentry_set_user(user_data)


def set_extra_context(name: str, data: Dict[str, Any]) -> None:
    """
    Устанавливает дополнительный контекст для событий.
    
    Args:
        name: Имя контекста
        data: Данные контекста
    """
    if not _sentry_available or not _sentry_initialized:
        return
    
    _sentry_set_context(name, data)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Добавляет breadcrumb для отслеживания действий.
    
    Args:
        message: Описание действия
        category: Категория (http, navigation, user, etc.)
        level: Уровень (debug, info, warning, error)
        data: Дополнительные данные
    """
    if not _sentry_available or not _sentry_initialized:
        return
    
    _sentry_add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


@contextmanager
def SentryContext(
    operation: str,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Контекстный менеджер для отслеживания операций.
    
    Пример:
        with SentryContext("audio.process", tags={"format": "mp3"}):
            process_audio(file)
    
    Args:
        operation: Название операции
        tags: Теги для фильтрации
        extra: Дополнительные данные
    """
    # Добавляем breadcrumb о начале операции
    add_breadcrumb(
        message=f"Starting: {operation}",
        category="operation",
        level="info",
        data=extra,
    )
    
    try:
        yield
        
        # Успешное завершение
        add_breadcrumb(
            message=f"Completed: {operation}",
            category="operation",
            level="info",
        )
        
    except Exception as e:
        # Захватываем исключение с контекстом
        capture_exception(
            e,
            extra={"operation": operation, **(extra or {})},
            tags={"operation": operation, **(tags or {})},
        )
        raise


def sentry_span(
    operation: str,
    description: Optional[str] = None,
):
    """
    Декоратор для создания Sentry span вокруг функции.
    
    Пример:
        @sentry_span("audio.transcode", description="Transcode audio file")
        async def transcode_audio(file_path: str):
            ...
    
    Args:
        operation: Название операции (будет op в span)
        description: Описание операции
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _sentry_available or not _sentry_initialized:
                return await func(*args, **kwargs)
            
            with _sentry_start_span(op=operation, description=description or func.__name__):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _sentry_available or not _sentry_initialized:
                return func(*args, **kwargs)
            
            with _sentry_start_span(op=operation, description=description or func.__name__):
                return func(*args, **kwargs)
        
        # Определяем, async функция или нет
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# Audio Streaming специфичные хелперы
# ============================================================================

def set_audio_context(
    track_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    stream_type: Optional[str] = None,
    bitrate: Optional[int] = None,
    format: Optional[str] = None,
):
    """
    Устанавливает контекст audio streaming для событий.
    
    Args:
        track_id: ID трека
        channel_id: ID канала
        stream_type: Тип стрима (file, radio, youtube)
        bitrate: Битрейт в kbps
        format: Формат аудио
    """
    context = {}
    if track_id:
        context["track_id"] = track_id
    if channel_id:
        context["channel_id"] = channel_id
    if stream_type:
        context["stream_type"] = stream_type
    if bitrate:
        context["bitrate"] = bitrate
    if format:
        context["format"] = format
    
    if context:
        set_extra_context("audio", context)


def capture_audio_error(
    exception: BaseException,
    operation: str,
    track_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    **extra,
) -> Optional[str]:
    """
    Захватывает ошибку audio streaming с специфичным контекстом.
    
    Args:
        exception: Исключение
        operation: Название операции (play, pause, seek, etc.)
        track_id: ID трека
        channel_id: ID канала
        **extra: Дополнительные данные
        
    Returns:
        ID события в Sentry
    """
    extra_data = {
        "operation": operation,
        "track_id": track_id,
        "channel_id": channel_id,
        **extra,
    }
    
    return capture_exception(
        exception,
        extra=extra_data,
        tags={
            "component": "audio_streaming",
            "operation": operation,
        },
    )


# ============================================================================
# Middleware для FastAPI
# ============================================================================

class SentryMiddleware:
    """
    Middleware для автоматической настройки Sentry контекста.
    Добавляет информацию о запросе и пользователе.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Устанавливаем контекст запроса
        if _sentry_available and _sentry_initialized:
            with configure_scope() as sentry_scope:
                # Добавляем информацию о запросе
                sentry_scope.set_tag("path", scope.get("path", "unknown"))
                sentry_scope.set_tag("method", scope.get("method", "unknown"))
                
                # Добавляем headers как контекст (без чувствительных данных)
                headers = dict(scope.get("headers", []))
                safe_headers = {
                    k.decode() if isinstance(k, bytes) else k: 
                    v.decode() if isinstance(v, bytes) else v
                    for k, v in headers.items()
                    if k not in [b"authorization", b"cookie", b"x-api-key"]
                }
                sentry_scope.set_context("request_headers", safe_headers)
        
        await self.app(scope, receive, send)


# ============================================================================
# Утилиты для тестирования
# ============================================================================

def is_sentry_initialized() -> bool:
    """Проверяет, инициализирован ли Sentry SDK."""
    return _sentry_initialized


def is_sentry_available() -> bool:
    """Проверяет, доступен ли Sentry SDK."""
    return _sentry_available


def test_sentry_connection() -> bool:
    """
    Тестирует подключение к Sentry отправкой тестового сообщения.
    
    Returns:
        True если сообщение отправлено успешно
    """
    if not _sentry_available or not _sentry_initialized:
        return False
    
    try:
        event_id = capture_message(
            "Sentry connection test",
            level="info",
            tags={"type": "test"},
        )
        return event_id is not None
    except Exception as e:
        logger.error(f"Sentry connection test failed: {e}")
        return False
