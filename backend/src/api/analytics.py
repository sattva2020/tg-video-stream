"""
Analytics API endpoints.
Feature: 021-admin-analytics-menu

Эндпоинты для раздела "Аналитика" в админ-панели:
- GET /analytics/summary - Сводная статистика
- GET /analytics/listeners - Статистика слушателей
- GET /analytics/listeners/history - История слушателей
- GET /analytics/top-tracks - Топ треков
- GET /analytics/interactions - Метрики взаимодействий (опросы, Q&A, реакции, чат)
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
    InteractionPeriod,
    InteractionMetricsResponse,
    MostVotedPoll,
    PollStatsResponse,
    QAStatsResponse,
    EmojiUsage,
    ReactionStatsResponse,
    ChatStatsResponse,
    ActiveUser,
    EngagementSummaryResponse,
)
from src.services.analytics_service import AnalyticsService, get_analytics_service
from src.services.interaction_analytics_service import InteractionAnalyticsService

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


async def get_interaction_analytics_service_dep(
    db: Session = Depends(get_db)
) -> InteractionAnalyticsService:
    """Dependency для получения InteractionAnalyticsService."""
    redis_client = await get_redis_client()
    return InteractionAnalyticsService(db=db, redis_client=redis_client)


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


@router.get(
    "/interactions",
    response_model=InteractionMetricsResponse,
    summary="Получить метрики взаимодействий",
    description="Статистика опросов, Q&A, реакций и чата за указанный период"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_interaction_metrics(
    request: Request,
    period: InteractionPeriod = Query("7d", description="Период для агрегации данных"),
    service: InteractionAnalyticsService = Depends(get_interaction_analytics_service_dep)
):
    """
    Получить метрики взаимодействий.

    Возвращает агрегированную статистику по всем типам взаимодействий:
    - Опросы (количество, активные, голоса, участие)
    - Q&A (вопросы, ответы, upvotes)
    - Реакции (emoji, активность)
    - Чат (сообщения, авторы, фильтрация)
    - Сводная статистика вовлеченности

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        # Получаем статистику по всем типам взаимодействий
        poll_stats = await service.get_poll_stats(period=period)
        qa_stats = await service.get_qa_stats(period=period)
        reaction_stats = await service.get_reaction_stats(period=period)
        chat_stats = await service.get_chat_stats(period=period)
        engagement_summary = await service.get_engagement_summary(period=period)

        return InteractionMetricsResponse(
            period=period,
            polls=PollStatsResponse(
                total_polls=poll_stats.total_polls,
                active_polls=poll_stats.active_polls,
                total_votes=poll_stats.total_votes,
                unique_voters=poll_stats.unique_voters,
                avg_participation_rate=poll_stats.avg_participation_rate,
                most_voted_poll=MostVotedPoll(**poll_stats.most_voted_poll) if poll_stats.most_voted_poll else None
            ),
            qa=QAStatsResponse(
                total_questions=qa_stats.total_questions,
                pending_questions=qa_stats.pending_questions,
                answered_questions=qa_stats.answered_questions,
                total_upvotes=qa_stats.total_upvotes,
                unique_participants=qa_stats.unique_participants,
                avg_answer_time_hours=qa_stats.avg_answer_time_hours
            ),
            reactions=ReactionStatsResponse(
                total_reactions=reaction_stats.total_reactions,
                unique_users=reaction_stats.unique_users,
                top_emojis=[EmojiUsage(**emoji) for emoji in reaction_stats.top_emojis],
                reactions_per_hour=reaction_stats.reactions_per_hour
            ),
            chat=ChatStatsResponse(
                total_messages=chat_stats.total_messages,
                unique_authors=chat_stats.unique_authors,
                avg_message_length=chat_stats.avg_message_length,
                messages_per_hour=chat_stats.messages_per_hour,
                filtered_messages=chat_stats.filtered_messages
            ),
            engagement=EngagementSummaryResponse(
                total_interactions=engagement_summary.total_interactions,
                poll_participation_rate=engagement_summary.poll_participation_rate,
                qa_engagement_rate=engagement_summary.qa_engagement_rate,
                reaction_intensity=engagement_summary.reaction_intensity,
                chat_activity_level=engagement_summary.chat_activity_level,
                most_active_users=[ActiveUser(**user) for user in engagement_summary.most_active_users],
                peak_interaction_hour=engagement_summary.peak_interaction_hour
            )
        )
    except Exception as e:
        logger.error(f"Error getting interaction metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get interaction metrics")


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
