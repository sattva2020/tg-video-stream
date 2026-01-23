"""GuestSession ORM Model.

SQLAlchemy model для персистентности Guest Session (со-ведущие в live streams).
Создан в рамках Feature 019 (Real-Time Live Streaming Capabilities).

**Purpose**: Хранение состояния guest co-hosting sessions в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется для управления guest sessions в live streaming

**Schema Reference**: См. specs/019-real-time-live-streaming-capabilities/spec.md
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class GuestSessionStatus(str, PyEnum):
    """Статусы guest session."""
    PENDING = "pending"           # Guest invited, waiting to accept
    ACCEPTED = "accepted"         # Guest accepted, waiting to join
    ACTIVE = "active"             # Guest actively participating
    REJECTED = "rejected"         # Guest declined invitation
    LEFT = "left"                 # Guest left the session
    KICKED = "kicked"             # Guest was removed by host


class GuestPermission(str, PyEnum):
    """Разрешения для guest co-hosts."""
    CAN_SPEAK = "can_speak"                   # Может использовать микрофон
    CAN_SHARE_VIDEO = "can_share_video"       # Может включать камеру
    CAN_SHARE_SCREEN = "can_share_screen"     # Может демонстрировать экран
    CAN_CONTROL_STREAM = "can_control_stream" # Может управлять потоком (start/stop)
    CAN_INVITE_OTHERS = "can_invite_others"   # Может приглашать других гостей


class GuestSession(Base):
    """ORM Model для guest co-hosting sessions.

    **Table**: guest_sessions
    **Purpose**: Управление состоянием guest co-hosts в live streams

    **Relationships**:
    - live_stream: LiveStream (FK to live_streams.id)
    - user: User (FK to users.id)

    **Permissions**:
    Guest co-hosts can have granular permissions:
    - can_speak: Может использовать микрофон
    - can_share_video: Может включать камеру
    - can_share_screen: Может демонстрировать экран
    - can_control_stream: Может управлять потоком
    - can_invite_others: Может приглашать других гостей

    **Timestamps**:
    - created_at: Время создания приглашения
    - joined_at: Время когда guest присоединился к сессии
    - left_at: Время когда guest покинул сессию
    """
    __tablename__ = "guest_sessions"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    live_stream_id = Column(GUID(), ForeignKey("live_streams.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Session Status
    status = Column(
        SQLEnum(GuestSessionStatus, name="guest_session_status", create_type=True),
        nullable=False,
        default=GuestSessionStatus.PENDING,
        comment="Текущий статус guest session"
    )

    # Guest Permissions (bitmask-style or individual booleans)
    can_speak = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Разрешение на использование микрофона"
    )
    can_share_video = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Разрешение на включение камеры"
    )
    can_share_screen = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Разрешение на демонстрацию экрана"
    )
    can_control_stream = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Разрешение на управление потоком"
    )
    can_invite_others = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Разрешение на приглашение других гостей"
    )

    # WebRTC Connection Tracking
    webrtc_connection_id = Column(
        String(255),
        nullable=True,
        unique=True,
        comment="Уникальный ID WebRTC соединения"
    )
    connection_quality = Column(
        String(50),
        nullable=True,
        comment="Качество соединения (poor, fair, good, excellent)"
    )

    # Metadata
    invite_token = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Уникальный токен для приглашения"
    )
    invite_message = Column(
        Text,
        nullable=True,
        comment="Персональное сообщение в приглашении"
    )

    # Rejection/Leave Reason
    rejection_reason = Column(
        Text,
        nullable=True,
        comment="Причина отказа (если rejected)"
    )
    leave_reason = Column(
        Text,
        nullable=True,
        comment="Причина выхода (если left)"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания приглашения"
    )
    joined_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время когда guest присоединился к сессии"
    )
    left_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время когда guest покинул сессию"
    )
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней активности"
    )

    # Relationships
    live_stream = relationship(
        "src.models.live_stream.LiveStream",
        back_populates="guest_sessions",
        lazy="joined"
    )
    user = relationship(
        "src.models.user.User",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<GuestSession(id={self.id}, user_id={self.user_id}, status={self.status}, live_stream_id={self.live_stream_id})>"

    def mark_as_joined(self) -> None:
        """Отметить guest как присоединившегося к сессии."""
        self.status = GuestSessionStatus.ACTIVE
        self.joined_at = datetime.now(timezone.utc)
        self.last_active_at = datetime.now(timezone.utc)

    def mark_as_left(self, reason: str | None = None) -> None:
        """Отметить guest как покинувшего сессию."""
        self.status = GuestSessionStatus.LEFT
        self.left_at = datetime.now(timezone.utc)
        if reason:
            self.leave_reason = reason

    def mark_as_rejected(self, reason: str | None = None) -> None:
        """Отметить что guest отклонил приглашение."""
        self.status = GuestSessionStatus.REJECTED
        if reason:
            self.rejection_reason = reason

    def update_last_active(self) -> None:
        """Обновить время последней активности."""
        self.last_active_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Проверить, активно ли участие guest в сессии."""
        return self.status == GuestSessionStatus.ACTIVE

    def has_permission(self, permission: GuestPermission) -> bool:
        """Проверить наличие конкретного разрешения."""
        permissions_map = {
            GuestPermission.CAN_SPEAK: self.can_speak,
            GuestPermission.CAN_SHARE_VIDEO: self.can_share_video,
            GuestPermission.CAN_SHARE_SCREEN: self.can_share_screen,
            GuestPermission.CAN_CONTROL_STREAM: self.can_control_stream,
            GuestPermission.CAN_INVITE_OTHERS: self.can_invite_others,
        }
        return permissions_map.get(permission, False)

    def grant_permission(self, permission: GuestPermission) -> None:
        """Выдать разрешение guest."""
        if permission == GuestPermission.CAN_SPEAK:
            self.can_speak = True
        elif permission == GuestPermission.CAN_SHARE_VIDEO:
            self.can_share_video = True
        elif permission == GuestPermission.CAN_SHARE_SCREEN:
            self.can_share_screen = True
        elif permission == GuestPermission.CAN_CONTROL_STREAM:
            self.can_control_stream = True
        elif permission == GuestPermission.CAN_INVITE_OTHERS:
            self.can_invite_others = True

    def revoke_permission(self, permission: GuestPermission) -> None:
        """Отозвать разрешение у guest."""
        if permission == GuestPermission.CAN_SPEAK:
            self.can_speak = False
        elif permission == GuestPermission.CAN_SHARE_VIDEO:
            self.can_share_video = False
        elif permission == GuestPermission.CAN_SHARE_SCREEN:
            self.can_share_screen = False
        elif permission == GuestPermission.CAN_CONTROL_STREAM:
            self.can_control_stream = False
        elif permission == GuestPermission.CAN_INVITE_OTHERS:
            self.can_invite_others = False
