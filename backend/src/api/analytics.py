"""
Analytics API endpoints.
Feature: 021-admin-analytics-menu

Эндпоинты для раздела "Аналитика" в админ-панели:
- GET /analytics/summary - Сводная статистика
- GET /analytics/listeners - Статистика слушателей
- GET /analytics/listeners/history - История слушателей
- GET /analytics/top-tracks - Топ треков
- POST /internal/track-play - Запись воспроизведения (для streamer)
"""

import os
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.orm import Session

from src.database import get_db
from src.lib.rbac import require_role, UserRole
from src.schemas.analytics import (
    AnalyticsSummaryResponse,
    ListenerStatsResponse,
    ListenerHistoryResponse,
    TopTracksResponse,
    TrackPlayRequest,
    TrackPlayResponse,
    AnalyticsPeriod,
    HistoryInterval,
)
from src.services.analytics_service import AnalyticsService, get_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
internal_router = APIRouter(prefix="/internal", tags=["Internal"])

# Internal token for service-to-service communication
INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")


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


async def get_analytics_service_dep(
    db: Session = Depends(get_db)
) -> AnalyticsService:
    """Dependency для получения AnalyticsService."""
    redis_client = await get_redis_client()
    return get_analytics_service(db=db, redis_client=redis_client)


# ============ Analytics Endpoints (require ADMIN/MODERATOR role) ============

@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Получить сводную статистику",
    description="Возвращает общую статистику за указанный период"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_analytics_summary(
    request: Request,
    period: AnalyticsPeriod = Query("7d", description="Период для агрегации данных"),
    service: AnalyticsService = Depends(get_analytics_service_dep)
):
    """
    Получить сводную статистику.
    
    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        return await service.get_summary(period=period)
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics summary")


@router.get(
    "/listeners",
    response_model=ListenerStatsResponse,
    summary="Получить статистику слушателей",
    description="Текущее количество, пиковые и средние значения"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_listener_stats(
    request: Request,
    service: AnalyticsService = Depends(get_analytics_service_dep)
):
    """
    Получить статистику слушателей.
    
    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        return await service.get_listener_stats()
    except Exception as e:
        logger.error(f"Error getting listener stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get listener stats")


@router.get(
    "/listeners/history",
    response_model=ListenerHistoryResponse,
    summary="Получить историю слушателей",
    description="Данные для построения графика истории слушателей"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_listener_history(
    request: Request,
    period: AnalyticsPeriod = Query("7d", description="Период для агрегации данных"),
    interval: HistoryInterval = Query("day", description="Интервал агрегации данных"),
    service: AnalyticsService = Depends(get_analytics_service_dep)
):
    """
    Получить историю слушателей.
    
    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        return await service.get_listener_history(period=period, interval=interval)
    except Exception as e:
        logger.error(f"Error getting listener history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get listener history")


@router.get(
    "/top-tracks",
    response_model=TopTracksResponse,
    summary="Получить топ треков",
    description="Самые популярные треки за период"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_top_tracks(
    request: Request,
    period: AnalyticsPeriod = Query("7d", description="Период для агрегации данных"),
    limit: int = Query(5, ge=1, le=50, description="Количество треков в топе"),
    service: AnalyticsService = Depends(get_analytics_service_dep)
):
    """
    Получить топ треков.
    
    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        return await service.get_top_tracks(period=period, limit=limit)
    except Exception as e:
        logger.error(f"Error getting top tracks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top tracks")


# ============ Internal Endpoints (for streamer service) ============

@internal_router.post(
    "/track-play",
    response_model=TrackPlayResponse,
    summary="Записать воспроизведение трека",
    description="Внутренний эндпоинт для streamer"
)
async def log_track_play(
    request: TrackPlayRequest,
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    db: Session = Depends(get_db)
):
    """
    Записать воспроизведение трека.
    
    Внутренний эндпоинт для streamer сервиса.
    Требует X-Internal-Token header.
    """
    # Validate internal token
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid internal token")
    
    try:
        service = get_analytics_service(db=db, redis_client=None)
        return service.log_track_play(request)
    except Exception as e:
        logger.error(f"Error logging track play: {e}")
        raise HTTPException(status_code=500, detail="Failed to log track play")
