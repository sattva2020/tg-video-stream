"""
Mobile Device model
Feature: 017-native-mobile-applications

Модель для хранения зарегистрированных мобильных устройств пользователей
и их push токенов для отправки уведомлений.
"""
import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class MobilePlatform(str, PyEnum):
    """Платформы мобильных устройств."""
    IOS = "ios"
    ANDROID = "android"


class DeviceStatus(str, PyEnum):
    """Статусы мобильных устройств."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class MobileDevice(Base):
    """Модель мобильного устройства пользователя."""

    __tablename__ = "mobile_devices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign key to user
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Device identification
    device_id = Column(String(255), unique=True, index=True, nullable=False)  # Уникальный ID устройства
    platform = Column(String(50), nullable=False)  # ios или android
    push_token = Column(String(500), nullable=False, index=True)  # Push токен для уведомлений

    # Device metadata
    device_name = Column(String(255), nullable=True)  # Название устройства (например, "iPhone 14 Pro")
    app_version = Column(String(50), nullable=True)  # Версия мобильного приложения
    os_version = Column(String(50), nullable=True)  # Версия операционной системы

    # Status and tracking
    status = Column(String(50), nullable=False, server_default="active", default="active")
    last_seen_at = Column(DateTime(timezone=True), nullable=True)  # Последняя активность устройства

    # Timestamps
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship(
        "User",
        back_populates="mobile_devices"
    )

    def __repr__(self):
        return f"<MobileDevice(id='{self.id}', device_id='{self.device_id}', platform='{self.platform}')>"

    def update_last_seen(self) -> None:
        """Обновить время последней активности устройства."""
        self.last_seen_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Проверяет, активно ли устройство."""
        return self.status == DeviceStatus.ACTIVE.value

    def revoke(self) -> None:
        """Отзывает устройство (отключает push уведомления)."""
        self.status = DeviceStatus.REVOKED.value

    def activate(self) -> None:
        """Активирует устройство."""
        self.status = DeviceStatus.ACTIVE.value
        self.update_last_seen()

    @property
    def platform_display(self) -> str:
        """Возвращает читаемое название платформы."""
        if self.platform == MobilePlatform.IOS.value:
            return "iOS"
        elif self.platform == MobilePlatform.ANDROID.value:
            return "Android"
        return self.platform
