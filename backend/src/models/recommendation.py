"""
Recommendation models for AI-powered content suggestions.
Feature: 014-ai-powered-content-recommendations
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import Column, BigInteger, DateTime, Numeric, ForeignKey, Index, String, CheckConstraint, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class FeedbackType(str, PyEnum):
    """Тип обратной связи на рекомендацию."""
    LIKE = "like"
    DISLIKE = "dislike"


class Recommendation(Base):
    """
    AI-генерируемая рекомендация контента для пользователя.
    Хранит результаты работы рекомендательных алгоритмов.
    """
    __tablename__ = "recommendations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Пользователь, для которого создана рекомендация
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Рекомендуемый элемент плейлиста
    playlist_item_id = Column(GUID(), ForeignKey("playlist_items.id", ondelete="CASCADE"), nullable=False, index=True)
    # Алгоритм, который сгенерировал рекомендацию
    algorithm = Column(String, nullable=False, comment='collaborative_filtering, content_based, hybrid')
    # Уверенность рекомендации от 0 до 1
    score = Column(Numeric(5, 4), nullable=False, comment='Уверенность рекомендации от 0 до 1')
    # Время создания рекомендации
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", backref="recommendations")
    playlist_item = relationship("PlaylistItem", backref="recommendations")

    # Indexes for performance
    __table_args__ = (
        Index('idx_recommendations_user_id', 'user_id'),
        Index('idx_recommendations_playlist_item_id', 'playlist_item_id'),
        Index('idx_recommendations_score', 'score'),
        Index('idx_recommendations_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Recommendation(id={self.id}, user_id={self.user_id}, score={self.score}, algorithm={self.algorithm})>"


class RecommendationFeedback(Base):
    """
    Обратная связь пользователя на рекомендацию.
    Пользователи могут лайкать или дизлайкать рекомендации для улучшения алгоритмов.
    """
    __tablename__ = "recommendation_feedback"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Пользователь, оставивший обратную связь
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Рекомендуемый элемент плейлиста
    playlist_item_id = Column(GUID(), ForeignKey("playlist_items.id", ondelete="CASCADE"), nullable=False, index=True)
    # Тип обратной связи: like или dislike
    feedback_type = Column(String(10), nullable=False, comment='like или dislike')
    # Время создания обратной связи
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", backref="recommendation_feedback")
    playlist_item = relationship("PlaylistItem", backref="recommendation_feedback")

    # Indexes and constraints for performance
    __table_args__ = (
        Index('idx_recommendation_feedback_user_id', 'user_id'),
        Index('idx_recommendation_feedback_playlist_item_id', 'playlist_item_id'),
        Index('idx_recommendation_feedback_feedback_type', 'feedback_type'),
        Index('idx_recommendation_feedback_created_at', 'created_at'),
        CheckConstraint(
            "feedback_type IN ('like', 'dislike')",
            name='ck_recommendation_feedback_type'
        ),
    )

    def __repr__(self):
        return f"<RecommendationFeedback(id={self.id}, user_id={self.user_id}, feedback_type={self.feedback_type})>"


class UserItemInteraction(Base):
    """
    Запись о взаимодействии пользователя с контентом.
    Основной источник данных для коллаборативной фильтрации.
    Агрегирует данные из TrackPlay для построения матрицы пользователь-предмет.
    """
    __tablename__ = "user_item_interactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Пользователь, взаимодействовавший с контентом
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Элемент плейлиста, с которым было взаимодействие
    playlist_item_id = Column(GUID(), ForeignKey("playlist_items.id", ondelete="CASCADE"), nullable=False, index=True)
    # Тип взаимодействия: watch, skip, like, share
    interaction_type = Column(String(20), nullable=False, comment='Тип взаимодействия')
    # Длительность взаимодействия в секундах (для watch)
    duration_seconds = Column(BigInteger, nullable=True, comment='Длительность просмотра в секундах')
    # Доля просмотра от 0 до 1 (например, 0.5 = просмотрено 50%)
    completion_rate = Column(Numeric(5, 4), nullable=True, comment='Доля просмотра от 0 до 1')
    # Время взаимодействия (timezone-aware)
    interacted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    # Дополнительные метаданные (JSON) для расширения
    metadata = Column(String, nullable=True, comment='Дополнительные метаданные в формате JSON')

    # Relationships
    user = relationship("User", backref="item_interactions")
    playlist_item = relationship("PlaylistItem", backref="user_interactions")

    # Indexes and constraints for performance
    __table_args__ = (
        Index('idx_user_item_interactions_user_id', 'user_id'),
        Index('idx_user_item_interactions_playlist_item_id', 'playlist_item_id'),
        Index('idx_user_item_interactions_interaction_type', 'interaction_type'),
        Index('idx_user_item_interactions_interacted_at', 'interacted_at'),
        Index('idx_user_item_interactions_user_item', 'user_id', 'playlist_item_id'),
        CheckConstraint(
            "interaction_type IN ('watch', 'skip', 'like', 'share', 'click')",
            name='ck_user_item_interactions_type'
        ),
        CheckConstraint(
            "(completion_rate IS NULL OR completion_rate >= 0 AND completion_rate <= 1)",
            name='ck_user_item_interactions_completion_rate'
        ),
    )

    def __repr__(self):
        return f"<UserItemInteraction(id={self.id}, user_id={self.user_id}, interaction_type={self.interaction_type})>"
