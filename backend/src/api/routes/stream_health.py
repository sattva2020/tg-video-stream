"""
Stream Health API Routes.

API endpoints for monitoring stream health and managing recovery operations.
Создан в рамках Feature 001 (Intelligent Auto-Recovery System).

Endpoints:
- GET /api/streams/{stream_id}/health - Get stream health status
- GET /api/streams/{stream_id}/recovery-logs - Get recovery logs for a stream
- POST /api/streams/{stream_id}/recover - Trigger manual recovery
- POST /api/streams/{stream_id}/reset-circuit-breaker - Reset circuit breaker
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.stream import Stream
from src.models.recovery_log import RecoveryLog, RecoveryFailureType, RecoveryStatus
from src.services.stream_health_monitor import (
    StreamHealthMonitor,
    get_stream_health_monitor,
    StreamHealthStatus
)
from src.services.stream_recovery_service import (
    StreamRecoveryService,
    get_stream_recovery_service,
    RecoveryConfig
)
from api.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class StreamHealthResponse(BaseModel):
    """Ответ со статусом здоровья потока."""
    stream_id: str
    is_healthy: bool
    last_check: str
    consecutive_failures: int
    last_failure_type: Optional[str] = None
    last_failure_time: Optional[str] = None
    last_error_message: Optional[str] = None
    uptime_seconds: Optional[int] = None
    total_checks: int = 0
    failed_checks: int = 0
    circuit_breaker_state: Optional[str] = None
    circuit_breaker_open_until: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecoveryLogResponse(BaseModel):
    """Ответ с информацией о попытке восстановления."""
    id: uuid.UUID
    stream_id: uuid.UUID
    failure_type: str
    failure_reason: str
    error_code: Optional[str] = None
    recovery_strategy: str
    status: str
    attempt_number: int
    max_attempts: int
    backoff_seconds: Optional[int] = None
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error_details: Optional[dict] = None
    recovery_metadata: Optional[dict] = None
    circuit_breaker_state: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class RecoveryStatsResponse(BaseModel):
    """Ответ со статистикой восстановления для потока."""
    stream_id: uuid.UUID
    total_recoveries: int
    successful_recoveries: int
    failed_recoveries: int
    abandoned_recoveries: int
    average_recovery_time_ms: Optional[float] = None
    last_recovery_time: Optional[str] = None
    last_failure_type: Optional[str] = None
    current_circuit_breaker_state: str


class ManualRecoveryRequest(BaseModel):
    """Запрос на ручное восстановление потока."""
    failure_type: RecoveryFailureType
    failure_reason: str
    error_code: Optional[str] = None
    force: bool = False  # Игнорировать circuit breaker


class ManualRecoveryResponse(BaseModel):
    """Ответ на запрос ручного восстановления."""
    success: bool
    message: str
    recovery_log_id: Optional[uuid.UUID] = None
    strategy_used: Optional[str] = None
    circuit_breaker_opened: bool = False


# ============================================================================
# Health Status Endpoints
# ============================================================================

@router.get("/{stream_id}/health", response_model=StreamHealthResponse)
async def get_stream_health(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить статус здоровья потока.

    Возвращает текущее состояние здоровья, включая информацию о circuit breaker.
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа (владелец или админ)
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this stream's health"
        )

    try:
        # Получаем мониторинг здоровья
        monitor = get_stream_health_monitor()
        health_status = await monitor.get_stream_health(str(stream_id))

        if not health_status:
            # Если нет данных в Redis, возвращаем статус с дефолтными значениями
            health_status = StreamHealthStatus(
                stream_id=str(stream_id),
                is_healthy=True,
                last_check=datetime.utcnow(),
                consecutive_failures=0,
                total_checks=0,
                failed_checks=0
            )

        # Получаем информацию о circuit breaker
        circuit_breaker_info = monitor.get_circuit_breaker_info(str(stream_id))

        response_data = {
            "stream_id": health_status.stream_id,
            "is_healthy": health_status.is_healthy,
            "last_check": health_status.last_check.isoformat(),
            "consecutive_failures": health_status.consecutive_failures,
            "last_failure_type": health_status.last_failure_type,
            "last_failure_time": health_status.last_failure_time.isoformat() if health_status.last_failure_time else None,
            "last_error_message": health_status.last_error_message,
            "uptime_seconds": health_status.uptime_seconds,
            "total_checks": health_status.total_checks,
            "failed_checks": health_status.failed_checks,
            "circuit_breaker_state": circuit_breaker_info.get("state") if circuit_breaker_info else None,
            "circuit_breaker_open_until": circuit_breaker_info.get("open_until") if circuit_breaker_info else None
        }

        return StreamHealthResponse(**response_data)

    except Exception as e:
        logger.error(f"Error getting stream health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stream health: {str(e)}"
        )


@router.get("/{stream_id}/recovery-logs", response_model=List[RecoveryLogResponse])
async def get_recovery_logs(
    stream_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Максимальное количество записей"),
    status_filter: Optional[RecoveryStatus] = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить логи восстановления для потока.

    Возвращает историю попыток восстановления с возможностью фильтрации.
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this stream's recovery logs"
        )

    try:
        # Строим запрос
        query = db.query(RecoveryLog).filter(RecoveryLog.stream_id == stream_id)

        # Применяем фильтр по статусу
        if status_filter:
            query = query.filter(RecoveryLog.status == status_filter)

        # Сортируем по убыванию даты начала
        query = query.order_by(RecoveryLog.started_at.desc())

        # Применяем пагинацию
        logs = query.offset(skip).limit(limit).all()

        # Конвертируем datetime в ISO format
        return [
            RecoveryLogResponse(
                id=log.id,
                stream_id=log.stream_id,
                failure_type=log.failure_type.value,
                failure_reason=log.failure_reason,
                error_code=log.error_code,
                recovery_strategy=log.recovery_strategy.value,
                status=log.status.value,
                attempt_number=log.attempt_number,
                max_attempts=log.max_attempts,
                backoff_seconds=log.backoff_seconds,
                started_at=log.started_at.isoformat(),
                completed_at=log.completed_at.isoformat() if log.completed_at else None,
                duration_ms=log.duration_ms,
                error_details=log.error_details,
                recovery_metadata=log.recovery_metadata,
                circuit_breaker_state=log.circuit_breaker_state
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Error getting recovery logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recovery logs: {str(e)}"
        )


@router.get("/{stream_id}/recovery-stats", response_model=RecoveryStatsResponse)
async def get_recovery_stats(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить статистику восстановления для потока.

    Возвращает агрегированную статистику по попыткам восстановления.
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this stream's recovery stats"
        )

    try:
        # Используем StreamRecoveryService для получения статистики
        recovery_service = get_stream_recovery_service(db)
        stats = recovery_service.get_recovery_stats(stream_id)

        return RecoveryStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting recovery stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recovery stats: {str(e)}"
        )


# ============================================================================
# Manual Recovery Endpoints
# ============================================================================

@router.post("/{stream_id}/recover", response_model=ManualRecoveryResponse)
async def trigger_manual_recovery(
    stream_id: uuid.UUID,
    request: ManualRecoveryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Запустить ручное восстановление потока.

    Позволяет вручную инициировать процесс восстановления с указанием типа сбоя.
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to recover this stream"
        )

    try:
        # Получаем сервис восстановления
        recovery_service = get_stream_recovery_service(db)

        # Если force=True, игнорируем circuit breaker
        if request.force:
            # Сбрасываем circuit breaker перед восстановлением
            recovery_service.reset_circuit_breaker(stream_id)

        # Запускаем восстановление
        result = recovery_service.recover_stream(
            stream_id=stream_id,
            failure_type=request.failure_type,
            failure_reason=request.failure_reason,
            error_code=request.error_code
        )

        if result["success"]:
            return ManualRecoveryResponse(
                success=True,
                message="Stream recovery initiated successfully",
                recovery_log_id=result.get("recovery_log_id"),
                strategy_used=result.get("strategy"),
                circuit_breaker_opened=result.get("circuit_breaker_opened", False)
            )
        else:
            error_detail = result.get("error", "Unknown error")
            circuit_breaker_opened = result.get("circuit_breaker_opened", False)

            # Если circuit breaker открыт, возвращаем 503 Service Unavailable
            if circuit_breaker_opened or "circuit breaker" in error_detail.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Circuit breaker is open: {error_detail}"
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Recovery failed: {error_detail}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual recovery: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger recovery: {str(e)}"
        )


@router.post("/{stream_id}/reset-circuit-breaker")
async def reset_stream_circuit_breaker(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Сбросить circuit breaker для потока.

    Позволяет вручную сбросить circuit breaker после разрешения проблем.
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reset this stream's circuit breaker"
        )

    try:
        # Сбрасываем circuit breaker
        recovery_service = get_stream_recovery_service(db)
        recovery_service.reset_circuit_breaker(stream_id)

        return {
            "ok": True,
            "message": "Circuit breaker reset successfully",
            "stream_id": str(stream_id)
        }

    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.post("/{stream_id}/reset-health")
async def reset_stream_health(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Сбросить статус здоровья потока.

    Позволяет вручную сбросить метрики здоровья (счётчики отказов, etc.).
    """
    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    # Проверяем права доступа
    if stream.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reset this stream's health"
        )

    try:
        # Сбрасываем здоровье через монитор
        monitor = get_stream_health_monitor()
        await monitor.reset_stream_health(str(stream_id))

        return {
            "ok": True,
            "message": "Stream health reset successfully",
            "stream_id": str(stream_id)
        }

    except Exception as e:
        logger.error(f"Error resetting stream health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset stream health: {str(e)}"
        )
