"""
Viewer session models for tracking individual viewing sessions and drop-off points.
Feature: 012-comprehensive-analytics-dashboard
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, DateTime, String, ForeignKey, Index, Integer, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class ViewerSession(Base):
    """
    Запись о сессии просмотра/прослушивания.
    Отслеживает индивидуальные сессии и точки отказа (drop-off points).
    """
    __tablename__ = "viewer_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Уникальный идентификатор сессии
    session_id = Column(GUID(), nullable=False, default=uuid.uuid4, unique=True, index=True)
    # Ссылка на playlist_items.id (UUID)
    playlist_item_id = Column(GUID(), ForeignKey("playlist_items.id", ondelete="SET NULL"), nullable=True, index=True)
    # Идентификатор пользователя (если известен)
    user_id = Column(BigInteger, nullable=True, index=True)
    # Время начала сессии (timezone-aware)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    # Время окончания сессии (nullable - если сессия активна)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    # Точка отказа - позиция в секундах, где пользователь остановился
    drop_off_position_seconds = Column(Integer, nullable=True)
    # Полная длительность контента в секундах
    content_duration_seconds = Column(Integer, nullable=True)
    # Процент просмотра (вычисляется как drop_off_position / content_duration * 100)
    completion_percentage = Column(Integer, nullable=True)
    # IP-адрес пользователя (опционально, для аналитики)
    ip_address = Column(String(45), nullable=True)
    # User Agent (опционально)
    user_agent = Column(String(255), nullable=True)

    # Relationships
    playlist_item = relationship("PlaylistItem", backref="viewer_sessions")

    # Indexes for performance
    __table_args__ = (
        Index('idx_viewer_sessions_session_id', 'session_id'),
        Index('idx_viewer_sessions_started_at', 'started_at'),
        Index('idx_viewer_sessions_user_id', 'user_id'),
        Index('idx_viewer_sessions_playlist_item', 'playlist_item_id'),
    )

    def __repr__(self):
        return f"<ViewerSession(id={self.id}, session_id={self.session_id}, started_at={self.started_at})>"
