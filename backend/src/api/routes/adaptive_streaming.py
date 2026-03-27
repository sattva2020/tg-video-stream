"""
Feature 009 Phase 2: Adaptive Streaming API Routes

API endpoints for managing adaptive streaming configuration and bandwidth detection.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime, timedelta

from database import get_db
from api.auth import require_admin
from src.models.user import User
from src.services.adaptive_streaming_service import (
    get_adaptive_streaming_service,
    AdaptiveStreamingService
)
from src.services.bandwidth_monitor import get_bandwidth_monitor, BandwidthMonitor
from src.schemas.adaptive_streaming import (
    BandwidthDetectionResponse,
    BandwidthDetectionRequest,
    AdaptiveStreamConfigCreate,
    AdaptiveStreamConfigUpdate,
    AdaptiveStreamConfigResponse,
    AdaptiveStreamingStatus,
    QualityChangeHistory,
    QualityLevel,
    DeviceType
)

router = APIRouter()


@router.get("/bandwidth", response_model=BandwidthDetectionResponse)
async def detect_bandwidth(
    stream_id: str,
    force_measurement: bool = False,
    timeout_seconds: int = 10,
    current_user: User = Depends(require_admin),
    bandwidth_monitor: BandwidthMonitor = Depends(get_bandwidth_monitor)
):
    """
    Определить пропускную способность сети и рекомендованное качество.

    Args:
        stream_id: ID потока (GUID)
        force_measurement: Принудительно измерить (игнорировать кэш)
        timeout_seconds: Таймаут измерения
        current_user: Текущий пользователь (admin required)
        bandwidth_monitor: Сервис мониторинга пропускной способности

    Returns:
        BandwidthDetectionResponse с результатами измерения
    """
    try:
        # Получаем или измеряем пропускную способность
        if force_measurement:
            status = await bandwidth_monitor.measure_bandwidth(stream_id)
        else:
            status = await bandwidth_monitor.get_bandwidth_status(stream_id)
            # Если нет данных, выполняем измерение
            if not status:
                status = await bandwidth_monitor.measure_bandwidth(stream_id)

        if not status:
            raise HTTPException(
                status_code=500,
                detail="Failed to measure bandwidth"
            )

        # Формируем ответ
        from src.schemas.adaptive_streaming import BandwidthMeasurement, DeviceType

        measurement = BandwidthMeasurement(
            bandwidth_kbps=status.smoothed_bandwidth_kbps,
            latency_ms=status.avg_latency_ms,
            packet_loss=None,
            measured_at=status.last_measurement,
            measurement_method="http",
            confidence=0.8 if status.measurements_count >= 3 else 0.5
        )

        # Определяем рекомендуемое качество
        recommended_quality_str = status.recommended_quality or "high"
        recommended_quality = QualityLevel(recommended_quality_str)

        return BandwidthDetectionResponse(
            stream_id=stream_id,
            measurement=measurement,
            recommended_quality=recommended_quality,
            current_config=None,  # Можно загрузить из базы если нужно
            device_type=DeviceType.UNKNOWN,
            success=True
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting bandwidth: {str(e)}"
        )


@router.get("/config/{stream_id}", response_model=AdaptiveStreamConfigResponse)
async def get_adaptive_config(
    stream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    adaptive_service: AdaptiveStreamingService = Depends(get_adaptive_streaming_service)
):
    """
    Получить конфигурацию адаптивного стрима для потока.

    Args:
        stream_id: ID потока (GUID)
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)
        adaptive_service: Сервис адаптивного стрима

    Returns:
        AdaptiveStreamConfigResponse с конфигурацией
    """
    from src.models.adaptive_stream_config import AdaptiveStreamConfig

    config = db.query(AdaptiveStreamConfig).filter(
        AdaptiveStreamConfig.stream_id == stream_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Adaptive streaming config not found for stream {stream_id}"
        )

    return config


@router.post("/config", response_model=AdaptiveStreamConfigResponse)
async def create_adaptive_config(
    config_data: AdaptiveStreamConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Создать новую конфигурацию адаптивного стрима.

    Args:
        config_data: Данные для создания конфигурации
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)

    Returns:
        AdaptiveStreamConfigResponse с созданной конфигурацией
    """
    from src.models.adaptive_stream_config import AdaptiveStreamConfig
    from src.models.stream import Stream

    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.guid == config_data.stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"Stream {config_data.stream_id} not found"
        )

    # Проверяем, что конфигурация еще не существует
    existing = db.query(AdaptiveStreamConfig).filter(
        AdaptiveStreamConfig.stream_id == config_data.stream_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Adaptive streaming config already exists for stream {config_data.stream_id}"
        )

    # Создаем конфигурацию
    config = AdaptiveStreamConfig(
        stream_id=config_data.stream_id,
        enabled=config_data.enabled,
        default_quality=config_data.default_quality.value,
        min_quality=config_data.min_quality.value,
        max_quality=config_data.max_quality.value,
        bandwidth_threshold_low_kbps=config_data.bandwidth_threshold_low_kbps,
        bandwidth_threshold_medium_kbps=config_data.bandwidth_threshold_medium_kbps,
        bandwidth_threshold_high_kbps=config_data.bandwidth_threshold_high_kbps,
        bandwidth_threshold_ultra_kbps=config_data.bandwidth_threshold_ultra_kbps,
        adaptation_interval_seconds=config_data.adaptation_interval_seconds,
        bandwidth_smoothing_factor=config_data.bandwidth_smoothing_factor,
        consecutive_measurements_required=config_data.consecutive_measurements_required,
        device_rules=config_data.device_rules,
        quality_profiles=config_data.quality_profiles,
        enable_bandwidth_monitoring=config_data.enable_bandwidth_monitoring,
        enable_quality_logging=config_data.enable_quality_logging
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.put("/config/{stream_id}", response_model=AdaptiveStreamConfigResponse)
async def update_adaptive_config(
    stream_id: str,
    config_data: AdaptiveStreamConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить конфигурацию адаптивного стрима.

    Args:
        stream_id: ID потока (GUID)
        config_data: Данные для обновления
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)

    Returns:
        AdaptiveStreamConfigResponse с обновленной конфигурацией
    """
    from src.models.adaptive_stream_config import AdaptiveStreamConfig

    config = db.query(AdaptiveStreamConfig).filter(
        AdaptiveStreamConfig.stream_id == stream_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Adaptive streaming config not found for stream {stream_id}"
        )

    # Обновляем только предоставленные поля
    update_data = config_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(config, field):
            # Конвертируем enum в строку если нужно
            if isinstance(value, QualityLevel):
                value = value.value
            setattr(config, field, value)

    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    return config


@router.delete("/config/{stream_id}")
async def delete_adaptive_config(
    stream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удалить конфигурацию адаптивного стрима.

    Args:
        stream_id: ID потока (GUID)
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)

    Returns:
        Сообщение об успешном удалении
    """
    from src.models.adaptive_stream_config import AdaptiveStreamConfig

    config = db.query(AdaptiveStreamConfig).filter(
        AdaptiveStreamConfig.stream_id == stream_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Adaptive streaming config not found for stream {stream_id}"
        )

    db.delete(config)
    db.commit()

    return {"message": f"Adaptive streaming config deleted for stream {stream_id}"}


@router.get("/status/{stream_id}", response_model=AdaptiveStreamingStatus)
async def get_adaptive_status(
    stream_id: str,
    device_type: DeviceType = DeviceType.UNKNOWN,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    adaptive_service: AdaptiveStreamingService = Depends(get_adaptive_streaming_service)
):
    """
    Получить полный статус адаптивного стрима.

    Args:
        stream_id: ID потока (GUID)
        device_type: Тип устройства для определения качества
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)
        adaptive_service: Сервис адаптивного стрима

    Returns:
        AdaptiveStreamingStatus с полным статусом
    """
    try:
        status = await adaptive_service.get_stream_status(
            stream_id=stream_id,
            db=db,
            device_type=device_type
        )

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Stream {stream_id} not found"
            )

        return status

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting adaptive status: {str(e)}"
        )


@router.get("/history/{stream_id}", response_model=QualityChangeHistory)
async def get_quality_history(
    stream_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    adaptive_service: AdaptiveStreamingService = Depends(get_adaptive_streaming_service)
):
    """
    Получить историю изменений качества для потока.

    Args:
        stream_id: ID потока (GUID)
        limit: Максимальное количество записей (1-200)
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)
        adaptive_service: Сервис адаптивного стрима

    Returns:
        QualityChangeHistory с событиями изменений качества
    """
    from src.models.stream import Stream

    # Проверяем существование потока
    stream = db.query(Stream).filter(Stream.guid == stream_id).first()

    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"Stream {stream_id} not found"
        )

    # Получаем историю из сервиса
    history = await adaptive_service.get_quality_history(stream_id, limit)

    # Конвертируем в формат ответа
    events = []
    for event_data in history:
        from src.schemas.adaptive_streaming import QualityChangeEvent

        event = QualityChangeEvent(
            id=0,  # В памяти нет ID из базы
            stream_id=stream_id,
            previous_quality=None,  # Можно извлечь из истории если нужно
            new_quality=QualityLevel(event_data["quality"]),
            bandwidth_kbps=event_data.get("bandwidth_kbps"),
            reason=event_data["reason"],
            device_type=DeviceType(event_data.get("device_type", "unknown")),
            triggered_at=datetime.fromisoformat(event_data["timestamp"])
        )
        events.append(event)

    # Текущее качество
    current_quality = QualityLevel.HIGH  # Default
    if history:
        current_quality = QualityLevel(history[-1]["quality"])

    return QualityChangeHistory(
        stream_id=stream_id,
        stream_name=getattr(stream, 'name', None),
        events=events,
        total_changes=len(events),
        current_quality=current_quality
    )


@router.post("/quality-select")
async def select_quality(
    stream_id: str,
    device_type: DeviceType = DeviceType.UNKNOWN,
    user_agent: Optional[str] = None,
    force_measurement: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    adaptive_service: AdaptiveStreamingService = Depends(get_adaptive_streaming_service)
):
    """
    Выбрать оптимальное качество для потока на основе текущих условий.

    Args:
        stream_id: ID потока (GUID)
        device_type: Тип устройства
        user_agent: User Agent строка для детекции устройства
        force_measurement: Принудительно измерить пропускную способность
        db: Сессия базы данных
        current_user: Текущий пользователь (admin required)
        adaptive_service: Сервис адаптивного стрима

    Returns:
        Результат выбора качества
    """
    try:
        decision = await adaptive_service.select_quality_for_stream(
            stream_id=stream_id,
            device_type=device_type,
            user_agent=user_agent,
            db=db,
            force_measurement=force_measurement
        )

        return {
            "stream_id": stream_id,
            "selected_quality": decision.quality.value,
            "reason": decision.reason.value,
            "bandwidth_kbps": decision.bandwidth_kbps,
            "device_type": decision.device_type.value,
            "confidence": decision.confidence
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error selecting quality: {str(e)}"
        )
