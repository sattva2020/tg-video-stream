"""
AI endpoints for Schedule API.
Feature: 015-smart-scheduling-auto-pilot-mode

Эндпоинты AI-функций расписания:
- GET /schedule/peak-hours - Аналитика пиковых часов
"""

import os
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.orm import Session

from src.database import get_db
from src.lib.rbac import require_role, UserRole
from src.schemas.schedule_ai import (
    PeakHoursResponse,
    ScheduleRecommendationRequest,
    ScheduleRecommendationResponse,
)
from src.services.schedule_recommendation_service import (
    ScheduleRecommendationService,
    get_schedule_recommendation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schedule-ai"])


async def get_redis_client():
    """Получение Redis клиента для кэширования."""
    if aioredis is None:
        return None
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    try:
        return await aioredis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        return None


async def get_schedule_recommendation_service_dep(
    db: Session = Depends(get_db)
) -> ScheduleRecommendationService:
    """Dependency для получения ScheduleRecommendationService."""
    redis_client = await get_redis_client()
    return get_schedule_recommendation_service(db=db, redis_client=redis_client)


@router.get(
    "/peak-hours",
    response_model=PeakHoursResponse,
    summary="Получить аналитику пиковых часов",
    description="Возвращает данные о слушателях по часам и дням недели"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_peak_hours_endpoint(
    channel_id: str = Query(..., description="ID канала"),
    period: Literal["7d", "30d", "90d"] = Query("30d", description="Период анализа"),
    service: ScheduleRecommendationService = Depends(get_schedule_recommendation_service_dep)
):
    """
    Получить аналитику пиковых часов прослушивания.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR

    Args:
        channel_id: ID канала для анализа
        period: Период анализа (7d, 30d, 90d)

    Returns:
        PeakHoursResponse с данными по часам и лучшим временем
    """
    try:
        return await service.get_peak_hours(channel_id=channel_id, period=period)
    except Exception as e:
        logger.error(f"Error getting peak hours: {e}")
        raise HTTPException(status_code=500, detail="Failed to get peak hours analytics")


@router.get(
    "/recommend",
    response_model=ScheduleRecommendationResponse,
    summary="Получить рекомендации по расписанию",
    description="Возвращает AI-рекомендации по контенту на основе исторических данных вовлеченности"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_recommendations_endpoint(
    channel_id: str = Query(..., description="ID канала"),
    date: date = Query(..., description="Целевая дата для рекомендаций (YYYY-MM-DD)"),
    min_confidence: float = Query(50.0, ge=0.0, le=100.0, description="Минимальная уверенность рекомендации"),
    max_recommendations: int = Query(10, ge=1, le=50, description="Максимальное количество рекомендаций"),
    service: ScheduleRecommendationService = Depends(get_schedule_recommendation_service_dep)
):
    """
    Получить рекомендации по контенту для указанной даты.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR

    Args:
        channel_id: ID канала
        date: Целевая дата для рекомендаций
        min_confidence: Минимальный порог уверенности (0-100)
        max_recommendations: Максимум рекомендаций в ответе

    Returns:
        ScheduleRecommendationResponse с списком рекомендаций
    """
    try:
        request = ScheduleRecommendationRequest(
            channel_id=channel_id,
            target_date=date,
            min_confidence=min_confidence,
            max_recommendations=max_recommendations
        )
        return await service.get_recommendations(request)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")
