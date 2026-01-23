"""
Recommendations API endpoints.
Feature: 014-ai-powered-content-recommendations

Эндпоинты для рекомендаций контента:
- GET /api/recommendations - Персонализированные рекомендации
- POST /api/recommendations/feedback - Обратная связь (like/dislike)
- GET /api/recommendations/for-playlist - Рекомендации для плейлиста
- GET /api/recommendations/stats - Статистика качества рекомендаций
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    FeedbackRequest,
    FeedbackResponse,
    RecommendationStatsResponse,
    RecommendationAlgorithm,
)
from src.services.recommendation_service import RecommendationService, get_recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


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


async def get_recommendation_service_dep(
    db: Session = Depends(get_db)
) -> RecommendationService:
    """Dependency для получения RecommendationService."""
    redis_client = await get_redis_client()
    return get_recommendation_service(db=db, redis_client=redis_client)


# ============ Recommendations Endpoints ============

@router.get(
    "/",
    response_model=RecommendationResponse,
    summary="Получить персонализированные рекомендации",
    description="Возвращает рекомендации контента на основе истории пользователя"
)
async def get_recommendations(
    request: Request,
    user_id: Optional[str] = Query(None, description="ID пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество рекомендаций"),
    algorithm: RecommendationAlgorithm = Query("hybrid", description="Алгоритм рекомендации"),
    exclude_watched: bool = Query(True, description="Исключать просмотренное"),
    service: RecommendationService = Depends(get_recommendation_service_dep)
):
    """
    Получить персонализированные рекомендации.

    Поддерживаемые алгоритмы:
    - collaborative_filtering: На основе предпочтений похожих пользователей
    - content_based: На основе похожести контента
    - hybrid: Комбинация нескольких подходов (по умолчанию)
    """
    try:
        req = RecommendationRequest(
            user_id=user_id,
            limit=limit,
            algorithm=algorithm,
            exclude_watched=exclude_watched
        )
        return await service.get_recommendations(req)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Записать обратную связь",
    description="Пользователь может отметить рекомендацию как понравившуюся или нет"
)
async def submit_feedback(
    request: Request,
    feedback_req: FeedbackRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """
    Записать обратную связь на рекомендацию.

    Обратная связь используется для улучшения будущих рекомендаций.
    """
    try:
        user_id = x_user_id or "anonymous"
        service = get_recommendation_service(db=db, redis_client=None)
        return await service.submit_feedback(user_id, feedback_req)
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get(
    "/for-playlist",
    response_model=RecommendationResponse,
    summary="Получить рекомендации для плейлиста",
    description="Рекомендации контента, который хорошо подойдет в указанный плейлист"
)
async def get_playlist_recommendations(
    request: Request,
    playlist_id: int = Query(..., ge=1, description="ID плейлиста"),
    limit: int = Query(10, ge=1, le=100, description="Количество рекомендаций"),
    service: RecommendationService = Depends(get_recommendation_service_dep)
):
    """
    Получить рекомендации для плейлиста.

    Анализирует содержимое плейлиста и предлагает похожий контент.
    """
    try:
        return await service.get_recommendations_for_playlist(playlist_id, limit)
    except Exception as e:
        logger.error(f"Error getting playlist recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get playlist recommendations")


@router.get(
    "/stats",
    response_model=RecommendationStatsResponse,
    summary="Получить статистику рекомендаций",
    description="Метрики качества рекомендаций (CTR, watch time, feedback rate)"
)
async def get_recommendation_stats(
    request: Request,
    period: str = Query("7d", description="Период: 7d, 30d, 90d"),
    service: RecommendationService = Depends(get_recommendation_service_dep)
):
    """
    Получить статистику качества рекомендаций.

    Включает метрики:
    - CTR (Click-Through Rate)
    - Среднее время просмотра
    - Доля положительной обратной связи
    """
    try:
        return await service.get_stats(period)
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendation stats")
