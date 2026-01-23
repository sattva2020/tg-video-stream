"""
Recommendation models for AI-powered content suggestions.
Feature: 014-ai-powered-content-recommendations
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, BigInteger, DateTime, Numeric, ForeignKey, Index, String, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


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
