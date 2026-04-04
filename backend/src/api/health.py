"""
Health API endpoints для мониторинга состояния сервиса.
Соответствует спецификации contracts/health-api.yaml
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
import redis
import psutil

log = logging.getLogger(__name__)

# Application start time для uptime calculation
_start_time = time.time()

# Version from environment or default
import os
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


router = APIRouter(prefix="/health", tags=["Health"])


class StreamDetails(BaseModel):
    """Детальная информация о потоках."""
    total_streams: int
    active_streams: int
    healthy_streams: int
    unhealthy_streams: int
    unhealthy_stream_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class DependencyHealth(BaseModel):
    """Состояние зависимости."""
    name: str
    status: str  # up, down, degraded
    latency_ms: float
    message: Optional[str] = None
    last_check: str

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Ответ health check."""
    status: str  # healthy, degraded, unhealthy
    version: str
    uptime_seconds: float
    timestamp: str
    dependencies: list[DependencyHealth]
    stream_details: Optional[StreamDetails] = None
    system_metrics: Optional[SystemMetrics] = None

    model_config = ConfigDict(from_attributes=True)


class LivenessResponse(BaseModel):
    """Ответ liveness probe."""
    status: str  # alive


class ReadinessResponse(BaseModel):
    """Ответ readiness probe."""
    status: str  # ready, not_ready
    reason: Optional[str] = None


class SystemMetrics(BaseModel):
    """Метрики использования системных ресурсов."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    memory_total_mb: float

    model_config = ConfigDict(from_attributes=True)


def check_database() -> DependencyHealth:
    """Проверка доступности PostgreSQL."""
    from src.database import get_db, SessionLocal
    
    start = time.time()
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            
            # Degraded если latency > 100ms
            if latency > 100:
                return DependencyHealth(
                    name="database",
                    status="degraded",
                    latency_ms=round(latency, 2),
                    message="High latency detected",
                    last_check=datetime.now(timezone.utc).isoformat()
                )
            
            return DependencyHealth(
                name="database",
                status="up",
                latency_ms=round(latency, 2),
                last_check=datetime.now(timezone.utc).isoformat()
            )
        finally:
            db.close()
    except Exception as e:
        return DependencyHealth(
            name="database",
            status="down",
            latency_ms=-1,
            message=str(e)[:100],  # Limit message length
            last_check=datetime.now(timezone.utc).isoformat()
        )


def check_redis() -> DependencyHealth:
    """Проверка доступности Redis."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    start = time.time()
    try:
        r = redis.from_url(redis_url, socket_timeout=5)
        r.ping()
        latency = (time.time() - start) * 1000

        # Degraded если latency > 50ms
        if latency > 50:
            return DependencyHealth(
                name="redis",
                status="degraded",
                latency_ms=round(latency, 2),
                message="High latency detected",
                last_check=datetime.now(timezone.utc).isoformat()
            )

        return DependencyHealth(
            name="redis",
            status="up",
            latency_ms=round(latency, 2),
            last_check=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return DependencyHealth(
            name="redis",
            status="down",
            latency_ms=-1,
            message=str(e)[:100],
            last_check=datetime.now(timezone.utc).isoformat()
        )


def check_streams() -> DependencyHealth:
    """Проверка здоровья потоков."""
    from src.database import SessionLocal
    from src.models.stream import Stream, StreamStatus
    from src.services.stream_health_monitor import get_stream_health_monitor

    start = time.time()
    try:
        db = SessionLocal()
        try:
            # Получить количество активных потоков из базы данных
            active_streams_count = db.query(Stream).filter(
                Stream.status == StreamStatus.ACTIVE
            ).count()

            # Если нет активных потоков, считаем это "up" (система работает)
            if active_streams_count == 0:
                latency = (time.time() - start) * 1000
                return DependencyHealth(
                    name="streams",
                    status="up",
                    latency_ms=round(latency, 2),
                    message="No active streams",
                    last_check=datetime.now(timezone.utc).isoformat()
                )

            # Получить монитор и проверить здоровье всех активных потоков
            monitor = get_stream_health_monitor()

            # Получить все нездоровые потоки (асинхронно)
            import asyncio
            try:
                # Попытаться получить event loop или создать новый
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                unhealthy_streams = loop.run_until_complete(
                    monitor.get_all_unhealthy_streams()
                )
            except Exception as async_error:
                # Если не удалось получить event loop, просто логируем предупреждение
                log.warning(f"Could not check stream health asynchronously: {async_error}")
                unhealthy_streams = []

            latency = (time.time() - start) * 1000

            # Если есть нездоровые потоки, но не все - degraded
            if unhealthy_streams and len(unhealthy_streams) < active_streams_count:
                return DependencyHealth(
                    name="streams",
                    status="degraded",
                    latency_ms=round(latency, 2),
                    message=f"{len(unhealthy_streams)}/{active_streams_count} streams unhealthy",
                    last_check=datetime.now(timezone.utc).isoformat()
                )

            # Если все активные потоки нездоровы - down
            if unhealthy_streams and len(unhealthy_streams) >= active_streams_count:
                return DependencyHealth(
                    name="streams",
                    status="down",
                    latency_ms=round(latency, 2),
                    message=f"All {active_streams_count} streams unhealthy",
                    last_check=datetime.now(timezone.utc).isoformat()
                )

            # Все потоки здоровы
            return DependencyHealth(
                name="streams",
                status="up",
                latency_ms=round(latency, 2),
                message=f"{active_streams_count} active streams healthy",
                last_check=datetime.now(timezone.utc).isoformat()
            )

        finally:
            db.close()
    except Exception as e:
        return DependencyHealth(
            name="streams",
            status="down",
            latency_ms=-1,
            message=str(e)[:100],
            last_check=datetime.now(timezone.utc).isoformat()
        )


def get_stream_details() -> StreamDetails:
    """Получить детальную информацию о потоках."""
    from src.database import SessionLocal
    from src.models.stream import Stream, StreamStatus
    from src.services.stream_health_monitor import get_stream_health_monitor

    try:
        db = SessionLocal()
        try:
            # Получить общую статистику
            total_streams = db.query(Stream).count()
            active_streams = db.query(Stream).filter(
                Stream.status == StreamStatus.ACTIVE
            ).count()

            # Если нет активных потоков, возвращаем базовую информацию
            if active_streams == 0:
                return StreamDetails(
                    total_streams=total_streams,
                    active_streams=active_streams,
                    healthy_streams=0,
                    unhealthy_streams=0,
                    unhealthy_stream_ids=[]
                )

            # Получить монитор и проверить здоровье всех активных потоков
            monitor = get_stream_health_monitor()
            unhealthy_stream_ids = []

            # Получить все нездоровые потоки (асинхронно)
            import asyncio
            try:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                unhealthy_streams = loop.run_until_complete(
                    monitor.get_all_unhealthy_streams()
                )
                unhealthy_stream_ids = [s.id for s in unhealthy_streams]
            except Exception as async_error:
                log.warning(f"Could not check stream health asynchronously: {async_error}")

            unhealthy_count = len(unhealthy_stream_ids)
            healthy_count = active_streams - unhealthy_count

            return StreamDetails(
                total_streams=total_streams,
                active_streams=active_streams,
                healthy_streams=healthy_count,
                unhealthy_streams=unhealthy_count,
                unhealthy_stream_ids=unhealthy_stream_ids
            )

        finally:
            db.close()
    except Exception as e:
        log.error(f"Error getting stream details: {e}")
        # Возвращаем пустую информацию в случае ошибки
        return StreamDetails(
            total_streams=0,
            active_streams=0,
            healthy_streams=0,
            unhealthy_streams=0,
            unhealthy_stream_ids=[]
        )


def calculate_overall_status(dependencies: list[DependencyHealth]) -> str:
    """Определить общий статус на основе зависимостей."""
    statuses = [d.status for d in dependencies]

    if "down" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


def get_system_metrics() -> Optional[SystemMetrics]:
    """Получить метрики использования системных ресурсов."""
    try:
        # CPU usage (как среднее за последние секунды)
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = round(memory.used / (1024 * 1024), 2)
        memory_available_mb = round(memory.available / (1024 * 1024), 2)
        memory_total_mb = round(memory.total / (1024 * 1024), 2)

        return SystemMetrics(
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory_percent, 2),
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            memory_total_mb=memory_total_mb
        )
    except Exception as e:
        log.warning(f"Failed to get system metrics: {e}")
        return None


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Возвращает текущее состояние сервиса и его зависимостей.
    Используется Docker health check и мониторингом.
    """
    dependencies = [
        check_database(),
        check_redis(),
        check_streams()
    ]

    overall_status = calculate_overall_status(dependencies)
    uptime = time.time() - _start_time
    stream_details = get_stream_details()
    system_metrics = get_system_metrics()

    response = HealthResponse(
        status=overall_status,
        version=APP_VERSION,
        uptime_seconds=round(uptime, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependencies,
        stream_details=stream_details,
        system_metrics=system_metrics
    )

    if overall_status == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump()
        )

    return response


@router.get("/live", response_model=LivenessResponse)
async def liveness_probe():
    """
    Простая проверка что приложение запущено.
    Не проверяет зависимости — только сам процесс.
    """
    return LivenessResponse(status="alive")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_probe():
    """
    Проверка готовности принимать трафик.
    Возвращает 200 только если все критические зависимости доступны.
    """
    db_health = check_database()
    redis_health = check_redis()
    
    if db_health.status == "down":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ReadinessResponse(
                status="not_ready",
                reason=f"Database: {db_health.message}"
            ).model_dump()
        )
    
    if redis_health.status == "down":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ReadinessResponse(
                status="not_ready",
                reason=f"Redis: {redis_health.message}"
            ).model_dump()
        )
    
    return ReadinessResponse(status="ready")
