"""
Schedule Recommendation Service
Feature: 015-smart-scheduling-auto-pilot-mode

Сервис для AI-рекомендаций по расписанию:
- Анализ вовлеченности для определения пиковых часов
- Рекомендации контента на основе исторических данных
- Прогнозирование оптимального времени размещения
- Кэширование через Redis
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.schedule_optimization import (
    ScheduleRecommendation,
    PeakHoursAnalytics,
    RecommendationType
)
from src.models.analytics import TrackPlay
from src.models.playlist import Playlist, PlaylistItem
from src.models.schedule import ScheduleSlot
from src.schemas.schedule_ai import (
    ScheduleRecommendationRequest,
    ScheduleRecommendationResponse,
    ScheduleRecommendationItem,
    RecommendationMetadata,
    PeakHoursRequest,
    PeakHoursResponse,
    PeakHoursDataPoint,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "schedule_recommendation:"
CACHE_PEAK_HOURS_KEY = f"{CACHE_PREFIX}peak_hours:{{channel_id}}:{{period}}"
CACHE_RECOMMENDATIONS_KEY = f"{CACHE_PREFIX}recommendations:{{channel_id}}:{{date}}"
CACHE_TTL = 600  # 10 minutes


class ScheduleRecommendationService:
    """
    Сервис рекомендаций по расписанию с Redis кэшированием.

    Методы:
    - get_peak_hours: Аналитика пиковых часов прослушивания
    - get_recommendations: Получить рекомендации для даты
    - analyze_engagement_data: Анализ данных вовлеченности
    - generate_recommendations: Генерация рекомендаций
    - save_recommendation: Сохранение рекомендации в БД
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

    def _get_period_days(self, period: str) -> int:
        """Конвертация периода в количество дней."""
        mapping = {"7d": 7, "30d": 30, "90d": 90}
        return mapping.get(period, 30)

    async def get_peak_hours(
        self,
        channel_id: str,
        period: str = "30d"
    ) -> PeakHoursResponse:
        """
        Получение аналитики пиковых часов.

        Args:
            channel_id: ID канала
            period: Период анализа (7d, 30d, 90d)

        Returns:
            PeakHoursResponse с данными по часам
        """
        cache_key = CACHE_PEAK_HOURS_KEY.format(channel_id=channel_id, period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return PeakHoursResponse(**cached)

        days = self._get_period_days(period)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Агрегируем данные по дням недели и часам
        query = select(
            func.date_part('dow', TrackPlay.played_at).label('day_of_week'),
            func.date_part('hour', TrackPlay.played_at).label('hour'),
            func.count(TrackPlay.id).label('total_plays'),
            func.avg(TrackPlay.listeners_count).label('avg_listeners'),
            func.max(TrackPlay.listeners_count).label('peak_listeners'),
            func.avg(TrackPlay.duration_seconds).label('avg_duration'),
            func.count(func.distinct(TrackPlay.playlist_item_id)).label('unique_tracks')
        ).where(
            and_(
                TrackPlay.played_at >= datetime.combine(start_date, datetime.min.time()),
                TrackPlay.played_at < datetime.combine(end_date, datetime.max.time())
            )
        ).group_by(
            func.date_part('dow', TrackPlay.played_at),
            func.date_part('hour', TrackPlay.played_at)
        )

        rows = self.db.execute(query).fetchall()

        peak_hours_data = []
        for row in rows:
            peak_hours_data.append(
                PeakHoursDataPoint(
                    day_of_week=int(row.day_of_week),
                    hour=int(row.hour),
                    total_plays=row.total_plays,
                    avg_listeners=float(row.avg_listeners) if row.avg_listeners else 0.0,
                    peak_listeners=row.peak_listeners or 0,
                    avg_duration_seconds=int(row.avg_duration) if row.avg_duration else 0,
                    unique_tracks_count=row.unique_tracks
                )
            )

        # Определяем лучшие часы (топ-10 по средним слушателям)
        sorted_hours = sorted(
            peak_hours_data,
            key=lambda x: x.avg_listeners,
            reverse=True
        )[:10]

        best_hours = [
            {
                "day_of_week": h.day_of_week,
                "hour": h.hour,
                "avg_listeners": h.avg_listeners,
                "total_plays": h.total_plays
            }
            for h in sorted_hours
        ]

        result = PeakHoursResponse(
            channel_id=channel_id,
            period_start=start_date,
            period_end=end_date,
            sample_size=days,
            peak_hours_data=peak_hours_data,
            best_hours=best_hours,
            updated_at=datetime.now(timezone.utc)
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def analyze_engagement_data(
        self,
        channel_id: str,
        target_date: date,
        hour: int
    ) -> Dict[str, Any]:
        """
        Анализ данных вовлеченности для конкретного времени.

        Args:
            channel_id: ID канала
            target_date: Целевая дата
            hour: Час суток (0-23)

        Returns:
            Словарь с метриками вовлеченности
        """
        day_of_week = target_date.weekday()

        # Ищем исторические данные за этот же день недели и час
        historical_query = select(
            func.avg(TrackPlay.listeners_count).label('avg_listeners'),
            func.count(TrackPlay.id).label('play_count'),
            func.max(TrackPlay.listeners_count).label('peak_listeners')
        ).where(
            and_(
                func.date_part('dow', TrackPlay.played_at) == day_of_week,
                func.date_part('hour', TrackPlay.played_at) == hour,
                TrackPlay.played_at >= datetime.now(timezone.utc) - timedelta(days=90)
            )
        )

        row = self.db.execute(historical_query).first()

        return {
            "avg_listeners": float(row.avg_listeners) if row and row.avg_listeners else 0.0,
            "play_count": row.play_count if row else 0,
            "peak_listeners": row.peak_listeners if row else 0,
            "day_of_week": day_of_week,
            "hour": hour
        }

    async def _get_playlist_performance(
        self,
        playlist_id: UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение метрик производительности плейлиста.

        Args:
            playlist_id: ID плейлиста
            period_days: Период анализа в днях

        Returns:
            Словарь с метриками плейлиста
        """
        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)

        query = select(
            func.avg(TrackPlay.listeners_count).label('avg_listeners'),
            func.count(TrackPlay.id).label('play_count'),
            func.sum(TrackPlay.duration_seconds).label('total_duration')
        ).join(
            PlaylistItem,
            TrackPlay.playlist_item_id == PlaylistItem.id
        ).where(
            and_(
                PlaylistItem.playlist_id == playlist_id,
                TrackPlay.played_at >= period_start
            )
        )

        row = self.db.execute(query).first()

        return {
            "avg_listeners": float(row.avg_listeners) if row and row.avg_listeners else 0.0,
            "play_count": row.play_count if row else 0,
            "total_duration": int(row.total_duration) if row and row.total_duration else 0
        }

    async def generate_recommendations(
        self,
        request: ScheduleRecommendationRequest
    ) -> ScheduleRecommendationResponse:
        """
        Генерация рекомендаций для целевой даты.

        Args:
            request: Запрос на рекомендации

        Returns:
            ScheduleRecommendationResponse с рекомендациями
        """
        recommendations = []
        target_date = request.target_date

        # Получаем аналитику пиковых часов
        peak_hours_data = await self.get_peak_hours(
            request.channel_id,
            period="30d"
        )

        # Получаем существующие слоты на дату
        existing_slots = self.db.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == UUID(request.channel_id),
                    ScheduleSlot.start_date == target_date,
                    ScheduleSlot.is_active == True
                )
            )
        ).scalars().all()

        # Определяем занятые часы
        occupied_hours = set()
        for slot in existing_slots:
            start_hour = slot.start_time.hour
            end_hour = slot.end_time.hour
            for h in range(start_hour, end_hour):
                occupied_hours.add(h)

        # Лучшие часы для контента
        best_hours_map = {}
        for bh in peak_hours_data.best_hours:
            key = (bh["day_of_week"], bh["hour"])
            best_hours_map[key] = bh

        # Генерируем рекомендации для незанятых часов
        for hour_data in peak_hours_data.peak_hours_data:
            if hour_data.hour in occupied_hours:
                continue

            # Проверяем, является ли час пиковым
            key = (hour_data.day_of_week, hour_data.hour)
            is_peak_hour = key in best_hours_map

            # Пропускаем часы с низкой активностью
            if hour_data.avg_listeners < 1.0:
                continue

            # Анализируем вовлеченность
            engagement_data = await self.analyze_engagement_data(
                request.channel_id,
                target_date,
                hour_data.hour
            )

            # Определяем тип рекомендации
            if is_peak_hour:
                rec_type = RecommendationType.PEAK_HOURS
                confidence = min(95.0, 50.0 + hour_data.avg_listeners * 2)
                title = f"Пиковый час: {hour_data.hour}:00"
                description = f"Высокая активность слушателей (ср. {hour_data.avg_listeners:.1f})"
            elif hour_data.avg_listeners > 5.0:
                rec_type = RecommendationType.PERFORMANCE
                confidence = min(85.0, 40.0 + hour_data.avg_listeners * 3)
                title = f"Хороший час: {hour_data.hour}:00"
                description = f"Стабильная активность (ср. {hour_data.avg_listeners:.1f})"
            else:
                rec_type = RecommendationType.FILL_GAP
                confidence = min(70.0, 30.0 + hour_data.avg_listeners * 5)
                title = f"Заполнить пробел: {hour_data.hour}:00"
                description = f"Низкий час, можно заполнить контентом"

            # Получаем топ плейлисты
            top_playlists = self.db.execute(
                select(Playlist)
                .join(PlaylistItem, Playlist.id == PlaylistItem.playlist_id)
                .join(TrackPlay, TrackPlay.playlist_item_id == PlaylistItem.id)
                .where(
                    and_(
                        Playlist.channel_id == UUID(request.channel_id),
                        TrackPlay.played_at >= datetime.now(timezone.utc) - timedelta(days=30)
                    )
                )
                .group_by(Playlist.id)
                .order_by(desc(func.count(TrackPlay.id)))
                .limit(3)
            ).scalars().all()

            playlist_id = top_playlists[0].id if top_playlists else None
            playlist_name = top_playlists[0].name if top_playlists else None

            # Создаем рекомендацию
            recommendation = ScheduleRecommendationItem(
                id=str(uuid.uuid4()),
                rec_type=rec_type,
                playlist_id=str(playlist_id) if playlist_id else None,
                playlist_name=playlist_name,
                recommended_date=target_date,
                start_time=f"{hour_data.hour:02d}:00",
                end_time=f"{(hour_data.hour + 1) % 24:02d}:00",
                confidence_score=round(confidence, 2),
                expected_engagement=round(
                    min(10.0, engagement_data["avg_listeners"] / 10.0),
                    2
                ) if engagement_data["avg_listeners"] > 0 else None,
                expected_listeners=int(engagement_data["avg_listeners"])
                if engagement_data["avg_listeners"] > 0 else None,
                priority=10 if is_peak_hour else 5,
                title=title,
                description=description,
                metadata=RecommendationMetadata(
                    avg_listeners_at_time=int(engagement_data["avg_listeners"])
                    if engagement_data["avg_listeners"] > 0 else None,
                    trend="stable"
                ),
                created_at=datetime.now(timezone.utc)
            )

            recommendations.append(recommendation)

            # Ограничиваем количество
            if len(recommendations) >= request.max_recommendations:
                break

        # Фильтруем по уверенности
        filtered_recommendations = [
            r for r in recommendations
            if r.confidence_score >= request.min_confidence
        ]

        # Фильтруем по типам если указано
        if request.recommendation_types:
            filtered_recommendations = [
                r for r in filtered_recommendations
                if r.rec_type in request.recommendation_types
            ]

        # Сортируем по приоритету и уверенности
        filtered_recommendations.sort(
            key=lambda x: (-x.priority, -x.confidence_score)
        )

        high_confidence_count = sum(
            1 for r in filtered_recommendations if r.confidence_score >= 75.0
        )

        return ScheduleRecommendationResponse(
            recommendations=filtered_recommendations,
            total_count=len(filtered_recommendations),
            high_confidence_count=high_confidence_count,
            target_date=target_date,
            generated_at=datetime.now(timezone.utc)
        )

    async def save_recommendation(
        self,
        recommendation: ScheduleRecommendationItem,
        channel_id: str,
        optimization_id: Optional[str] = None
    ) -> ScheduleRecommendation:
        """
        Сохранение рекомендации в базу данных.

        Args:
            recommendation: Данные рекомендации
            channel_id: ID канала
            optimization_id: Опциональный ID оптимизации

        Returns:
            Сохраненная модель ScheduleRecommendation
        """
        db_recommendation = ScheduleRecommendation(
            optimization_id=UUID(optimization_id) if optimization_id else None,
            channel_id=UUID(channel_id),
            rec_type=recommendation.rec_type,
            playlist_id=UUID(recommendation.playlist_id) if recommendation.playlist_id else None,
            recommended_date=recommendation.recommended_date,
            start_time=recommendation.start_time,
            end_time=recommendation.end_time,
            confidence_score=Decimal(str(recommendation.confidence_score)),
            expected_engagement=Decimal(str(recommendation.expected_engagement))
            if recommendation.expected_engagement else None,
            expected_listeners=recommendation.expected_listeners,
            priority=recommendation.priority,
            title=recommendation.title,
            description=recommendation.description,
            metadata=recommendation.metadata.model_dump() if recommendation.metadata else None
        )

        self.db.add(db_recommendation)
        self.db.commit()
        self.db.refresh(db_recommendation)

        return db_recommendation

    async def get_recommendations(
        self,
        request: ScheduleRecommendationRequest
    ) -> ScheduleRecommendationResponse:
        """
        Получение рекомендаций (из кэша или генерация новых).

        Args:
            request: Запрос на рекомендации

        Returns:
            ScheduleRecommendationResponse с рекомендациями
        """
        cache_key = CACHE_RECOMMENDATIONS_KEY.format(
            channel_id=request.channel_id,
            date=request.target_date.isoformat()
        )
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ScheduleRecommendationResponse(**cached)

        # Генерируем новые рекомендации
        response = await self.generate_recommendations(request)

        # Кэшируем результат
        await self._set_to_cache(cache_key, response.model_dump())

        return response


def get_schedule_recommendation_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> ScheduleRecommendationService:
    """
    Фабрика для создания сервиса рекомендаций.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент

    Returns:
        ScheduleRecommendationService instance
    """
    return ScheduleRecommendationService(db=db, redis_client=redis_client)
