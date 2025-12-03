"""
Admin Audit Log Model

Модель для логирования всех административных действий.

Хранит:
- Кто совершил действие (user_id)
- Что было сделано (action)
- Над каким ресурсом (resource_type, resource_id)
- Когда (timestamp)
- Дополнительные детали (details)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base


class AdminAuditLog(Base):
    """
    Лог административных действий.
    
    Записывает все действия в административной панели для аудита.
    
    Attributes:
        id: Уникальный идентификатор записи
        user_id: ID администратора, совершившего действие
        action: Тип действия (login, logout, create, update, delete, view)
        resource_type: Тип ресурса (user, channel, track, etc.)
        resource_id: ID ресурса
        details: Дополнительные детали в свободной форме
        timestamp: Время действия
    """
    
    __tablename__ = "admin_audit_logs"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Уникальный идентификатор записи лога"
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID администратора"
    )
    
    action = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Тип действия: login, logout, create, update, delete, view, export"
    )
    
    resource_type = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Тип ресурса: user, channel, track, settings, etc."
    )
    
    resource_id = Column(
        String(255),
        nullable=True,
        doc="ID ресурса (может быть UUID или другой идентификатор)"
    )
    
    details = Column(
        Text,
        nullable=True,
        doc="Дополнительные детали действия в свободной форме"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        doc="IP адрес администратора (IPv4 или IPv6)"
    )
    
    user_agent = Column(
        String(500),
        nullable=True,
        doc="User-Agent браузера"
    )
    
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="Время совершения действия"
    )
    
    # Relationship
    user = relationship(
        "User",
        back_populates="audit_logs",
        lazy="selectin"
    )
    
    # Indexes для частых запросов
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_timestamp_desc", timestamp.desc()),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AdminAuditLog(id={self.id}, "
            f"user_id={self.user_id}, "
            f"action='{self.action}', "
            f"resource_type='{self.resource_type}', "
            f"timestamp={self.timestamp})>"
        )
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для API."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# Константы для типов действий
class AuditAction:
    """Константы для типов действий."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    BAN = "ban"
    UNBAN = "unban"


# Константы для типов ресурсов
class ResourceType:
    """Константы для типов ресурсов."""
    USER = "user"
    CHANNEL = "channel"
    TRACK = "track"
    PLAYLIST = "playlist"
    SETTINGS = "settings"
    QUEUE = "queue"
    STREAM = "stream"
    ROLE = "role"
    PERMISSION = "permission"
