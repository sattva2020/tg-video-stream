"""Engagement ORM Models.

SQLAlchemy models для персистентности Shoutout и CTA Entities (viewer engagement).
Создан в рамках Feature 020 (Viewer Interaction & Engagement Features).

**Purpose**: Хранение состояния shoutouts и call-to-action в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется EngagementMapper для конвертации Entity ↔ ORM

**Design Decision**:
- NEW models для поддержки viewer shoutouts и interactive CTAs
- Shoutout: highlight new followers, subscribers, donors
- CTA: prompt viewers to take actions (subscribe, visit link, donate)
- Поддержка manual и automatic triggers
- Отслеживание engagement metrics (display, click, dismiss counts)

**Schema Reference**: См. specs/020-viewer-interaction-engagement-features/spec.md
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, func, Index, Text
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class ShoutoutType(str, PyEnum):
    """Типы shoutouts."""
    NEW_FOLLOWER = "new_follower"       # Новый подписчик
    NEW_SUBSCRIBER = "new_subscriber"   # Новый платный подписчик
    DONOR = "donor"                     # Донор
    TOP_VIEWER = "top_viewer"           # Активный зритель
    CUSTOM = "custom"                   # Произвольный shoutout


class ShoutoutStatus(str, PyEnum):
    """Статусы shoutouts."""
    PENDING = "pending"       # Ожидает отображения
    DISPLAYED = "displayed"   # Отображен
    SKIPPED = "skipped"       # Пропущен
    CANCELLED = "cancelled"   # Отменен


class CTAStatus(str, PyEnum):
    """Статусы CTAs."""
    DRAFT = "draft"           # Черновик
    SCHEDULED = "scheduled"   # Запланирован
    ACTIVE = "active"         # Активен (отображается)
    PAUSED = "paused"         # Приостановлен
    COMPLETED = "completed"   # Завершен
    EXPIRED = "expired"       # Истек срок действия


class ActionType(str, PyEnum):
    """Типы действий для CTA."""
    SUBSCRIBE = "subscribe"           # Подписаться на канал
    VISIT_LINK = "visit_link"         # Перейти по ссылке
    DONATE = "donate"                 # Сделать донат
    FOLLOW_SOCIAL = "follow_social"   # Подписаться в соцсети
    JOIN_GROUP = "join_group"         # Вступить в группу
    CUSTOM = "custom"                 # Произвольное действие


class Shoutout(Base):
    """ORM Model для viewer shoutouts.

    **Table**: shoutouts
    **Entity Mapping**: См. infrastructure/persistence/mappers/engagement_mapper.py

    **Relationships**:
    - stream: Stream (FK to streams.id)
    - triggered_by: User (FK to users.id, nullable - user who triggered)

    **Timestamps**:
    - created_at: Время создания shoutout
    - displayed_at: Время отображения (NULL если не отображался)
    - expires_at: Время окончания отображения (для overlay)

    **Use Cases**:
    - Highlight new followers/subscribers
    - Thank donors
    - Recognize top viewers
    - Custom announcements
    """
    __tablename__ = "shoutouts"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=False, index=True)
    triggered_by_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # Core Fields
    shoutout_type = Column(
        SQLEnum(ShoutoutType, name="shoutout_type", create_type=True),
        nullable=False,
        default=ShoutoutType.CUSTOM,
        comment="Тип shoutout"
    )
    status = Column(
        SQLEnum(ShoutoutStatus, name="shoutout_status", create_type=True),
        nullable=False,
        default=ShoutoutStatus.PENDING,
        comment="Текущий статус shoutout"
    )

    # Recipient information
    recipient_name = Column(
        String(255),
        nullable=False,
        comment="Имя получателя shoutout"
    )
    recipient_handle = Column(
        String(255),
        nullable=True,
        comment="Username/handle получателя (опционально)"
    )
    recipient_avatar_url = Column(
        String(500),
        nullable=True,
        comment="URL аватара получателя (опционально)"
    )

    # Message content
    title = Column(
        String(255),
        nullable=True,
        comment="Заголовок shoutout (опционально)"
    )
    message = Column(
        Text,
        nullable=True,
        comment="Сообщение shoutout (опционально)"
    )

    # Display settings
    display_duration = Column(
        Integer,
        nullable=False,
        default=10,
        comment="Длительность отображения в секундах"
    )
    priority = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Приоритет отображения (higher = раньше)"
    )
    is_pinned = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Закреплен для отображения"
    )

    # Trigger information
    trigger_type = Column(
        String(50),
        nullable=False,
        default="manual",
        comment="Тип триггера (manual, auto_follower, auto_subscriber, etc.)"
    )
    trigger_metadata = Column(
        Text,
        nullable=True,
        comment="JSON метаданные триггера (опционально)"
    )

    # Moderation
    is_filtered = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Shoutout отфильтрован модерацией"
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
        comment="Время создания shoutout"
    )
    displayed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время отображения (NULL если не отображался)"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время окончания отображения (NULL = бессрочно)"
    )

    # Relationships
    stream = relationship("src.models.stream.Stream", lazy="joined")
    triggered_by = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_shoutouts_stream_status", "stream_id", "status"),
        Index("ix_shoutouts_stream_priority", "stream_id", "priority"),
        Index("ix_shoutouts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Shoutout(id={self.id}, type={self.shoutout_type}, recipient='{self.recipient_name}', status={self.status})>"


class CTA(Base):
    """ORM Model для Call-To-Actions.

    **Table**: ctas
    **Entity Mapping**: См. infrastructure/persistence/mappers/engagement_mapper.py

    **Relationships**:
    - stream: Stream (FK to streams.id)
    - created_by: User (FK to users.id)

    **Timestamps**:
    - created_at: Время создания CTA
    - scheduled_at: Запланированное время отображения
    - expires_at: Время окончания действия

    **Use Cases**:
    - Prompt viewers to subscribe
    - Direct viewers to external links
    - Encourage donations
    - Promote social media follows
    - Custom engagement actions

    **Metrics**:
    - display_count: Сколько раз отображался
    - dismiss_count: Сколько раз закрыли
    - click_count: Сколько раз кликнули
    """
    __tablename__ = "ctas"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=False, index=True)
    created_by_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Core Fields
    action_type = Column(
        SQLEnum(ActionType, name="cta_action_type", create_type=True),
        nullable=False,
        default=ActionType.CUSTOM,
        comment="Тип действия CTA"
    )
    status = Column(
        SQLEnum(CTAStatus, name="cta_status", create_type=True),
        nullable=False,
        default=CTAStatus.DRAFT,
        comment="Текущий статус CTA"
    )

    # Content
    title = Column(
        String(255),
        nullable=False,
        comment="Заголовок CTA"
    )
    message = Column(
        Text,
        nullable=True,
        comment="Сообщение CTA (опционально)"
    )

    # Action details
    action_url = Column(
        String(1000),
        nullable=True,
        comment="URL для действия (для visit_link, donate, etc.)"
    )
    button_text = Column(
        String(100),
        nullable=False,
        default="Learn More",
        comment="Текст на кнопке действия"
    )
    button_color = Column(
        String(20),
        nullable=True,
        comment="Цвет кнопки (hex код, опционально)"
    )

    # Display settings
    is_dismissable = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Можно ли закрыть CTA"
    )
    display_duration = Column(
        Integer,
        nullable=True,
        comment="Длительность отображения в секундах (NULL = пока не закроют)"
    )
    position = Column(
        String(50),
        nullable=False,
        default="bottom-right",
        comment="Позиция на overlay (top-left, top-right, bottom-left, bottom-right, center)"
    )
    priority = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Приоритет отображения (higher = раньше)"
    )

    # Scheduling
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Запланированное время отображения (NULL = немедленно)"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время окончания действия (NULL = бессрочно)"
    )

    # Engagement metrics
    display_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Сколько раз отображался"
    )
    dismiss_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Сколько раз закрыли"
    )
    click_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Сколько раз кликнули"
    )
    conversion_rate = Column(
        Integer,
        nullable=True,
        comment="Коэффициент конверсии в % (clicks / displays * 100)"
    )

    # Moderation
    is_filtered = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="CTA отфильтрован модерацией"
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
        comment="Время создания CTA"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Время последнего обновления"
    )

    # Relationships
    stream = relationship("src.models.stream.Stream", lazy="joined")
    created_by = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_ctas_stream_status", "stream_id", "status"),
        Index("ix_ctas_scheduled_at", "scheduled_at"),
        Index("ix_ctas_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<CTA(id={self.id}, title='{self.title}', action={self.action_type}, status={self.status})>"
