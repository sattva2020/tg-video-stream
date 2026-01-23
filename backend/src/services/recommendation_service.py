"""
Recommendation Service
Feature: 014-ai-powered-content-recommendations

Сервис для управления рекомендациями контента:
- Персонализированные рекомендации (collaborative filtering, content-based, hybrid)
- Обратная связь пользователей (like/dislike)
- Запись взаимодействий с контентом
- Статистика качества рекомендаций
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import Session

from src.models.recommendation import (
    Recommendation,
    RecommendationFeedback,
    UserItemInteraction,
)
from src.models.playlist import PlaylistItem
from src.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationItem,
    FeedbackRequest,
    FeedbackResponse,
    InteractionRequest,
    InteractionResponse,
    RecommendationQualityMetrics,
    RecommendationStatsResponse,
    RecommendationAlgorithm,
)
from src.services.recommendation_engine import (
    CollaborativeFilteringEngine,
    ContentBasedFilteringEngine,
    HybridRecommender,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "recommendations:"
CACHE_USER_RECS_KEY = f"{CACHE_PREFIX}user:{{user_id}}:{{algorithm}}:{{limit}}"
CACHE_PLAYLIST_RECS_KEY = f"{CACHE_PREFIX}playlist:{{playlist_id}}:{{limit}}"
CACHE_STATS_KEY = f"{CACHE_PREFIX}stats:{{period}}"
CACHE_TTL = 600  # 10 minutes

# Минимальное количество элементов для fallback
FALLBACK_LIMIT = 10


class RecommendationService:
    """
    Сервис рекомендаций с Redis кэшированием и ML-движками.

    Методы:
    - get_recommendations: Персонализированные рекомендации для пользователя
    - get_recommendations_for_playlist: Рекомендации для плейлиста
    - submit_feedback: Запись обратной связи (like/dislike)
    - record_interaction: Запись взаимодействия с контентом
    - get_stats: Статистика качества рекомендаций
    """

    def __init__(
        self,
        db: Session,
        redis_client: Optional["aioredis.Redis"] = None,
        database_url: Optional[str] = None,
    ):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
            redis_client: Опциональный Redis клиент для кэширования
            database_url: URL базы данных для ML-движков
        """
        self.db = db
        self.redis = redis_client
        self.database_url = database_url or str(settings.DATABASE_URL)

        # Инициализируем ML-движки
        self.collaborative_engine = CollaborativeFilteringEngine()
        self.content_engine = ContentBasedFilteringEngine()
        self.hybrid_recommender = HybridRecommender(
            self.collaborative_engine, self.content_engine
        )

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

    async def _get_liked_items(self, user_id: str) -> List[str]:
        """
        Получить список элементов, понравившихся пользователю.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID элементов плейлиста
        """
        try:
            # Получаем элементы с positive feedback
            feedback_query = select(RecommendationFeedback.playlist_item_id).where(
                and_(
                    RecommendationFeedback.user_id == user_id,
                    RecommendationFeedback.feedback_type == "like",
                )
            )

            # Также учитываем watch взаимодействия с высоким completion_rate
            interaction_query = select(UserItemInteraction.playlist_item_id).where(
                and_(
                    UserItemInteraction.user_id == user_id,
                    UserItemInteraction.interaction_type == "watch",
                    UserItemInteraction.completion_rate >= 0.7,  # Просмотрено более 70%
                )
            )

            feedback_items = [str(row[0]) for row in self.db.execute(feedback_query).fetchall()]
            interaction_items = [
                str(row[0]) for row in self.db.execute(interaction_query).fetchall()
            ]

            # Объединяем и убираем дубликаты
            liked_items = list(set(feedback_items + interaction_items))
            return liked_items

        except Exception as e:
            logger.error(f"Ошибка получения понравившихся элементов: {e}")
            return []

    async def _get_watched_items(self, user_id: str, days: int = 30) -> List[str]:
        """
        Получить список элементов, просмотренных пользователем.

        Args:
            user_id: ID пользователя
            days: Количество дней для поиска

        Returns:
            Список ID элементов плейлиста
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(UserItemInteraction.playlist_item_id).where(
                and_(
                    UserItemInteraction.user_id == user_id,
                    UserItemInteraction.interacted_at >= cutoff_date,
                )
            ).distinct()

            watched_items = [str(row[0]) for row in self.db.execute(query).fetchall()]
            return watched_items

        except Exception as e:
            logger.error(f"Ошибка получения просмотренных элементов: {e}")
            return []

    async def _enrich_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[RecommendationItem]:
        """
        Обогатить рекомендации метаданными из PlaylistItem.

        Args:
            recommendations: Список рекомендаций из ML-движков

        Returns:
            Список RecommendationItem с метаданными
        """
        try:
            if not recommendations:
                return []

            # Получаем ID элементов
            item_ids = [rec["playlist_item_id"] for rec in recommendations]

            # Загружаем метаданные из базы
            items_query = select(PlaylistItem).where(PlaylistItem.id.in_(item_ids))
            items = {str(item.id): item for item in self.db.execute(items_query).scalars().all()}

            # Обогащаем рекомендации
            enriched = []
            for rec in recommendations:
                item = items.get(rec["playlist_item_id"])
                enriched.append(
                    RecommendationItem(
                        playlist_item_id=rec["playlist_item_id"],
                        title=item.title if item else "Unknown",
                        artist=None,  # PlaylistItem не хранит artist отдельно
                        score=round(rec["score"], 4),
                        algorithm=rec.get("algorithm", "collaborative_filtering"),
                        reason=rec.get("reason"),
                    )
                )

            return enriched

        except Exception as e:
            logger.error(f"Ошибка обогащения рекомендаций: {e}")
            # Возвращаем базовые рекомендации без метаданных
            return [
                RecommendationItem(
                    playlist_item_id=rec["playlist_item_id"],
                    title="Unknown",
                    score=round(rec["score"], 4),
                    algorithm=rec.get("algorithm", "collaborative_filtering"),
                    reason=rec.get("reason"),
                )
                for rec in recommendations
            ]

    async def get_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Получить персонализированные рекомендации для пользователя.

        Args:
            request: RecommendationRequest с параметрами

        Returns:
            RecommendationResponse с рекомендациями
        """
        user_id = request.user_id or "anonymous"
        algorithm = request.algorithm
        limit = request.limit

        # Проверяем кэш
        cache_key = CACHE_USER_RECS_KEY.format(user_id=user_id, algorithm=algorithm, limit=limit)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return RecommendationResponse(**cached)

        try:
            # Получаем просмотренные элементы для исключения
            exclude_items = []
            if request.exclude_watched:
                exclude_items = await self._get_watched_items(user_id)

            # Получаем понравившиеся элементы для content-based
            liked_items = await self._get_liked_items(user_id)

            # Генерируем рекомендации в зависимости от алгоритма
            raw_recommendations = []
            if algorithm == "collaborative_filtering":
                raw_recommendations = self.collaborative_engine.predict_for_user(
                    user_id=user_id, exclude_items=exclude_items, n=limit
                )
            elif algorithm == "content_based":
                # Обучаем content-based модель если нужно
                await self.content_engine.train(self.database_url)
                raw_recommendations = self.content_engine.predict_for_user(
                    user_id=user_id, liked_items=liked_items, exclude_items=exclude_items, n=limit
                )
            else:  # hybrid
                # Обучаем движки если нужно
                await self.content_engine.train(self.database_url)
                raw_recommendations = await self.hybrid_recommender.predict_for_user(
                    user_id=user_id,
                    liked_items=liked_items,
                    exclude_items=exclude_items,
                    n=limit,
                    strategy="weighted",
                )

            # Обогащаем метаданными
            recommendations = await self._enrich_recommendations(raw_recommendations)

            # Сохраняем рекомендации в базу
            await self._save_recommendations(user_id, recommendations, algorithm)

            result = RecommendationResponse(
                recommendations=recommendations,
                total_count=len(recommendations),
                algorithm=algorithm,
                generated_at=datetime.now(timezone.utc),
            )

            await self._set_to_cache(cache_key, result.model_dump())
            return result

        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций: {e}")
            # Fallback: возвращаем популярные элементы
            return await self._get_fallback_recommendations(limit, algorithm)

    async def _save_recommendations(
        self, user_id: str, recommendations: List[RecommendationItem], algorithm: str
    ) -> None:
        """
        Сохранить рекомендации в базу данных.

        Args:
            user_id: ID пользователя
            recommendations: Список рекомендаций
            algorithm: Алгоритм рекомендации
        """
        try:
            now = datetime.now(timezone.utc)
            for rec in recommendations[:20]:  # Сохраняем только топ-20
                recommendation = Recommendation(
                    user_id=user_id,
                    playlist_item_id=rec.playlist_item_id,
                    algorithm=algorithm,
                    score=rec.score,
                    created_at=now,
                )
                self.db.add(recommendation)

            self.db.commit()

        except Exception as e:
            logger.error(f"Ошибка сохранения рекомендаций: {e}")
            self.db.rollback()

    async def _get_fallback_recommendations(
        self, limit: int, algorithm: str
    ) -> RecommendationResponse:
        """
        Получить fallback-рекомендации (популярные элементы).

        Args:
            limit: Количество рекомендаций
            algorithm: Алгоритм для метки

        Returns:
            RecommendationResponse с популярными элементами
        """
        try:
            # Получаем популярные элементы на основе количества взаимодействий
            query = (
                select(
                    UserItemInteraction.playlist_item_id,
                    func.count(UserItemInteraction.id).label("interaction_count"),
                )
                .group_by(UserItemInteraction.playlist_item_id)
                .order_by(desc("interaction_count"))
                .limit(limit)
            )

            rows = self.db.execute(query).fetchall()

            # Загружаем метаданные
            item_ids = [str(row[0]) for row in rows]
            items_query = select(PlaylistItem).where(PlaylistItem.id.in_(item_ids))
            items = {str(item.id): item for item in self.db.execute(items_query).scalars().all()}

            # Создаем рекомендации
            recommendations = [
                RecommendationItem(
                    playlist_item_id=str(row[0]),
                    title=items.get(str(row[0])).title if items.get(str(row[0])) else "Popular",
                    score=0.5,  # Средний скор для fallback
                    algorithm=algorithm,
                    reason="Популярный контент",
                )
                for row in rows
            ]

            return RecommendationResponse(
                recommendations=recommendations,
                total_count=len(recommendations),
                algorithm=algorithm,
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Ошибка получения fallback-рекомендаций: {e}")
            return RecommendationResponse(
                recommendations=[],
                total_count=0,
                algorithm=algorithm,
                generated_at=datetime.now(timezone.utc),
            )

    async def get_recommendations_for_playlist(
        self, playlist_id: int, limit: int = 10
    ) -> RecommendationResponse:
        """
        Получить рекомендации для конкретного плейлиста.

        Args:
            playlist_id: ID плейлиста
            limit: Количество рекомендаций

        Returns:
            RecommendationResponse с рекомендациями для плейлиста
        """
        cache_key = CACHE_PLAYLIST_RECS_KEY.format(playlist_id=playlist_id, limit=limit)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return RecommendationResponse(**cached)

        try:
            # Получаем элементы из плейлиста
            query = (
                select(PlaylistItem)
                .where(PlaylistItem.playlist_id == playlist_id)
                .order_by(PlaylistItem.position)
                .limit(50)
            )
            items = self.db.execute(query).scalars().all()

            if not items:
                return RecommendationResponse(
                    recommendations=[],
                    total_count=0,
                    algorithm="content_based",
                    generated_at=datetime.now(timezone.utc),
                )

            # Находим похожие элементы через content-based engine
            await self.content_engine.train(self.database_url)

            all_recommendations = []
            for item in items[:5]:  # Берем первые 5 элементов
                similar_items = self.content_engine.find_similar_items(str(item.id), n=limit)
                for similar_item_id, score in similar_items:
                    if similar_item_id not in [str(i.id) for i in items]:  # Исключаем уже в плейлисте
                        all_recommendations.append(
                            {"playlist_item_id": similar_item_id, "score": score}
                        )

            # Сортируем по score и убираем дубликаты
            seen = set()
            unique_recommendations = []
            for rec in sorted(all_recommendations, key=lambda x: x["score"], reverse=True):
                if rec["playlist_item_id"] not in seen:
                    seen.add(rec["playlist_item_id"])
                    unique_recommendations.append(rec)
                if len(unique_recommendations) >= limit:
                    break

            # Обогащаем метаданными
            recommendations = await self._enrich_recommendations(unique_recommendations)

            result = RecommendationResponse(
                recommendations=recommendations,
                total_count=len(recommendations),
                algorithm="content_based",
                generated_at=datetime.now(timezone.utc),
            )

            await self._set_to_cache(cache_key, result.model_dump())
            return result

        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций для плейлиста: {e}")
            return RecommendationResponse(
                recommendations=[],
                total_count=0,
                algorithm="content_based",
                generated_at=datetime.now(timezone.utc),
            )

    async def submit_feedback(self, user_id: str, request: FeedbackRequest) -> FeedbackResponse:
        """
        Записать обратную связь на рекомендацию.

        Args:
            user_id: ID пользователя
            request: FeedbackRequest с типом обратной связи

        Returns:
            FeedbackResponse с записью
        """
        try:
            feedback = RecommendationFeedback(
                user_id=user_id,
                playlist_item_id=request.playlist_item_id,
                feedback_type=request.feedback_type,
                created_at=datetime.now(timezone.utc),
            )

            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)

            # Инвалидируем кэш рекомендаций для этого пользователя
            cache_pattern = f"{CACHE_PREFIX}user:{user_id}:*"
            if self.redis:
                try:
                    keys = await self.redis.keys(cache_pattern)
                    if keys:
                        await self.redis.delete(*keys)
                except Exception as e:
                    logger.warning(f"Ошибка инвалидации кэша: {e}")

            return FeedbackResponse(
                id=feedback.id,
                playlist_item_id=str(feedback.playlist_item_id),
                feedback_type=feedback.feedback_type,
                created_at=feedback.created_at,
            )

        except Exception as e:
            logger.error(f"Ошибка записи обратной связи: {e}")
            self.db.rollback()
            raise

    async def record_interaction(self, user_id: str, request: InteractionRequest) -> InteractionResponse:
        """
        Записать взаимодействие пользователя с контентом.

        Args:
            user_id: ID пользователя
            request: InteractionRequest с данными о взаимодействии

        Returns:
            InteractionResponse с записью
        """
        try:
            interaction = UserItemInteraction(
                user_id=user_id,
                playlist_item_id=request.playlist_item_id,
                interaction_type=request.interaction_type,
                duration_seconds=request.duration_seconds,
                completion_rate=request.completion_rate,
                interacted_at=datetime.now(timezone.utc),
            )

            self.db.add(interaction)
            self.db.commit()
            self.db.refresh(interaction)

            return InteractionResponse(
                id=interaction.id,
                playlist_item_id=str(interaction.playlist_item_id),
                interaction_type=interaction.interaction_type,
                interacted_at=interaction.interacted_at,
            )

        except Exception as e:
            logger.error(f"Ошибка записи взаимодействия: {e}")
            self.db.rollback()
            raise

    async def get_stats(self, period: str = "7d") -> RecommendationStatsResponse:
        """
        Получить статистику качества рекомендаций.

        Args:
            period: Период данных (7d, 30d, 90d)

        Returns:
            RecommendationStatsResponse с метриками качества
        """
        cache_key = CACHE_STATS_KEY.format(period=period)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return RecommendationStatsResponse(**cached)

        try:
            # Вычисляем фильтр по времени
            days_map = {"7d": 7, "30d": 30, "90d": 90}
            days = days_map.get(period, 7)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Общее количество показанных рекомендаций
            total_recommendations = self.db.execute(
                select(func.count(Recommendation.id)).where(
                    Recommendation.created_at >= cutoff_date
                )
            ).scalar() or 0

            # Количество взаимодействий с рекомендованными элементами
            total_interactions = self.db.execute(
                select(func.count(UserItemInteraction.id))
                .join(
                    Recommendation,
                    UserItemInteraction.playlist_item_id == Recommendation.playlist_item_id,
                )
                .where(UserItemInteraction.interacted_at >= cutoff_date)
            ).scalar() or 0

            # Positive feedback rate
            positive_feedback = self.db.execute(
                select(func.count(RecommendationFeedback.id)).where(
                    and_(
                        RecommendationFeedback.created_at >= cutoff_date,
                        RecommendationFeedback.feedback_type == "like",
                    )
                )
            ).scalar() or 0

            total_feedback = self.db.execute(
                select(func.count(RecommendationFeedback.id)).where(
                    RecommendationFeedback.created_at >= cutoff_date
                )
            ).scalar() or 0

            # Average watch time
            avg_watch_time = self.db.execute(
                select(func.avg(UserItemInteraction.duration_seconds)).where(
                    and_(
                        UserItemInteraction.interaction_type == "watch",
                        UserItemInteraction.interacted_at >= cutoff_date,
                    )
                )
            ).scalar() or 0.0

            # CTR (Interactions / Recommendations)
            ctr = (
                (total_interactions / total_recommendations)
                if total_recommendations > 0
                else 0.0
            )

            # Positive feedback rate
            positive_rate = (
                (positive_feedback / total_feedback) if total_feedback > 0 else 0.0
            )

            quality_metrics = RecommendationQualityMetrics(
                click_through_rate=round(float(ctr), 4),
                average_watch_time_seconds=round(float(avg_watch_time), 2),
                feedback_positive_rate=round(float(positive_rate), 4),
                total_recommendations_shown=total_recommendations,
                total_interactions=total_interactions,
            )

            # Производительность по алгоритмам
            algorithm_performance = []
            for alg in ["collaborative_filtering", "content_based", "hybrid"]:
                alg_count = self.db.execute(
                    select(func.count(Recommendation.id)).where(
                        and_(
                            Recommendation.algorithm == alg,
                            Recommendation.created_at >= cutoff_date,
                        )
                    )
                ).scalar() or 0

                if alg_count > 0:
                    algorithm_performance.append(
                        {"algorithm": alg, "count": alg_count}
                    )

            result = RecommendationStatsResponse(
                period=period,
                quality_metrics=quality_metrics,
                algorithm_performance=algorithm_performance,
                cached_at=datetime.now(timezone.utc),
            )

            await self._set_to_cache(cache_key, result.model_dump())
            return result

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            # Возвращаем пустую статистику
            return RecommendationStatsResponse(
                period=period,
                quality_metrics=RecommendationQualityMetrics(
                    click_through_rate=0.0,
                    average_watch_time_seconds=0.0,
                    feedback_positive_rate=0.0,
                    total_recommendations_shown=0,
                    total_interactions=0,
                ),
                algorithm_performance=[],
                cached_at=datetime.now(timezone.utc),
            )


def get_recommendation_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None,
    database_url: Optional[str] = None,
) -> RecommendationService:
    """
    Фабрика для создания сервиса рекомендаций.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент
        database_url: Опциональный URL базы данных

    Returns:
        RecommendationService instance
    """
    return RecommendationService(
        db=db, redis_client=redis_client, database_url=database_url
    )
