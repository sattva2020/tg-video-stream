"""
Analytics Service
Feature: 021-admin-analytics-menu

Сервис для сбора и кэширования аналитики:
- Статистика слушателей (текущие, пик, среднее)
- История слушателей (для графиков)
- Топ треков
- Сводная статистика
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.analytics import TrackPlay, MonthlyAnalytics
from src.models.playlist import PlaylistItem
from src.schemas.analytics import (
    ListenerStatsResponse,
    ListenerHistoryPoint,
    ListenerHistoryResponse,
    TopTrackItem,
    TopTracksResponse,
    AnalyticsSummaryResponse,
    TrackPlayRequest,
    TrackPlayResponse,
    AnalyticsPeriod,
    HistoryInterval,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "analytics:"
CACHE_SUMMARY_KEY = f"{CACHE_PREFIX}summary:{{period}}"
CACHE_LISTENERS_KEY = f"{CACHE_PREFIX}listeners"
CACHE_HISTORY_KEY = f"{CACHE_PREFIX}history:{{period}}:{{interval}}"
CACHE_TOP_TRACKS_KEY = f"{CACHE_PREFIX}top_tracks:{{period}}:{{limit}}"
CACHE_TTL = 300  # 5 minutes


def _period_to_days(period: AnalyticsPeriod) -> Optional[int]:
    """Конвертация периода в количество дней."""
    mapping = {"7d": 7, "30d": 30, "90d": 90, "all": None}
    return mapping.get(period)


class AnalyticsService:
    """
    Сервис аналитики с Redis кэшированием.
    
    Методы:
    - get_listener_stats: Текущая статистика слушателей
    - get_listener_history: История для графиков
    - get_top_tracks: Топ треков
    - get_summary: Сводная статистика
    - log_track_play: Запись воспроизведения (для streamer)
    """

    def __init__(self, db: Session, redis_client: Optional["aioredis.Redis"] = None):
        """
        Инициализация сервиса.
        
        Args:
            db: SQLAlchemy сессия
            redis_client: Опциональный Redis клиент для кэширования
        """
        self.db = db
        self.redis = redis_client

    async def _get_from_cache(self, key: str) -> Optional[dict]:
        """Получение данных из кэша Redis."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    async def _set_to_cache(self, key: str, data: dict, ttl: int = CACHE_TTL) -> None:
        """Сохранение данных в кэш Redis."""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    def _get_period_filter(self, period: AnalyticsPeriod) -> Optional[datetime]:
        """Получение фильтра по времени для периода."""
        days = _period_to_days(period)
        if days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=days)

    async def get_listener_stats(self) -> ListenerStatsResponse:
        """
        Получение текущей статистики слушателей.
        
        Returns:
            ListenerStatsResponse с current, peak_today, peak_week, average_week
        """
        cache_key = CACHE_LISTENERS_KEY
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ListenerStatsResponse(**cached)

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # Последняя запись - текущие слушатели
        latest_play = self.db.execute(
            select(TrackPlay.listeners_count)
            .order_by(desc(TrackPlay.played_at))
            .limit(1)
        ).scalar()
        current = latest_play or 0

        # Пик за сегодня
        peak_today = self.db.execute(
            select(func.max(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= today_start)
        ).scalar() or 0

        # Пик за неделю
        peak_week = self.db.execute(
            select(func.max(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= week_ago)
        ).scalar() or 0

        # Среднее за неделю
        avg_week = self.db.execute(
            select(func.avg(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= week_ago)
        ).scalar() or 0.0

        result = ListenerStatsResponse(
            current=current,
            peak_today=peak_today,
            peak_week=peak_week,
            average_week=round(float(avg_week), 2)
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_listener_history(
        self, 
        period: AnalyticsPeriod = "7d",
        interval: HistoryInterval = "day"
    ) -> ListenerHistoryResponse:
        """
        Получение истории слушателей для графиков.
        
        Args:
            period: Период данных (7d, 30d, 90d, all)
            interval: Интервал агрегации (hour, day)
            
        Returns:
            ListenerHistoryResponse с точками для графика
        """
        cache_key = CACHE_HISTORY_KEY.format(period=period, interval=interval)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ListenerHistoryResponse(**cached)

        period_start = self._get_period_filter(period)
        
        # Для группировки по интервалу
        if interval == "hour":
            time_trunc = func.date_trunc('hour', TrackPlay.played_at)
        else:
            time_trunc = func.date_trunc('day', TrackPlay.played_at)

        query = select(
            time_trunc.label('timestamp'),
            func.avg(TrackPlay.listeners_count).label('avg_count')
        ).group_by(time_trunc).order_by(time_trunc)

        if period_start:
            query = query.where(TrackPlay.played_at >= period_start)

        rows = self.db.execute(query).fetchall()

        data = [
            ListenerHistoryPoint(
                timestamp=row.timestamp,
                count=round(row.avg_count)
            )
            for row in rows
        ]

        result = ListenerHistoryResponse(period=period, data=data)
        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_top_tracks(
        self,
        period: AnalyticsPeriod = "7d",
        limit: int = 5
    ) -> TopTracksResponse:
        """
        Получение топ треков за период.
        
        Args:
            period: Период данных
            limit: Количество треков (1-50)
            
        Returns:
            TopTracksResponse со списком треков
        """
        cache_key = CACHE_TOP_TRACKS_KEY.format(period=period, limit=limit)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return TopTracksResponse(**cached)

        period_start = self._get_period_filter(period)

        query = (
            select(
                TrackPlay.playlist_item_id,
                PlaylistItem.title,
                func.count(TrackPlay.id).label('play_count'),
                func.sum(TrackPlay.duration_seconds).label('total_duration')
            )
            .join(PlaylistItem, TrackPlay.playlist_item_id == PlaylistItem.id)
            .group_by(TrackPlay.playlist_item_id, PlaylistItem.title)
            .order_by(desc('play_count'))
            .limit(limit)
        )

        if period_start:
            query = query.where(TrackPlay.played_at >= period_start)

        rows = self.db.execute(query).fetchall()

        tracks = [
            TopTrackItem(
                track_id=idx + 1,  # Просто порядковый номер
                title=row.title or "Unknown",
                artist=None,  # PlaylistItem не хранит artist отдельно
                play_count=row.play_count,
                total_duration_seconds=row.total_duration or 0
            )
            for idx, row in enumerate(rows)
        ]

        result = TopTracksResponse(period=period, tracks=tracks)
        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_summary(self, period: AnalyticsPeriod = "7d") -> AnalyticsSummaryResponse:
        """
        Получение сводной статистики.
        
        Args:
            period: Период данных
            
        Returns:
            AnalyticsSummaryResponse со всеми метриками
        """
        cache_key = CACHE_SUMMARY_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return AnalyticsSummaryResponse(**cached)

        period_start = self._get_period_filter(period)
        now = datetime.now(timezone.utc)

        # Базовый фильтр
        base_filter = TrackPlay.played_at >= period_start if period_start else True

        # Общее количество воспроизведений
        total_plays = self.db.execute(
            select(func.count(TrackPlay.id)).where(base_filter)
        ).scalar() or 0

        # Общее время вещания в секундах
        total_seconds = self.db.execute(
            select(func.sum(TrackPlay.duration_seconds)).where(base_filter)
        ).scalar() or 0

        # Уникальные треки
        unique_tracks = self.db.execute(
            select(func.count(func.distinct(TrackPlay.playlist_item_id))).where(base_filter)
        ).scalar() or 0

        # Статистика слушателей
        listeners = await self.get_listener_stats()

        result = AnalyticsSummaryResponse(
            period=period,
            total_plays=total_plays,
            total_duration_hours=round(total_seconds / 3600, 2),
            unique_tracks=unique_tracks,
            listeners=listeners,
            cached_at=now
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    def log_track_play(self, request: TrackPlayRequest) -> TrackPlayResponse:
        """
        Записать воспроизведение трека (вызывается streamer'ом).
        
        Args:
            request: Данные о воспроизведении
            
        Returns:
            TrackPlayResponse с ID и временем записи
        """
        # Преобразуем track_id в UUID если это int
        playlist_item_id = None
        if request.track_id:
            # Ищем playlist_item по id (предполагая что это position или другой идентификатор)
            # В реальности streamer должен передавать UUID
            pass

        track_play = TrackPlay(
            playlist_item_id=playlist_item_id,
            duration_seconds=request.duration_seconds,
            listeners_count=request.listeners_count,
            played_at=datetime.now(timezone.utc)
        )

        self.db.add(track_play)
        self.db.commit()
        self.db.refresh(track_play)

        return TrackPlayResponse(
            id=track_play.id,
            played_at=track_play.played_at
        )


def get_analytics_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> AnalyticsService:
    """
    Фабрика для создания сервиса аналитики.
    
    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент
        
    Returns:
        AnalyticsService instance
    """
    return AnalyticsService(db=db, redis_client=redis_client)
