"""
Recommendation API schemas
Feature: 014-ai-powered-content-recommendations
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

RecommendationAlgorithm = Literal["collaborative_filtering", "content_based", "hybrid"]
FeedbackType = Literal["like", "dislike"]
InteractionType = Literal["watch", "skip", "like", "share", "click"]


# === Recommendation Schemas ===

class RecommendationItem(BaseModel):
    """Один рекомендованный элемент."""
    playlist_item_id: str = Field(..., description="ID элемента плейлиста")
    title: str = Field(..., description="Название видео")
    artist: Optional[str] = Field(None, description="Исполнитель/Автор")
    score: float = Field(..., ge=0, le=1, description="Уверенность рекомендации от 0 до 1")
    algorithm: RecommendationAlgorithm = Field(..., description="Алгоритм рекомендации")
    reason: Optional[str] = Field(None, description="Причина рекомендации (например, 'Похоже на то, что вы смотрели')")


class RecommendationRequest(BaseModel):
    """Запрос на получение рекомендаций."""
    user_id: Optional[str] = Field(None, description="ID пользователя (опционально, берется из auth)")
    playlist_id: Optional[int] = Field(None, description="ID плейлиста для получения рекомендаций для плейлиста")
    limit: int = Field(10, ge=1, le=100, description="Количество рекомендаций (максимум 100)")
    algorithm: RecommendationAlgorithm = Field("hybrid", description="Алгоритм рекомендации")
    exclude_watched: bool = Field(True, description="Исключать уже просмотренное")


class RecommendationResponse(BaseModel):
    """Список рекомендаций для пользователя."""
    recommendations: List[RecommendationItem] = Field(default_factory=list, description="Список рекомендаций")
    total_count: int = Field(..., ge=0, description="Общее количество рекомендаций")
    algorithm: RecommendationAlgorithm = Field(..., description="Использованный алгоритм")
    generated_at: datetime = Field(..., description="Время генерации рекомендаций")


# === Feedback Schemas ===

class FeedbackRequest(BaseModel):
    """Запрос на добавление обратной связи."""
    playlist_item_id: str = Field(..., description="ID элемента плейлиста")
    feedback_type: FeedbackType = Field(..., description="Тип обратной связи: like или dislike")


class FeedbackResponse(BaseModel):
    """Ответ на добавление обратной связи."""
    id: int = Field(..., description="ID записи обратной связи")
    playlist_item_id: str = Field(..., description="ID элемента плейлиста")
    feedback_type: FeedbackType = Field(..., description="Тип обратной связи")
    created_at: datetime = Field(..., description="Время создания записи")


# === Interaction Schemas ===

class InteractionRequest(BaseModel):
    """Запрос на запись взаимодействия."""
    playlist_item_id: str = Field(..., description="ID элемента плейлиста")
    interaction_type: InteractionType = Field(..., description="Тип взаимодействия")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Длительность в секундах")
    completion_rate: Optional[float] = Field(None, ge=0, le=1, description="Доля просмотра от 0 до 1")


class InteractionResponse(BaseModel):
    """Ответ на запись взаимодействия."""
    id: int = Field(..., description="ID записи взаимодействия")
    playlist_item_id: str = Field(..., description="ID элемента плейлиста")
    interaction_type: InteractionType = Field(..., description="Тип взаимодействия")
    interacted_at: datetime = Field(..., description="Время записи")


# === Stats Schemas ===

class RecommendationQualityMetrics(BaseModel):
    """Метрики качества рекомендаций."""
    click_through_rate: float = Field(..., ge=0, le=1, description="CTR (доля кликов по рекомендациям)")
    average_watch_time_seconds: float = Field(..., ge=0, description="Среднее время просмотра")
    feedback_positive_rate: float = Field(..., ge=0, le=1, description="Доля положительной обратной связи")
    total_recommendations_shown: int = Field(..., ge=0, description="Общее количество показанных рекомендаций")
    total_interactions: int = Field(..., ge=0, description="Общее количество взаимодействий")


class RecommendationStatsResponse(BaseModel):
    """Статистика рекомендаций."""
    period: str = Field(..., description="Период данных (например, '7d', '30d')")
    quality_metrics: RecommendationQualityMetrics = Field(..., description="Метрики качества")
    algorithm_performance: List[dict] = Field(default_factory=list, description="Производительность по алгоритмам")
    cached_at: datetime = Field(..., description="Время кэширования")
