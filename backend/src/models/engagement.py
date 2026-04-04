"""
Engagement models for tracking chat activity, reactions, and comments.
Feature: 012-comprehensive-analytics-dashboard
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, DateTime, String, Text, ForeignKey, Index, JSON, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class EngagementEvent(Base):
    """
    Запись о событиях вовлеченности аудитории.
    Отслеживает сообщения в чате, реакции и комментарии.
    """
    __tablename__ = "engagement_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Тип события: chat_message, reaction, comment
    event_type = Column(String(50), nullable=False, index=True)
    # Ссылка на channels.id (UUID)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    # Telegram user ID (может быть NULL для анонимных пользователей)
    user_id = Column(BigInteger, nullable=True, index=True)
    # Имя пользователя (для отображения в аналитике)
    username = Column(String(255), nullable=True)
    # Содержимое события (текст сообщения, текст комментария)
    content = Column(Text, nullable=True)
    # Дополнительные метаданные (например, тип эмодзи для реакций)
    metadata = Column(JSON, nullable=True)
    # Время события (timezone-aware)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    channel = relationship("Channel", backref="engagement_events")

    # Indexes for performance
    __table_args__ = (
        Index('idx_engagement_events_type_timestamp', 'event_type', 'event_timestamp'),
        Index('idx_engagement_events_channel_timestamp', 'channel_id', 'event_timestamp'),
        Index('idx_engagement_events_user_timestamp', 'user_id', 'event_timestamp'),
    )

    def __repr__(self):
        return f"<EngagementEvent(id={self.id}, type={self.event_type}, channel={self.channel_id}, timestamp={self.event_timestamp})>"
