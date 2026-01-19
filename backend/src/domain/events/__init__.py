"""
Domain Events для User Entity.

**Architecture Layer**: Domain
**Dependencies**: DomainEvent base class
**Usage**: Event-driven architecture, audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.domain.value_objects.user_id import UserId
from src.shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class UserCreatedEvent(DomainEvent):
    """Событие создания пользователя."""
    user_id: UserId
    email: str
    username: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class UserActivatedEvent(DomainEvent):
    """Событие активации пользователя."""
    user_id: UserId
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class UserDeactivatedEvent(DomainEvent):
    """Событие деактивации пользователя."""
    user_id: UserId
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
