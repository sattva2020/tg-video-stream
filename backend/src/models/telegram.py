"""Telegram ORM Models.

SQLAlchemy models для персистентности Telegram Account и Channel entities.
Создан в рамках Session Management Automation (spec 002).

**Purpose**: Хранение состояния Telegram accounts и channels в PostgreSQL
**Layer**: Infrastructure (persistence)

**Design Decision**:
- TelegramAccount: управление Telegram accounts с автоматическим refresh сессий
- Channel: конфигурация channels для трансляции из Telegram chats
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, BigInteger, Boolean, Integer, func
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class SessionHealthStatus(str, PyEnum):
    """Статусы здоровья Telegram session."""
    HEALTHY = "healthy"           # Session активна и валидна
    EXPIRING = "expiring"         # Session скоро истекает (требует refresh)
    EXPIRED = "expired"           # Session истекла (требует ре-authorization)
    NEEDS_2FA = "needs_2fa"       # Требуется двухфакторная аутентификация
    ERROR = "error"               # Ошибка session (требует диагностики)


class TelegramAccount(Base):
    """ORM Model для Telegram accounts.

    **Table**: telegram_accounts
    **Purpose**: Управление Telegram accounts с автоматическим мониторингом и refresh сессий

    **Relationships**:
    - user: User (FK to users.id)
    - channels: List[Channel] (one-to-many)

    **Session Health**:
    - session_health_status: Текущий статус здоровья session
    - session_expires_at: Время истечения session
    - auto_refresh_enabled: Автоматический refresh перед истечением
    - refresh_before_expires_hours: За сколько часов до истечения делать refresh

    **Timestamps**:
    - created_at: Время создания account
    - updated_at: Время последнего обновления
    - last_health_check: Время последней проверки здоровья session
    - last_refreshed_at: Время последнего refresh session
    """
    __tablename__ = "telegram_accounts"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Core Fields
    phone = Column(String, nullable=False, comment="Номер телефона")
    encrypted_session = Column(String, nullable=False, comment="Зашифрованная Telegram session")
    tg_user_id = Column(BigInteger, nullable=True, comment="Telegram User ID (64-bit)")
    first_name = Column(String, nullable=True, comment="Имя пользователя Telegram")
    username = Column(String, nullable=True, comment="Username Telegram")
    photo_url = Column(String, nullable=True, comment="URL фото профиля")

    # Session Health Fields
    session_health_status = Column(
        SQLEnum(SessionHealthStatus, name="session_health_status", create_type=True),
        nullable=True,
        comment="Текущий статус здоровья session"
    )
    last_health_check = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней проверки здоровья session"
    )
    session_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время истечения session"
    )
    totp_secret = Column(
        String,
        nullable=True,
        comment="Зашифрованный TOTP secret для 2FA"
    )
    auto_refresh_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Автоматический refresh перед истечением session"
    )
    refresh_before_expires_hours = Column(
        Integer,
        default=24,
        nullable=False,
        comment="За сколько часов до истечения делать refresh"
    )
    last_refreshed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего refresh session"
    )
    refresh_error_message = Column(
        String,
        nullable=True,
        comment="Последняя ошибка при refresh session"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания account"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="Время последнего обновления"
    )

    # Relationships
    user = relationship("src.models.user.User", backref="telegram_accounts")

    def __repr__(self) -> str:
        return f"<TelegramAccount(id={self.id}, phone='{self.phone}', status={self.session_health_status})>"

    # Helper Methods

    def is_healthy(self) -> bool:
        """Проверить, является ли session здоровой.

        Returns:
            True если session статус HEALTHY, иначе False
        """
        return self.session_health_status == SessionHealthStatus.HEALTHY

    def needs_refresh(self) -> bool:
        """Проверить, требуется ли refresh session.

        Returns:
            True если session истекает скоро или уже истекла, иначе False
        """
        if not self.session_expires_at:
            return False

        now = datetime.utcnow()
        refresh_threshold = self.session_expires_at - timedelta(hours=self.refresh_before_expires_hours)

        return now >= refresh_threshold

    def is_expired(self) -> bool:
        """Проверить, истекла ли session.

        Returns:
            True если session уже истекла, иначе False
        """
        if not self.session_expires_at:
            return False

        return datetime.utcnow() >= self.session_expires_at

    def is_expiring_soon(self) -> bool:
        """Проверить, истекает ли session скоро.

        Returns:
            True если session истекает в течение refresh_before_expires_hours, иначе False
        """
        if not self.session_expires_at:
            return False

        now = datetime.utcnow()
        refresh_threshold = self.session_expires_at - timedelta(hours=self.refresh_before_expires_hours)

        return now >= refresh_threshold and now < self.session_expires_at

    def get_time_until_expiry(self) -> Optional[timedelta]:
        """Получить время до истечения session.

        Returns:
            timedelta до истечения session или None если session_expires_at не задан
        """
        if not self.session_expires_at:
            return None

        return self.session_expires_at - datetime.utcnow()

    def should_auto_refresh(self) -> bool:
        """Проверить, следует ли автоматически выполнить refresh.

        Returns:
            True если auto_refresh_enabled включен и session требует refresh, иначе False
        """
        return self.auto_refresh_enabled and self.needs_refresh()

class ChannelStatus(str, PyEnum):
    """Статусы channel."""
    STOPPED = "stopped"       # Channel остановлен
    RUNNING = "running"       # Channel активно транслирует
    ERROR = "error"           # Ошибка при трансляции


class Channel(Base):
    """ORM Model для Telegram channels.

    **Table**: channels
    **Purpose**: Конфигурация channels для трансляции из Telegram chats

    **Relationships**:
    - account: TelegramAccount (FK to telegram_accounts.id)

    **Configuration**:
    - ffmpeg_args: Кастомные аргументы для FFmpeg
    - video_quality: Качество видео (best, 720p, 480p, etc.)
    - stream_type: Тип трансляции (video, audio)
    - placeholder_image: Путь к кастомному placeholder изображению

    **Timestamps**:
    - created_at: Время создания channel
    - updated_at: Время последнего обновления
    """
    __tablename__ = "channels"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    account_id = Column(GUID(), ForeignKey("telegram_accounts.id"), nullable=False, index=True)

    # Core Fields
    chat_id = Column(BigInteger, nullable=False, comment="Telegram Chat ID (64-bit)")
    chat_username = Column(String, nullable=True, comment="Telegram chat username для peer resolution")
    name = Column(String, nullable=False, comment="Название channel")
    status = Column(
        SQLEnum(ChannelStatus, name="channel_status", create_type=True),
        default=ChannelStatus.STOPPED,
        comment="Текущий статус channel"
    )
    error_message = Column(String, nullable=True, comment="Последняя ошибка")

    # Configuration Fields
    ffmpeg_args = Column(String, nullable=True, comment="Кастомные аргументы для FFmpeg")
    video_quality = Column(String, default="best", comment="Качество видео")
    stream_type = Column(String, default="video", comment="Тип трансляции (video, audio)")
    placeholder_image = Column(String, nullable=True, comment="Путь к placeholder изображению")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания channel"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="Время последнего обновления"
    )

    # Relationships
    account = relationship("TelegramAccount", backref="channels")

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, name='{self.name}', status={self.status}, chat_id={self.chat_id})>"
