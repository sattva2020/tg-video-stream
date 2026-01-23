"""
API endpoints для AI-функционала расписания.

Функционал:
- AI-рекомендации для расписания
- Оптимизация расписания
- Автопилот (автоматическая генерация расписания)
- Анализ пиковых часов
- Обнаружение и разрешение конфликтов
"""

import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from src.database import get_db
from src.api.auth import get_current_user, require_admin
from src.models.user import User
from src.services.schedule_recommendation_service import ScheduleRecommendationService
from src.services.schedule_optimization_service import ScheduleOptimizationService
from src.services.auto_pilot_service import AutoPilotService
from src.schemas.schedule_ai import (
    ScheduleOptimizationRequest,
    ScheduleOptimizationResponse,
    ScheduleRecommendationRequest,
    ScheduleRecommendationResponse,
    PeakHoursRequest,
    PeakHoursResponse,
    AutoPilotRequest,
    AutoPilotResponse,
    ConflictDetectionRequest,
    ConflictDetectionResponse,
    ConflictResolutionResponse,
    GapDetectionRequest,
    GapDetectionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule-ai", tags=["Schedule AI"])


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """
    Проверка работоспособности AI-сервиса расписания.

    Returns:
        dict: Статус сервиса
    """
    return {
        "status": "healthy",
        "service": "schedule-ai",
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== Recommendations ====================

@router.get("/recommendations", response_model=ScheduleRecommendationResponse)
async def get_recommendations(
    channel_id: str = Query(..., description="ID канала"),
    target_date: date = Query(..., description="Целевая дата (YYYY-MM-DD)"),
    recommendation_types: Optional[List[str]] = Query(None, description="Фильтр по типам"),
    max_recommendations: int = Query(10, ge=1, le=50, description="Макс. количество"),
    min_confidence: float = Query(50.0, ge=0, le=100, description="Мин. уверенность"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить AI-рекомендации для расписания.

    Возвращает рекомендации по контенту с учётом пиковых часов и вовлечённости.
    """
    try:
        service = ScheduleRecommendationService(db)
        recommendations = await service.get_recommendations(
            channel_id=channel_id,
            target_date=target_date,
            min_confidence=min_confidence / 100.0,  # Convert to 0-1 range
            limit=max_recommendations
        )

        items = recommendations.get("recommendations", [])
        high_conf_count = sum(1 for item in items if item.get("confidence_score", 0) >= min_confidence)

        return ScheduleRecommendationResponse(
            recommendations=items,
            total_count=len(items),
            high_confidence_count=high_conf_count,
            target_date=target_date,
            generated_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Optimization ====================

@router.post("/optimize/preview", response_model=ScheduleOptimizationResponse)
async def preview_optimization(
    request: ScheduleOptimizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Предпросмотр оптимизации расписания.

    Анализирует текущее расписание и предлагает улучшения без применения изменений.
    """
    try:
        service = ScheduleOptimizationService(db)

        # Create optimization ID
        optimization_id = str(uuid.uuid4())

        # Detect gaps and conflicts
        gaps = await service.detect_gaps(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        conflicts = await service.detect_conflicts(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # Calculate current metrics
        current_metrics = await service.calculate_metrics(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return ScheduleOptimizationResponse(
            id=optimization_id,
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date,
            status="pending",
            metrics=current_metrics,
            suggestions=[],
            parameters=request.parameters,
            warnings=[],
            created_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error previewing optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Auto-Pilot ====================

@router.post("/auto-pilot/generate", response_model=AutoPilotResponse, status_code=201)
async def generate_auto_pilot_schedule(
    request: AutoPilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Сгенерировать расписание в режиме автопилота.

    Автоматически заполняет расписание с учётом рекомендаций, шаблонов и разрешений конфликтов.
    """
    try:
        service = AutoPilotService(db)

        # Parse date range from dict
        start = date.fromisoformat(request.date_range["start"])
        end = date.fromisoformat(request.date_range["end"])

        result = await service.generate_schedule(
            channel_id=request.channel_id,
            start_date=start,
            end_date=end,
            use_templates=True,
            fill_gaps=request.fill_gaps,
            resolve_conflicts=request.resolve_conflicts,
            user_id=current_user.id
        )

        return AutoPilotResponse(
            task_id=result.get("schedule_id", str(uuid.uuid4())),
            channel_id=request.channel_id,
            status="completed",
            date_range=request.date_range,
            slots_created=result.get("slots_created", 0),
            gaps_filled=result.get("gaps_filled", 0),
            conflicts_resolved=result.get("conflicts_resolved", 0),
            created_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error generating auto-pilot schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-pilot/preview")
async def preview_auto_pilot_schedule(
    request: AutoPilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Предпросмотр расписания автопилота без применения.

    Показывает, как будет выглядеть сгенерированное расписание.
    """
    try:
        service = AutoPilotService(db)

        # Parse date range from dict
        start = date.fromisoformat(request.date_range["start"])
        end = date.fromisoformat(request.date_range["end"])

        preview = await service.preview_schedule(
            channel_id=request.channel_id,
            start_date=start,
            end_date=end,
            use_templates=True,
            fill_gaps=request.fill_gaps
        )

        return {
            "channel_id": request.channel_id,
            "date_range": request.date_range,
            "preview": preview,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error previewing auto-pilot schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Peak Hours ====================

@router.get("/peak-hours", response_model=PeakHoursResponse)
async def get_peak_hours(
    channel_id: str = Query(..., description="ID канала"),
    period: str = Query("30d", description="Период анализа (7d, 30d, 90d)"),
    min_sample_size: int = Query(7, ge=1, description="Мин. размер выборки"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить анализ пиковых часов.

    Возвращает данные о часах пик на основе исторических данных.
    """
    try:
        service = ScheduleRecommendationService(db)

        # Parse period (e.g., "30d" -> 30 days)
        days = int(period.replace("d", ""))

        peak_hours = await service.get_peak_hours(
            channel_id=channel_id,
            days=days
        )

        # Calculate period dates
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return PeakHoursResponse(
            channel_id=channel_id,
            period_start=start_date,
            period_end=end_date,
            sample_size=days,
            peak_hours_data=peak_hours.get("peak_hours_data", []),
            best_hours=peak_hours.get("best_hours", []),
            updated_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error getting peak hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Conflict Detection & Resolution ====================

@router.post("/detect-conflicts", response_model=ConflictDetectionResponse)
async def detect_conflicts(
    request: ConflictDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обнаружить конфликты в расписании.

    Идентифицирует пересекающиеся слоты.
    """
    try:
        service = ScheduleOptimizationService(db)

        conflicts = await service.detect_conflicts(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return ConflictDetectionResponse(
            channel_id=request.channel_id,
            period={"start": str(request.start_date), "end": str(request.end_date)},
            total_conflicts=len(conflicts),
            conflicts=conflicts
        )
    except Exception as e:
        logger.error(f"Error detecting conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-conflicts", response_model=ConflictResolutionResponse)
async def resolve_conflicts(
    request: ConflictDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Разрешить конфликты в расписании.

    Предлагает действия для разрешения обнаруженных конфликтов.
    """
    try:
        service = ScheduleOptimizationService(db)

        resolution = await service.resolve_conflicts(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # Calculate stats from resolution
        resolutions_applied = len(resolution.get("resolutions", []))
        slots_removed = sum(1 for r in resolution.get("resolutions", []) if r.get("action") == "remove")
        slots_modified = sum(1 for r in resolution.get("resolutions", []) if r.get("action") in ["modify_time", "lower_priority"])

        return ConflictResolutionResponse(
            channel_id=request.channel_id,
            date=request.start_date,
            resolutions_applied=resolutions_applied,
            slots_removed=slots_removed,
            slots_modified=slots_modified,
            remaining_conflicts=resolution.get("remaining_conflicts", 0)
        )
    except Exception as e:
        logger.error(f"Error resolving conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Gap Detection ====================

@router.post("/detect-gaps", response_model=GapDetectionResponse)
async def detect_gaps(
    request: GapDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обнаружить пробелы в расписании.

    Идентифицирует незаполненные временные интервалы.
    """
    try:
        service = ScheduleOptimizationService(db)

        gaps = await service.detect_gaps(
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # Calculate stats
        total_gap_hours = sum(g.get("duration_hours", 0) for g in gaps)
        peak_hours_gap = sum(g.get("duration_hours", 0) for g in gaps if g.get("is_peak_hour", False))
        fillable_gaps = len(gaps)

        return GapDetectionResponse(
            channel_id=request.channel_id,
            period={"start": str(request.start_date), "end": str(request.end_date)},
            total_gap_hours=total_gap_hours,
            peak_hours_gap=peak_hours_gap,
            gaps=gaps,
            fillable_gaps=fillable_gaps
        )
    except Exception as e:
        logger.error(f"Error detecting gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))
