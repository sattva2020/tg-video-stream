from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from api.auth import require_admin
from src.models.user import User
from src.services.stream_quality_service import get_stream_quality_service, StreamQualityService
from src.services.quality_trends_service import get_quality_trends_service, QualityTrendsService
from src.services.stream_controller import get_stream_controller
from src.schemas.stream_quality import (
    StreamQualityResponse,
    QualityTrendData,
    QualityAlertConfigUpdate,
    QualityAlertConfigResponse,
)

router = APIRouter()

@router.get("/current", response_model=StreamQualityResponse)
async def get_current_stream_quality(
    url: Optional[str] = None,
    force: bool = False,
    current_user: User = Depends(require_admin),
    quality_service: StreamQualityService = Depends(get_stream_quality_service)
):
    """
    Получить текущее качество потока.
    Если URL не указан, пытается получить URL из активного стрима.
    """
    if not url:
        controller = get_stream_controller()
        status = await controller.get_status()
        if status.get("is_streaming") and status.get("current_track"):
             # В реальном сценарии URL может быть сложнее получить, 
             # но для MVP берем из конфигурации или активного стрима
             # Здесь мы предполагаем, что URL можно получить или он передан
             pass
        
        # Fallback: если нет активного стрима, возвращаем ошибку или пустой ответ
        if not url:
             # Попробуем получить URL из настроек радио или дефолтный
             # Для MVP требуем URL явно, если нет активного стрима
             if not status.get("is_streaming"):
                 raise HTTPException(status_code=400, detail="No active stream found and no URL provided")
             
             # TODO: Получить реальный URL стрима
             url = "http://localhost:8000/stream.mp3" # Placeholder

    result = await quality_service.analyze_stream_quality(url, force=force)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to analyze stream quality")
        
    return result

@router.get("/history", response_model=QualityTrendData)
async def get_stream_quality_history(
    url: str,
    period: str = Query("24h", regex="^(1h|6h|12h|24h|7d|30d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Получить историю качества потока за указанный период.
    """
    # Преобразуем период в datetime
    now = datetime.utcnow()
    if period == "1h":
        start_time = now - timedelta(hours=1)
    elif period == "6h":
        start_time = now - timedelta(hours=6)
    elif period == "12h":
        start_time = now - timedelta(hours=12)
    elif period == "24h":
        start_time = now - timedelta(days=1)
    elif period == "7d":
        start_time = now - timedelta(days=7)
    elif period == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=1)

    return await trends_service.get_quality_trend(
        db=db,
        stream_url=url,
        period_start=start_time
    )

@router.put("/alerts", response_model=QualityAlertConfigResponse)
async def update_alert_config(
    config: QualityAlertConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Обновить настройки уведомлений для потока.
    """
    return await trends_service.set_alert_config(db, config)

@router.get("/alerts", response_model=QualityAlertConfigResponse)
async def get_alert_config(
    url: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Получить настройки уведомлений для потока.
    """
    # TODO: Implement get_alert_config in QualityTrendsService
    # For now, we can reuse set_alert_config logic or add a get method
    # Assuming get_alert_config exists or we query directly
    from src.models.stream_quality import QualityAlertConfig
    
    config = db.query(QualityAlertConfig).filter(
        QualityAlertConfig.stream_url == url
    ).first()
    
    if not config:
        # Return default
        return QualityAlertConfigResponse(
            stream_url=url,
            min_overall_quality="medium",
            is_enabled=True
        )
        
    return config
