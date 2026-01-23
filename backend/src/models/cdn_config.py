"""
CDN Configuration Model (Feature 024).

SQLAlchemy model for storing CDN provider configurations.
"""

import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, func, Integer
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class CDNProviderType(str, PyEnum):
    """Типы CDN провайдеров."""
    CLOUDFLARE = "cloudflare"
    CLOUDFRONT = "cloudfront"
    FASTLY = "fastly"


class CDNConfig(Base):
    """
    Модель конфигурации CDN провайдера.

    Хранит настройки для подключения к различным CDN провайдерам:
    - API токены и ключи
    - Идентификаторы ресурсов (zones, distributions, services)
    - Статус enabled/disabled
    """
    __tablename__ = "cdn_configs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Provider info
    provider = Column(String, nullable=False, index=True)  # cloudflare, cloudfront, fastly
    name = Column(String(255), nullable=False)  # Пользовательское имя конфигурации

    # Authentication
    api_token = Column(String, nullable=False)  # Зашифрован или из secrets manager
    account_id = Column(String, nullable=True)  # Cloudflare account ID

    # Resource identifiers
    zone_id = Column(String, nullable=True)  # Cloudflare zone ID
    distribution_id = Column(String, nullable=True)  # CloudFront distribution ID
    service_id = Column(String, nullable=True)  # Fastly service ID

    # Configuration
    enabled = Column(Boolean, nullable=False, server_default="true", default=True)
    priority = Column(Integer, nullable=False, server_default="0", default=0)  # Для failover порядка

    # Metadata
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_status = Column(String, nullable=True)  # healthy, degraded, unhealthy
    last_error = Column(Text, nullable=True)  # Последняя ошибка

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CDNConfig(id={self.id}, provider={self.provider}, name={self.name}, enabled={self.enabled})>"

    def is_cloudflare(self) -> bool:
        """Проверяет, является ли провайдер Cloudflare."""
        return self.provider == CDNProviderType.CLOUDFLARE.value

    def is_cloudfront(self) -> bool:
        """Проверяет, является ли провайдер AWS CloudFront."""
        return self.provider == CDNProviderType.CLOUDFRONT.value

    def is_fastly(self) -> bool:
        """Проверяет, является ли провайдер Fastly."""
        return self.provider == CDNProviderType.FASTLY.value

    def get_identifier(self) -> str | None:
        """
        Получить основной идентификатор ресурса CDN.

        Returns:
            zone_id для Cloudflare, distribution_id для CloudFront,
            service_id для Fastly
        """
        if self.is_cloudflare():
            return self.zone_id
        if self.is_cloudfront():
            return self.distribution_id
        if self.is_fastly():
            return self.service_id
        return None

    def is_healthy(self) -> bool:
        """Проверяет, здорова ли конфигурация CDN."""
        return self.health_status == "healthy" and self.enabled

    def update_health_status(
        self,
        status: str,
        error: str | None = None
    ) -> None:
        """
        Обновить статус здоровья CDN.

        Args:
            status: Новый статус (healthy, degraded, unhealthy)
            error: Текст ошибки если есть
        """
        self.health_status = status
        self.last_health_check = datetime.now(timezone.utc)
        if error:
            self.last_error = error

    def mark_as_unhealthy(self, error: str) -> None:
        """Пометить конфигурацию как нездоровую."""
        self.update_health_status("unhealthy", error)

    def mark_as_healthy(self) -> None:
        """Пометить конфигурацию как здоровую."""
        self.update_health_status("healthy", None)
        self.last_error = None

    def mark_as_degraded(self, error: str | None = None) -> None:
        """Пометить конфигурацию как деградировавшую."""
        self.update_health_status("degraded", error)

    @property
    def display_name(self) -> str:
        """Отображаемое имя конфигурации."""
        if self.name:
            return f"{self.name} ({self.provider})"
        return f"{self.provider} - {self.get_identifier() or 'Unknown'}"

    def to_dict(self, include_secrets: bool = False) -> dict:
        """
        Конвертировать модель в словарь.

        Args:
            include_secrets: Включать ли секреты (api_token)

        Returns:
            dict с данными конфигурации
        """
        data = {
            "id": str(self.id),
            "provider": self.provider,
            "name": self.name,
            "zone_id": self.zone_id,
            "distribution_id": self.distribution_id,
            "service_id": self.service_id,
            "account_id": self.account_id,
            "enabled": self.enabled,
            "priority": self.priority,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_secrets:
            data["api_token"] = self.api_token
        else:
            # Скрываем большую часть токена для безопасности
            if self.api_token:
                data["api_token"] = f"{self.api_token[:8]}...{self.api_token[-4:]}"

        return data
