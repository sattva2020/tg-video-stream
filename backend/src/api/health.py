"""
Health API endpoints для мониторинга состояния сервиса.
Соответствует спецификации contracts/health-api.yaml
"""

import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
import redis

# Application start time для uptime calculation
_start_time = time.time()

# Version from environment or default
import os
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


router = APIRouter(prefix="/health", tags=["Health"])


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
    
    model_config = ConfigDict(from_attributes=True)


class LivenessResponse(BaseModel):
    """Ответ liveness probe."""
    status: str  # alive


class ReadinessResponse(BaseModel):
    """Ответ readiness probe."""
    status: str  # ready, not_ready
    reason: Optional[str] = None


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


def calculate_overall_status(dependencies: list[DependencyHealth]) -> str:
    """Определить общий статус на основе зависимостей."""
    statuses = [d.status for d in dependencies]
    
    if "down" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Возвращает текущее состояние сервиса и его зависимостей.
    Используется Docker health check и мониторингом.
    """
    dependencies = [
        check_database(),
        check_redis()
    ]
    
    overall_status = calculate_overall_status(dependencies)
    uptime = time.time() - _start_time
    
    response = HealthResponse(
        status=overall_status,
        version=APP_VERSION,
        uptime_seconds=round(uptime, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependencies
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
