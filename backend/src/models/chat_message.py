"""
Chat message models for cross-platform chat aggregation.
Feature: 021-social-media-integration-cross-platform-broadcasting
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class ChatMessage(Base):
    """
    Сообщение из чата платформы стриминга.
    Агрегирует сообщения с разных платформ для отображения в едином интерфейсе.
    """
    __tablename__ = "chat_messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    # Ссылка на платформу (streaming_platforms.id)
    platform_id = Column(GUID(), ForeignKey("streaming_platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    # Ссылка на канал (channels.id)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    # ID сообщения на платформе (для дедупликации)
    platform_message_id = Column(String(255), nullable=False, index=True)
    # Имя автора сообщения
    author_name = Column(String(255), nullable=False)
    # Отображаемое имя автора (может отличаться от username)
    author_display_name = Column(String(255), nullable=True)
    # Текст сообщения
    content = Column(Text, nullable=False)
    # Время отправки сообщения на платформе (timezone-aware)
    message_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    # Цвет автора (для отображения в UI)
    author_color = Column(String(7), nullable=True)  # hex color like #FF5733
    # Дополнительные данные о сообщении (JSON)
    metadata = Column(Text, nullable=True)
    # Время создания записи в БД
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    platform = relationship("StreamingPlatform", backref="chat_messages")
    channel = relationship("Channel", backref="chat_messages")

    # Indexes for performance
    __table_args__ = (
        Index('idx_chat_messages_platform_channel', 'platform_id', 'channel_id'),
        Index('idx_chat_messages_timestamp', 'message_timestamp'),
        Index('idx_chat_messages_platform_message_id', 'platform_id', 'platform_message_id'),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, author={self.author_name}, platform={self.platform_id})>"
