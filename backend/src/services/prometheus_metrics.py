"""
Prometheus Metrics Service

Централизованное определение всех Prometheus метрик для Sattva Streamer.

Метрики:
- sattva_active_streams: Количество активных стримов
- sattva_queue_size: Размер очереди по каналам
- sattva_stream_listeners: Слушатели по каналам
- sattva_stream_duration_seconds: Распределение длительности стримов
- sattva_queue_operations_total: Операции с очередью
- sattva_auto_end_total: Триггеры auto-end
- sattva_websocket_connections: WebSocket соединения
- sattva_http_requests_total: HTTP запросы
- sattva_http_request_duration_seconds: Latency запросов

Использование:
    from src.services.prometheus_metrics import (
        ACTIVE_STREAMS,
        QUEUE_SIZE,
        record_queue_operation,
    )
    
    ACTIVE_STREAMS.inc()
    QUEUE_SIZE.labels(channel_id="-1001234567890").set(5)
    record_queue_operation("-1001234567890", "add")
"""

import logging
from typing import Optional, Callable, Dict
from functools import wraps
import time

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Stream Metrics
# ==============================================================================

ACTIVE_STREAMS = Gauge(
    'sattva_active_streams',
    'Number of currently active streams'
)

QUEUE_SIZE = Gauge(
    'sattva_queue_size',
    'Queue size per channel',
    ['channel_id']
)

LISTENERS_COUNT = Gauge(
    'sattva_stream_listeners',
    'Number of listeners per stream',
    ['channel_id']
)

STREAM_DURATION = Histogram(
    'sattva_stream_duration_seconds',
    'Stream duration distribution in seconds',
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400)  # 1m, 5m, 10m, 30m, 1h, 2h, 4h
)

CURRENT_TRACK_DURATION = Gauge(
    'sattva_current_track_duration_seconds',
    'Duration of currently playing track',
    ['channel_id']
)

CURRENT_TRACK_POSITION = Gauge(
    'sattva_current_track_position_seconds',
    'Current position in track',
    ['channel_id']
)


# ==============================================================================
# Queue Metrics
# ==============================================================================

QUEUE_OPERATIONS = Counter(
    'sattva_queue_operations_total',
    'Total queue operations',
    ['channel_id', 'operation']
)

QUEUE_ITEMS_ADDED = Counter(
    'sattva_queue_items_added_total',
    'Total items added to queue',
    ['channel_id', 'source']
)

QUEUE_ITEMS_REMOVED = Counter(
    'sattva_queue_items_removed_total',
    'Total items removed from queue',
    ['channel_id', 'reason']
)


# ==============================================================================
# Auto-End Metrics
# ==============================================================================

AUTO_END_TRIGGERS = Counter(
    'sattva_auto_end_total',
    'Auto-end triggers',
    ['channel_id', 'reason']
)

AUTO_END_TIMER_ACTIVE = Gauge(
    'sattva_auto_end_timer_active',
    'Whether auto-end timer is active',
    ['channel_id']
)

PLACEHOLDER_ACTIVE = Gauge(
    'sattva_placeholder_active',
    'Whether placeholder audio is playing',
    ['channel_id']
)


# ==============================================================================
# WebSocket Metrics
# ==============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    'sattva_websocket_connections',
    'Active WebSocket connections',
    ['channel_id']
)

WEBSOCKET_MESSAGES_SENT = Counter(
    'sattva_websocket_messages_sent_total',
    'Total WebSocket messages sent',
    ['channel_id', 'message_type']
)

WEBSOCKET_MESSAGES_RECEIVED = Counter(
    'sattva_websocket_messages_received_total',
    'Total WebSocket messages received',
    ['channel_id', 'message_type']
)


# ==============================================================================
# HTTP Metrics
# ==============================================================================

HTTP_REQUESTS = Counter(
    'sattva_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

HTTP_REQUEST_DURATION = Histogram(
    'sattva_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    'sattva_http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'path']
)


# ==============================================================================
# System Metrics (дополнение к MetricsService)
# ==============================================================================

APP_INFO = Gauge(
    'sattva_app_info',
    'Application information',
    ['version', 'python_version', 'environment']
)

APP_UPTIME = Gauge(
    'sattva_app_uptime_seconds',
    'Application uptime in seconds'
)


# ==============================================================================
# Admin Panel Metrics
# ==============================================================================

ADMIN_ACTIONS = Counter(
    'sattva_admin_actions_total',
    'Total admin panel actions',
    ['action', 'model']
)

ADMIN_SESSIONS = Gauge(
    'sattva_admin_sessions_active',
    'Active admin sessions'
)


# ==============================================================================
# Helper Functions
# ==============================================================================

def record_queue_operation(
    channel_id: int | str,
    operation: str
) -> None:
    """
    Записать операцию с очередью.
    
    Args:
        channel_id: ID канала
        operation: Тип операции (add, remove, move, clear, skip, priority_add)
    """
    QUEUE_OPERATIONS.labels(
        channel_id=str(channel_id),
        operation=operation
    ).inc()


def record_queue_item_added(
    channel_id: int | str,
    source: str
) -> None:
    """
    Записать добавление элемента в очередь.
    
    Args:
        channel_id: ID канала
        source: Источник (youtube, file, stream)
    """
    QUEUE_ITEMS_ADDED.labels(
        channel_id=str(channel_id),
        source=source
    ).inc()


def record_queue_item_removed(
    channel_id: int | str,
    reason: str
) -> None:
    """
    Записать удаление элемента из очереди.
    
    Args:
        channel_id: ID канала
        reason: Причина (played, skipped, removed, cleared)
    """
    QUEUE_ITEMS_REMOVED.labels(
        channel_id=str(channel_id),
        reason=reason
    ).inc()


def set_queue_size(
    channel_or_size: int | str,
    size: int | None = None,
    *,
    channel_id: int | str | None = None,
) -> None:
    """Установить размер очереди для канала (поддерживает старый и новый синтаксис)."""

    if channel_id is not None:
        queue_size = int(channel_or_size)
        channel_value = channel_id
    else:
        if size is None:
            raise ValueError("`size` is required when channel_id keyword не указан")
        channel_value = channel_or_size
        queue_size = size

    QUEUE_SIZE.labels(channel_id=str(channel_value)).set(int(queue_size))


def set_listeners_count(channel_id: int | str, count: int) -> None:
    """Установить количество слушателей для канала."""
    LISTENERS_COUNT.labels(channel_id=str(channel_id)).set(int(count))


def set_total_listeners(count: int, channel_id: int | str | None = None) -> None:
    """Совместимый alias для установки количества слушателей (используется в тестах)."""
    target_channel = channel_id if channel_id is not None else "global"
    set_listeners_count(target_channel, count)


def set_active_streams(count: int) -> None:
    """Установить количество активных стримов."""
    ACTIVE_STREAMS.set(max(0, int(count)))


def inc_active_streams(step: int = 1) -> None:
    """Инкрементировать количество активных стримов."""
    ACTIVE_STREAMS.inc(step)


def dec_active_streams(step: int = 1) -> None:
    """Декрементировать количество активных стримов (не опускаясь ниже нуля)."""
    ACTIVE_STREAMS.dec(step)


def record_auto_end(channel_id: int | str, reason: str) -> None:
    """
    Записать срабатывание auto-end.
    
    Args:
        channel_id: ID канала
        reason: Причина (timeout, no_listeners, queue_empty, manual)
    """
    AUTO_END_TRIGGERS.labels(
        channel_id=str(channel_id),
        reason=reason
    ).inc()


def set_auto_end_timer(channel_id: int | str, active: bool) -> None:
    """Установить статус auto-end таймера."""
    AUTO_END_TIMER_ACTIVE.labels(channel_id=str(channel_id)).set(1 if active else 0)


def set_placeholder_active(channel_id: int | str, active: bool) -> None:
    """Установить статус placeholder."""
    PLACEHOLDER_ACTIVE.labels(channel_id=str(channel_id)).set(1 if active else 0)


def record_websocket_message(
    channel_id: int | str,
    message_type: str,
    direction: str = "sent"
) -> None:
    """
    Записать WebSocket сообщение.
    
    Args:
        channel_id: ID канала
        message_type: Тип сообщения (queue_update, stream_state, auto_end_warning, etc.)
        direction: Направление (sent, received)
    """
    if direction == "sent":
        WEBSOCKET_MESSAGES_SENT.labels(
            channel_id=str(channel_id),
            message_type=message_type
        ).inc()
    else:
        WEBSOCKET_MESSAGES_RECEIVED.labels(
            channel_id=str(channel_id),
            message_type=message_type
        ).inc()


def set_websocket_connections(
    channel_or_count: int | str,
    count: int | None = None,
    *,
    channel_id: int | str | None = None,
) -> None:
    """Установить количество WebSocket соединений (поддержка старого вызова)."""

    if channel_id is not None:
        value = int(channel_or_count)
        channel_value = channel_id
    elif count is None:
        channel_value = "global"
        value = channel_or_count
    else:
        channel_value = channel_or_count
        value = count

    WEBSOCKET_CONNECTIONS.labels(channel_id=str(channel_value)).set(int(value))


def record_http_request(
    method: str,
    path: str,
    status: int,
    duration: float | None = None
) -> None:
    """
    Записать HTTP запрос.
    
    Args:
        method: HTTP метод (GET, POST, etc.)
        path: Путь запроса (нормализованный)
        status: HTTP статус код
        duration: Время выполнения в секундах
    """
    # Нормализация пути для метрик (заменяем динамические части)
    normalized_path = _normalize_path(path)
    
    HTTP_REQUESTS.labels(
        method=method,
        path=normalized_path,
        status=str(status)
    ).inc()

    if duration is not None:
        HTTP_REQUEST_DURATION.labels(
            method=method,
            path=normalized_path
        ).observe(max(duration, 0.0))


def record_http_duration(
    method: str,
    path: str,
    status: int,
    duration: float
) -> None:
    """Совместимый alias для записи длительности HTTP-запроса."""
    record_http_request(method=method, path=path, status=status, duration=duration)


def record_admin_action(action: str, model: str) -> None:
    """
    Записать действие в админ-панели.
    
    Args:
        action: Тип действия (create, update, delete, view, login, logout)
        model: Название модели (User, Playlist, Stream)
    """
    ADMIN_ACTIONS.labels(action=action, model=model).inc()


def _normalize_path(path: str) -> str:
    """
    Нормализация пути для метрик.
    
    Заменяет динамические части (ID, UUID) на плейсхолдеры.
    
    Examples:
        /api/v1/queue/123 → /api/v1/queue/{channel_id}
        /api/v1/queue/123/items/abc-def → /api/v1/queue/{channel_id}/items/{item_id}
    """
    import re
    
    # Заменяем UUID
    path = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '{uuid}',
        path,
        flags=re.IGNORECASE
    )
    
    # Заменяем числовые ID (включая отрицательные channel_id)
    path = re.sub(r'/-?\d+(?=/|$)', '/{id}', path)
    
    return path


def track_time(
    histogram: Histogram,
    labels: Optional[dict] = None
) -> Callable:
    """
    Декоратор для измерения времени выполнения функции.
    
    Args:
        histogram: Prometheus Histogram
        labels: Дополнительные labels
        
    Example:
        @track_time(HTTP_REQUEST_DURATION, {"method": "GET", "path": "/api/health"})
        async def health_check():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def get_metrics() -> bytes:
    """
    Получить все метрики в формате Prometheus.
    
    Returns:
        Метрики в text format для /metrics endpoint
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Получить Content-Type для /metrics endpoint."""
    return CONTENT_TYPE_LATEST


def reset_channel_metrics(channel_id: int | str) -> None:
    """
    Сбросить все метрики для канала при завершении стрима.
    
    Args:
        channel_id: ID канала
    """
    channel_str = str(channel_id)
    
    try:
        QUEUE_SIZE.labels(channel_id=channel_str).set(0)
        LISTENERS_COUNT.labels(channel_id=channel_str).set(0)
        AUTO_END_TIMER_ACTIVE.labels(channel_id=channel_str).set(0)
        PLACEHOLDER_ACTIVE.labels(channel_id=channel_str).set(0)
        WEBSOCKET_CONNECTIONS.labels(channel_id=channel_str).set(0)
        CURRENT_TRACK_DURATION.labels(channel_id=channel_str).set(0)
        CURRENT_TRACK_POSITION.labels(channel_id=channel_str).set(0)
    except Exception as e:
        logger.warning(f"Error resetting channel metrics: {e}")


def init_app_info(version: str, python_version: str, environment: str) -> None:
    """
    Инициализировать информацию о приложении.
    
    Args:
        version: Версия приложения
        python_version: Версия Python
        environment: Окружение (development, production)
    """
    APP_INFO.labels(
        version=version,
        python_version=python_version,
        environment=environment
    ).set(1)


# ==============================================================================
# Prometheus Middleware для FastAPI
# ==============================================================================

class PrometheusMiddlewareConfig:
    """Конфигурация для Prometheus middleware."""
    
    # Пути, которые не отслеживаются
    EXCLUDED_PATHS = frozenset([
        '/metrics',
        '/health',
        '/healthz',
        '/ready',
        '/favicon.ico',
    ])
    
    # Паттерны путей для исключения
    EXCLUDED_PREFIXES = (
        '/static/',
        '/assets/',
    )
    
    @classmethod
    def should_track(cls, path: str) -> bool:
        """Проверить, нужно ли отслеживать путь."""
        if path in cls.EXCLUDED_PATHS:
            return False
        for prefix in cls.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return False
        return True


# ==============================================================================
# Aliases for middleware compatibility
# ==============================================================================

# Aliases for prometheus middleware
HTTP_REQUESTS_TOTAL = HTTP_REQUESTS
HTTP_REQUEST_DURATION_SECONDS = HTTP_REQUEST_DURATION

# Lowercase aliases expected by legacy tests
http_requests_total = HTTP_REQUESTS
http_request_duration_seconds = HTTP_REQUEST_DURATION
active_streams_gauge = ACTIVE_STREAMS
total_listeners_gauge = LISTENERS_COUNT
queue_size_gauge = QUEUE_SIZE
queue_operations_total = QUEUE_OPERATIONS
auto_end_total = AUTO_END_TRIGGERS
websocket_connections_gauge = WEBSOCKET_CONNECTIONS

# Helper aliases for backward compatibility
set_websocket_connections_gauge = set_websocket_connections


class PrometheusMetricsHelper:
    """Утилита для агрегирования текущих значений Prometheus-метрик."""

    def __init__(self) -> None:
        self.registry = REGISTRY

    def _sum_metric(self, metric) -> float:
        total = 0.0
        try:
            for metric_family in metric.collect():
                for sample in metric_family.samples:
                    if sample.name == metric._name:
                        total += sample.value
        except Exception as exc:  # pragma: no cover - защитный путь
            logger.debug("Failed to aggregate metric %s: %s", getattr(metric, "_name", "unknown"), exc)
        return total

    def get_current_values(self) -> Dict[str, Dict[str, float]]:
        """Вернуть сгруппированные значения для REST-эндпоинтов мониторинга."""
        return {
            "streams": {
                "active": self._sum_metric(ACTIVE_STREAMS),
                "listeners": self._sum_metric(LISTENERS_COUNT),
            },
            "queue": {
                "size": self._sum_metric(QUEUE_SIZE),
                "operations": self._sum_metric(QUEUE_OPERATIONS),
            },
            "http": {
                "requests": self._sum_metric(HTTP_REQUESTS),
                "duration_samples": self._sum_metric(HTTP_REQUEST_DURATION),
            },
            "auto_end": {
                "triggers": self._sum_metric(AUTO_END_TRIGGERS),
            }
        }


prometheus_helper = PrometheusMetricsHelper()
