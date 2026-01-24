"""Interaction ORM Models.

SQLAlchemy models для персистентности EmojiReaction и ChatMessage Entities.
Создан в рамках Feature 020 (Viewer Interaction & Engagement Features).

**Purpose**: Хранение состояния эмодзи-реакций и чат-сообщений в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется InteractionMapper для конвертации Entity ↔ ORM

**Design Decision**:
- NEW models для поддержки emoji reactions overlay и chat overlay
- Поддержка anonymous и authenticated interactions
- Позиционирование для overlay отображения
- Автоматическое удаление устаревших реакций (ttl)

**Schema Reference**: См. specs/020-viewer-interaction-engagement-features/spec.md
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, func, Index, Text
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class ReactionDisplayStatus(str, PyEnum):
    """Статусы отображения реакций."""
    PENDING = "pending"       # Ожидает отображения
    VISIBLE = "visible"       # Отображается на overlay
    EXPIRED = "expired"       # Истекшее время отображения
    HIDDEN = "hidden"         # Скрыто модерацией


class ChatMessageStatus(str, PyEnum):
    """Статусы чат-сообщений."""
    PENDING = "pending"       # Ожидает отображения
    VISIBLE = "visible"       # Отображается на overlay
    HIDDEN = "hidden"         # Скрыто модерацией
    FLAGGED = "flagged"       # Помечено для проверки


class EmojiReaction(Base):
    """ORM Model для эмодзи-реакций зрителей.

    **Table**: emoji_reactions
    **Entity Mapping**: См. infrastructure/persistence/mappers/interaction_mapper.py

    **Relationships**:
    - stream: Stream (FK to streams.id)
    - user: User (FK to users.id, nullable)

    **Timestamps**:
    - created_at: Время создания реакции
    - expires_at: Время окончания отображения (ttl для overlay)

    **Overlay Fields**:
    - position_x, position_y: Координаты для отображения на overlay
    - scale: Размер эмодзи
    - animation_type: Тип анимации появления
    """
    __tablename__ = "emoji_reactions"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # User identification (for anonymous users)
    telegram_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram ID для анонимных пользователей"
    )

    # Core Fields
    emoji = Column(
        String(100),
        nullable=False,
        comment="Эмодзи (Unicode or shortname)"
    )
    display_status = Column(
        SQLEnum(ReactionDisplayStatus, name="reaction_display_status", create_type=True),
        nullable=False,
        default=ReactionDisplayStatus.PENDING,
        comment="Статус отображения реакции"
    )

    # Overlay positioning
    position_x = Column(
        Integer,
        nullable=False,
        default=50,
        comment="Позиция X на overlay (0-100%)"
    )
    position_y = Column(
        Integer,
        nullable=False,
        default=50,
        comment="Позиция Y на overlay (0-100%)"
    )
    scale = Column(
        Integer,
        nullable=False,
        default=100,
        comment="Размер эмодзи в процентах"
    )
    animation_type = Column(
        String(50),
        nullable=True,
        comment="Тип анимации (fade, pop, bounce, etc.)"
    )

    # Moderation
    is_filtered = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Реакция отфильтрована модерацией"
    )
    filter_reason = Column(
        String(500),
        nullable=True,
        comment="Причина фильтрации"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания реакции"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время окончания отображения (NULL = бессрочно)"
    )

    # Relationships
    stream = relationship("src.models.stream.Stream", lazy="joined")
    user = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_emoji_reactions_stream_status", "stream_id", "display_status"),
        Index("ix_emoji_reactions_stream_created", "stream_id", "created_at"),
        Index("ix_emoji_reactions_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<EmojiReaction(id={self.id}, emoji='{self.emoji}', stream_id={self.stream_id})>"


class ChatMessage(Base):
    """ORM Model для чат-сообщений (Telegram chat overlay).

    **Table**: chat_messages
    **Entity Mapping**: См. infrastructure/persistence/mappers/interaction_mapper.py

    **Relationships**:
    - stream: Stream (FK to streams.id)
    - author: User (FK to users.id, nullable)

    **Timestamps**:
    - created_at: Время получения сообщения
    - original_timestamp: Оригинальное время из Telegram

    **Design Notes**:
    - Хранит сообщения для отображения на stream overlay
    - Поддерживает anonymous и authenticated авторов
    - Модерация через флаги is_filtered и filter_reason
    """
    __tablename__ = "chat_messages"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=False, index=True)
    author_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # User identification (for anonymous users)
    telegram_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram ID для анонимных пользователей"
    )
    author_name = Column(
        String(255),
        nullable=False,
        comment="Имя автора для отображения"
    )
    author_avatar_url = Column(
        String(500),
        nullable=True,
        comment="URL аватара автора (опционально)"
    )

    # Core Fields
    content = Column(
        Text,
        nullable=False,
        comment="Текст сообщения"
    )
    message_status = Column(
        SQLEnum(ChatMessageStatus, name="chat_message_status", create_type=True),
        nullable=False,
        default=ChatMessageStatus.PENDING,
        comment="Статус отображения сообщения"
    )

    # Telegram-specific fields
    telegram_message_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Оригинальный ID сообщения из Telegram"
    )
    original_timestamp = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Оригинальное время отправки в Telegram"
    )

    # Moderation
    is_filtered = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Сообщение отфильтровано модерацией"
    )
    filter_reason = Column(
        String(500),
        nullable=True,
        comment="Причина фильтрации"
    )
    is_flagged = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Сообщение помечено для проверки"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время получения сообщения"
    )

    # Relationships
    stream = relationship("src.models.stream.Stream", lazy="joined")
    author = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_chat_messages_stream_status", "stream_id", "message_status"),
        Index("ix_chat_messages_stream_created", "stream_id", "created_at"),
        Index("ix_chat_messages_telegram_id", "telegram_message_id"),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] if self.content else ""
        return f"<ChatMessage(id={self.id}, author='{self.author_name}', content='{content_preview}...')>"
