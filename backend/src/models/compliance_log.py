"""
Compliance Log Model

Модель для логирования событий безопасности и соответствия требованиям.

Хранит:
- Тип события (event_type)
- Категория (category)
- Уровень серьезности (severity)
- Связанный пользователь/ресурс (user_id, resource_type, resource_id)
- Статус соответствия (compliance_status)
- Когда (timestamp)
- Дополнительные детали (details, metadata)
"""

import uuid
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.database import Base


class ComplianceLog(Base):
    """
    Лог событий безопасности и соответствия требованиям.

    Записывает события, связанные с безопасностью и Compliance,
    включая нарушения политик, проверки доступа и изменения настроек.

    Attributes:
        id: Уникальный идентификатор записи
        event_type: Тип события (auth_failure, policy_violation, data_access, etc.)
        category: Категория события (authentication, authorization, data_protection, etc.)
        severity: Уровень серьезности (critical, high, medium, low, info)
        compliance_status: Статус соответствия требованиям (compliant, non_compliant, pending)
        user_id: ID пользователя, связанного с событием
        resource_type: Тип ресурса (user, channel, track, settings, policy, etc.)
        resource_id: ID ресурса
        title: Краткое описание события
        description: Подробное описание события
        details: Дополнительные детали в свободной форме
        metadata: Дополнительные структурированные данные (JSON)
        ip_address: IP адрес (IPv4 или IPv6)
        user_agent: User-Agent браузера или клиента
        resolved_by: ID пользователя, разрешившего инцидент
        resolved_at: Время разрешения инцидента
        resolution_notes: Заметки о разрешении инцидента
        timestamp: Время события
    """

    __tablename__ = "compliance_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Уникальный идентификатор записи лога"
    )

    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Тип события: auth_failure, policy_violation, data_access, config_change, etc."
    )

    category = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Категория: authentication, authorization, data_protection, privacy, audit"
    )

    severity = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Уровень серьезности: critical, high, medium, low, info"
    )

    compliance_status = Column(
        String(30),
        nullable=False,
        index=True,
        doc="Статус соответствия: compliant, non_compliant, pending_review, resolved"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID пользователя, связанного с событием"
    )

    resource_type = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Тип ресурса: user, channel, track, settings, policy, role, etc."
    )

    resource_id = Column(
        String(255),
        nullable=True,
        doc="ID ресурса (может быть UUID или другой идентификатор)"
    )

    title = Column(
        String(255),
        nullable=False,
        doc="Краткое описание события"
    )

    description = Column(
        Text,
        nullable=True,
        doc="Подробное описание события"
    )

    details = Column(
        Text,
        nullable=True,
        doc="Дополнительные детали события в свободной форме"
    )

    metadata = Column(
        JSONB,
        nullable=True,
        doc="Дополнительные структурированные данные (JSON)"
    )

    ip_address = Column(
        String(45),
        nullable=True,
        doc="IP адрес (IPv4 или IPv6)"
    )

    user_agent = Column(
        String(500),
        nullable=True,
        doc="User-Agent браузера или клиента"
    )

    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID пользователя, разрешившего инцидент"
    )

    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время разрешения инцидента"
    )

    resolution_notes = Column(
        Text,
        nullable=True,
        doc="Заметки о разрешении инцидента"
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Время события"
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="compliance_logs",
        lazy="selectin"
    )

    resolver = relationship(
        "User",
        foreign_keys=[resolved_by],
        lazy="selectin"
    )

    # Indexes для частых запросов
    __table_args__ = (
        Index("ix_compliance_logs_event_type", "event_type"),
        Index("ix_compliance_logs_category", "category"),
        Index("ix_compliance_logs_severity", "severity"),
        Index("ix_compliance_logs_status", "compliance_status"),
        Index("ix_compliance_logs_user", "user_id", "timestamp"),
        Index("ix_compliance_logs_resource", "resource_type", "resource_id"),
        Index("ix_compliance_logs_timestamp_desc", timestamp.desc()),
        Index("ix_compliance_logs_unresolved", "compliance_status", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<ComplianceLog(id={self.id}, "
            f"event_type='{self.event_type}', "
            f"category='{self.category}', "
            f"severity='{self.severity}', "
            f"compliance_status='{self.compliance_status}', "
            f"timestamp={self.timestamp})>"
        )

    def to_dict(self) -> dict:
        """Преобразовать в словарь для API."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "category": self.category,
            "severity": self.severity,
            "compliance_status": self.compliance_status,
            "user_id": str(self.user_id) if self.user_id else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resolved_by": str(self.resolved_by) if self.resolved_by else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def is_resolved(self) -> bool:
        """Проверить, разрешен ли инцидент."""
        return self.compliance_status in [
            ComplianceStatus.RESOLVED,
            ComplianceStatus.COMPLIANT
        ]

    def is_critical(self) -> bool:
        """Проверить, является ли событие критическим."""
        return self.severity in [
            SeverityLevel.CRITICAL,
            SeverityLevel.HIGH
        ]


# Константы для типов событий
class ComplianceEventType:
    """Константы для типов событий."""
    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    POLICY_VIOLATION = "policy_violation"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    SECURITY_SCAN = "security_scan"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    MALWARE_DETECTED = "malware_detected"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    COMPLIANCE_CHECK = "compliance_check"
    GDPR_REQUEST = "gdpr_request"


# Константы для категорий
class ComplianceCategory:
    """Константы для категорий."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_PROTECTION = "data_protection"
    PRIVACY = "privacy"
    AUDIT = "audit"
    SECURITY = "security"
    NETWORK = "network"
    ACCESS_CONTROL = "access_control"
    ENCRYPTION = "encryption"
    MONITORING = "monitoring"


# Константы для уровней серьезности
class SeverityLevel:
    """Константы для уровней серьезности."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Константы для статуса соответствия
class ComplianceStatus:
    """Константы для статуса соответствия."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
