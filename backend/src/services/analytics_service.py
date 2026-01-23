"""
Analytics Service
Feature: 021-admin-analytics-menu, 012-comprehensive-analytics-dashboard

Сервис для сбора и кэширования аналитики:
- Статистика слушателей (текущие, пик, среднее)
- История слушателей (для графиков)
- Топ треков
- Сводная статистика
- Метрики вовлеченности
- Производительность потока
- Аналитика контента и точки отказа
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
from src.models.engagement import EngagementEvent
from src.models.stream_quality import StreamQualityHistory
from src.models.viewer_session import ViewerSession
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
    EngagementMetricsResponse,
    EngagementTrendPoint,
    ActiveUserItem,
    StreamPerformanceResponse,
    QualityDistributionItem,
    QualityTrendPoint,
    ContentInsightsResponse,
    ContentPerformanceItem,
    DropOffPoint,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "analytics:"
CACHE_SUMMARY_KEY = f"{CACHE_PREFIX}summary:{{period}}"
CACHE_LISTENERS_KEY = f"{CACHE_PREFIX}listeners"
CACHE_HISTORY_KEY = f"{CACHE_PREFIX}history:{{period}}:{{interval}}"
CACHE_TOP_TRACKS_KEY = f"{CACHE_PREFIX}top_tracks:{{period}}:{{limit}}"
CACHE_ENGAGEMENT_KEY = f"{CACHE_PREFIX}engagement:{{period}}"
CACHE_STREAM_PERFORMANCE_KEY = f"{CACHE_PREFIX}stream_performance:{{period}}"
CACHE_CONTENT_INSIGHTS_KEY = f"{CACHE_PREFIX}content_insights:{{period}}"
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
    - get_engagement: Метрики вовлеченности
    - get_stream_performance: Производительность потока
    - get_content_insights: Аналитика контента и точки отказа
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

    async def get_engagement(self, period: AnalyticsPeriod = "7d") -> EngagementMetricsResponse:
        """
        Получение метрик вовлеченности за период.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            EngagementMetricsResponse с метриками вовлеченности
        """
        cache_key = CACHE_ENGAGEMENT_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return EngagementMetricsResponse(**cached)

        period_start = self._get_period_filter(period)
        now = datetime.now(timezone.utc)

        # Базовый фильтр
        base_filter = EngagementEvent.event_timestamp >= period_start if period_start else True

        # Общее количество событий по типам
        total_messages = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "chat_message"))
        ).scalar() or 0

        total_reactions = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "reaction"))
        ).scalar() or 0

        total_comments = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "comment"))
        ).scalar() or 0

        # Уникальные пользователи
        unique_users = self.db.execute(
            select(func.count(func.distinct(EngagementEvent.user_id))).where(base_filter)
        ).scalar() or 0

        # Среднее количество событий в день
        days = _period_to_days(period) or 7
        total_events = total_messages + total_reactions + total_comments
        average_daily = round(total_events / days, 2) if days > 0 else 0.0

        # Топ активных пользователей
        top_users_query = (
            select(
                EngagementEvent.user_id,
                EngagementEvent.username,
                func.sum(func.case((EngagementEvent.event_type == "chat_message", 1), else_=0)).label('message_count'),
                func.sum(func.case((EngagementEvent.event_type == "reaction", 1), else_=0)).label('reaction_count'),
                func.max(EngagementEvent.event_timestamp).label('last_activity')
            )
            .where(base_filter)
            .group_by(EngagementEvent.user_id, EngagementEvent.username)
            .order_by(desc('message_count'))
            .limit(10)
        )
        top_users_rows = self.db.execute(top_users_query).fetchall()

        top_active_users = [
            ActiveUserItem(
                user_id=row.user_id,
                username=row.username,
                message_count=row.message_count or 0,
                reaction_count=row.reaction_count or 0,
                last_activity=row.last_activity
            )
            for row in top_users_rows
        ]

        # Данные для графика вовлеченности по времени (группировка по дням)
        time_trunc = func.date_trunc('day', EngagementEvent.event_timestamp)
        engagement_query = select(
            time_trunc.label('timestamp'),
            func.sum(func.case((EngagementEvent.event_type == "chat_message", 1), else_=0)).label('message_count'),
            func.sum(func.case((EngagementEvent.event_type == "reaction", 1), else_=0)).label('reaction_count'),
            func.count(func.distinct(EngagementEvent.user_id)).label('unique_users')
        ).where(base_filter).group_by(time_trunc).order_by(time_trunc)

        engagement_rows = self.db.execute(engagement_query).fetchall()

        engagement_over_time = [
            EngagementTrendPoint(
                timestamp=row.timestamp,
                message_count=row.message_count or 0,
                reaction_count=row.reaction_count or 0,
                unique_users=row.unique_users or 0
            )
            for row in engagement_rows
        ]

        result = EngagementMetricsResponse(
            period=period,
            total_messages=total_messages,
            total_reactions=total_reactions,
            total_comments=total_comments,
            unique_users=unique_users,
            average_daily=average_daily,
            top_active_users=top_active_users,
            engagement_over_time=engagement_over_time,
            cached_at=now
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_stream_performance(self, period: AnalyticsPeriod = "7d") -> StreamPerformanceResponse:
        """
        Получение показателей производительности потока.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            StreamPerformanceResponse с метриками производительности
        """
        cache_key = CACHE_STREAM_PERFORMANCE_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return StreamPerformanceResponse(**cached)

        period_start = self._get_period_filter(period)
        now = datetime.now(timezone.utc)

        # Базовый фильтр
        base_filter = StreamQualityHistory.analyzed_at >= period_start if period_start else True

        # Аптайм: считаем процент успешных анализов
        total_records = self.db.execute(
            select(func.count(StreamQualityHistory.id)).where(base_filter)
        ).scalar() or 0

        successful_records = self.db.execute(
            select(func.count(StreamQualityHistory.id))
            .where(and_(base_filter, StreamQualityHistory.success == True))
        ).scalar() or 0

        uptime_percentage = round((successful_records / total_records * 100), 2) if total_records > 0 else 100.0

        # Аптайм в часах (предполагаем записи каждые 5 минут)
        uptime_hours = round(total_records * 5 / 60, 2) if total_records > 0 else 0.0

        # Средний процент буферизации
        avg_buffering = self.db.execute(
            select(func.avg(StreamQualityHistory.buffering_percentage))
            .where(and_(base_filter, StreamQualityHistory.buffering_percentage.isnot(None)))
        ).scalar() or 0.0

        average_buffering_percentage = round(float(avg_buffering), 2)

        # Количество изменений качества (считаем по изменению overall_quality между соседними записями)
        # Это упрощенная версия - в реальности может потребоваться более сложный запрос
        quality_changes_count = 0  # Заглушка, требует оконных функций для точного расчета

        # Текущее качество (последняя запись)
        latest_quality = self.db.execute(
            select(StreamQualityHistory.overall_quality)
            .where(base_filter)
            .order_by(desc(StreamQualityHistory.analyzed_at))
            .limit(1)
        ).scalar() or "unknown"

        current_quality = latest_quality

        # Распределение по качеству
        quality_dist_query = select(
            StreamQualityHistory.overall_quality,
            func.count(StreamQualityHistory.id).label('count')
        ).where(base_filter).group_by(StreamQualityHistory.overall_quality)

        quality_dist_rows = self.db.execute(quality_dist_query).fetchall()

        quality_distribution = [
            QualityDistributionItem(
                quality=row.overall_quality,
                count=row.count,
                percentage=round(row.count / total_records * 100, 2) if total_records > 0 else 0.0
            )
            for row in quality_dist_rows
        ]

        # Данные для графика качества по времени (группировка по часам)
        time_trunc = func.date_trunc('hour', StreamQualityHistory.analyzed_at)
        quality_query = select(
            time_trunc.label('timestamp'),
            func.max(StreamQualityHistory.overall_quality).label('overall_quality'),
            func.avg(StreamQualityHistory.audio_bitrate_kbps).label('audio_bitrate_kbps'),
            func.avg(StreamQualityHistory.video_bitrate_kbps).label('video_bitrate_kbps'),
            func.avg(StreamQualityHistory.buffering_percentage).label('buffering_percentage')
        ).where(base_filter).group_by(time_trunc).order_by(time_trunc)

        quality_rows = self.db.execute(quality_query).fetchall()

        quality_over_time = [
            QualityTrendPoint(
                timestamp=row.timestamp,
                overall_quality=row.overall_quality or "unknown",
                audio_bitrate_kbps=int(row.audio_bitrate_kbps) if row.audio_bitrate_kbps else None,
                video_bitrate_kbps=int(row.video_bitrate_kbps) if row.video_bitrate_kbps else None,
                buffering_percentage=round(row.buffering_percentage, 2) if row.buffering_percentage else None
            )
            for row in quality_rows
        ]

        result = StreamPerformanceResponse(
            period=period,
            uptime_percentage=uptime_percentage,
            uptime_hours=uptime_hours,
            average_buffering_percentage=average_buffering_percentage,
            quality_changes_count=quality_changes_count,
            bandwidth_usage_mbps=None,  # Требует дополнительных данных
            current_quality=current_quality,
            quality_distribution=quality_distribution,
            quality_over_time=quality_over_time,
            cached_at=now
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_content_insights(self, period: AnalyticsPeriod = "7d") -> ContentInsightsResponse:
        """
        Получение аналитики контента и точек отказа.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            ContentInsightsResponse с аналитикой контента
        """
        cache_key = CACHE_CONTENT_INSIGHTS_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ContentInsightsResponse(**cached)

        period_start = self._get_period_filter(period)
        now = datetime.now(timezone.utc)

        # Базовый фильтр
        base_filter = ViewerSession.started_at >= period_start if period_start else True

        # Самый просматриваемый контент (топ по количеству сессий)
        content_query = (
            select(
                PlaylistItem.id.label('content_id'),
                PlaylistItem.title,
                func.count(ViewerSession.id).label('total_views'),
                func.avg(ViewerSession.completion_percentage).label('avg_completion'),
                func.sum(ViewerSession.drop_off_position_seconds).label('total_watch_time'),
                func.avg(ViewerSession.drop_off_position_seconds).label('avg_duration')
            )
            .join(ViewerSession, ViewerSession.playlist_item_id == PlaylistItem.id)
            .where(base_filter)
            .group_by(PlaylistItem.id, PlaylistItem.title)
            .order_by(desc('total_views'))
            .limit(10)
        )

        content_rows = self.db.execute(content_query).fetchall()

        most_watched = [
            ContentPerformanceItem(
                content_id=str(row.content_id),
                title=row.title or "Unknown",
                total_views=row.total_views or 0,
                average_completion_percentage=round(float(row.avg_completion or 0), 2),
                total_watch_time_minutes=round((row.total_watch_time or 0) / 60, 2),
                average_watch_duration_seconds=round(float(row.avg_duration or 0), 2)
            )
            for row in content_rows
        ]

        # Точки отказа (агрегируем по позициям в секундах)
        # Группируем по интервалам в 10 секунд для создания графика
        interval_seconds = 10

        drop_off_query = select(
            (func.floor(ViewerSession.drop_off_position_seconds / interval_seconds) * interval_seconds).label('position_seconds'),
            func.count(ViewerSession.id).label('viewers_count')
        ).where(
            and_(base_filter, ViewerSession.drop_off_position_seconds.isnot(None))
        ).group_by(
            (func.floor(ViewerSession.drop_off_position_seconds / interval_seconds) * interval_seconds)
        ).order_by('position_seconds')

        drop_off_rows = self.db.execute(drop_off_query).fetchall()

        # Вычисляем кумулятивный процент отказа
        total_sessions = sum(row.viewers_count for row in drop_off_rows) or 1
        cumulative_drop_off = 0.0

        drop_off_points = []
        for row in drop_off_rows:
            percentage = round(row.viewers_count / total_sessions * 100, 2)
            cumulative_drop_off += percentage
            drop_off_points.append(
                DropOffPoint(
                    position_seconds=int(row.position_seconds),
                    percentage=percentage,
                    viewers_count=row.viewers_count,
                    cumulative_drop_off=round(min(cumulative_drop_off, 100.0), 2)
                )
            )

        # Средний рейтинг завершения
        avg_completion = self.db.execute(
            select(func.avg(ViewerSession.completion_percentage))
            .where(and_(base_filter, ViewerSession.completion_percentage.isnot(None)))
        ).scalar() or 0.0

        average_completion_rate = round(float(avg_completion), 2)

        # Общее количество сессий
        total_sessions_count = self.db.execute(
            select(func.count(ViewerSession.id)).where(base_filter)
        ).scalar() or 0

        # Средняя длительность сессии
        avg_session_duration = self.db.execute(
            select(func.avg(ViewerSession.drop_off_position_seconds))
            .where(and_(base_filter, ViewerSession.drop_off_position_seconds.isnot(None)))
        ).scalar() or 0.0

        average_session_duration_seconds = round(float(avg_session_duration), 2)

        result = ContentInsightsResponse(
            period=period,
            most_watched=most_watched,
            drop_off_points=drop_off_points,
            average_completion_rate=average_completion_rate,
            total_sessions=total_sessions_count,
            average_session_duration_seconds=average_session_duration_seconds,
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
