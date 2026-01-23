"""
Multi-Platform Analytics Service
Feature: 021-social-media-integration-cross-platform-broadcasting

Сервис для агрегации аналитики по всем платформам стриминга:
- Статистика по платформам (YouTube, Twitch, Twitter, Discord)
- Агрегированные метрики стриминга
- Статистика постов в соцсетях
- Показатели успешности постов
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from decimal import Decimal

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import Session

from src.models.streaming_platform import StreamingPlatform
from src.models.broadcast_destination import BroadcastDestination
from src.models.social_media_post import SocialMediaPost
from src.schemas.analytics import (
    PlatformMetrics,
    MultiPlatformAnalyticsResponse,
    AnalyticsPeriod,
)

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "multi_platform_analytics:"
CACHE_MULTI_PLATFORM_KEY = f"{CACHE_PREFIX}summary:{{period}}"
CACHE_TTL = 300  # 5 minutes


def _period_to_days(period: AnalyticsPeriod) -> Optional[int]:
    """Конвертация периода в количество дней."""
    mapping = {"7d": 7, "30d": 30, "90d": 90, "all": None}
    return mapping.get(period)


class MultiPlatformAnalyticsService:
    """
    Сервис мультиплатформенной аналитики с Redis кэшированием.

    Методы:
    - get_multi_platform_analytics: Агрегированная статистика по всем платформам
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

    async def get_multi_platform_analytics(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> MultiPlatformAnalyticsResponse:
        """
        Получение агрегированной аналитики по всем платформам.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            MultiPlatformAnalyticsResponse с агрегированными метриками
        """
        cache_key = CACHE_MULTI_PLATFORM_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return MultiPlatformAnalyticsResponse(**cached)

        period_start = self._get_period_filter(period)
        now = datetime.now(timezone.utc)

        # Получаем все платформы
        platforms_query = select(StreamingPlatform)
        platforms = self.db.execute(platforms_query).scalars().all()

        platform_metrics_list = []
        total_streams = 0
        total_stream_hours = 0.0
        total_posts = 0
        successful_posts = 0
        failed_posts = 0
        active_platforms = 0

        for platform in platforms:
            # Количество broadcast destinations для этой платформы
            dest_query = select(func.count(BroadcastDestination.id)).where(
                BroadcastDestination.platform_id == platform.id
            )
            stream_count = self.db.execute(dest_query).scalar() or 0

            # Количество постов для этой платформы за период
            post_filter = and_(
                SocialMediaPost.platform_id == platform.id,
                SocialMediaPost.created_at >= period_start
            ) if period_start else SocialMediaPost.platform_id == platform.id

            posts_query = select(SocialMediaPost).where(post_filter)
            posts = self.db.execute(posts_query).scalars().all()

            platform_post_count = len(posts)
            platform_successful = sum(1 for p in posts if p.status == "posted")
            platform_failed = sum(1 for p in posts if p.status == "failed")

            # Последняя активность (последний пост или последнее обновление платформы)
            last_activity = platform.updated_at
            if posts:
                latest_post = max(posts, key=lambda p: p.created_at)
                if last_activity is None or latest_post.created_at > last_activity:
                    last_activity = latest_post.created_at

            # Считаем активной, если есть активные назначения или недавние посты
            is_active = (
                stream_count > 0 or
                platform_post_count > 0 or
                platform.status == "active"
            )

            if is_active:
                active_platforms += 1

            platform_metric = PlatformMetrics(
                platform_type=platform.platform_type,
                platform_name=platform.platform_name,
                status=platform.status,
                stream_count=stream_count,
                total_stream_hours=0.0,  # Можно добавить позже, если храним время стриминга
                post_count=platform_post_count,
                successful_posts=platform_successful,
                failed_posts=platform_failed,
                last_activity=last_activity
            )

            platform_metrics_list.append(platform_metric)

            # Агрегируем totals
            total_streams += stream_count
            total_posts += platform_post_count
            successful_posts += platform_successful
            failed_posts += platform_failed

        # Вычисляем процент успешных постов
        successful_posts_rate = (
            (successful_posts / total_posts * 100) if total_posts > 0 else 0.0
        )

        result = MultiPlatformAnalyticsResponse(
            period=period,
            total_platforms=len(platforms),
            active_platforms=active_platforms,
            platforms=platform_metrics_list,
            total_streams=total_streams,
            total_stream_hours=total_stream_hours,
            total_posts=total_posts,
            successful_posts_rate=round(successful_posts_rate, 2),
            cached_at=now
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result


def get_multi_platform_analytics_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> MultiPlatformAnalyticsService:
    """
    Фабрика для создания сервиса мультиплатформенной аналитики.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент

    Returns:
        MultiPlatformAnalyticsService instance
    """
    return MultiPlatformAnalyticsService(db=db, redis_client=redis_client)
