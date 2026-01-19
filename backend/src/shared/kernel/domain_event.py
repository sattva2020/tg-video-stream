"""
Базовый класс DomainEvent для Event-Driven Architecture (FR-022).

**Architecture Layer**: Shared Kernel
**Dependencies**: datetime (stdlib)
**Usage**: Domain события для межслойной коммуникации.

Examples:
    >>> @dataclass(frozen=True)
    ... class UserCreatedEvent(DomainEvent):
    ...     user_id: UserId
    ...     email: str
    ...     event_id: str = field(default_factory=lambda: str(uuid4()))
    ...     occurred_at: datetime = field(default_factory=datetime.utcnow)
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


class DomainEvent(ABC):
    """
    Базовый класс для всех Domain Events.

    **Immutability**: События неизменяемы (факты из прошлого).
    **Naming**: Глаголы в прошедшем времени (UserCreated, StreamStarted).
    **Metadata**: event_id, occurred_at автоматически генерируются в дочерних классах.

    **Design Principles** (FR-022):
    1. **Immutability**: События - это факты, которые нельзя изменить
    2. **Past Tense Naming**: Событие уже произошло (Created, Updated, Deleted)
    3. **Rich Context**: Содержит всю информацию о произошедшем изменении
    4. **No Business Logic**: События только данные, логика в Event Handlers

    **Event Flow** (IEventBus pattern):
    1. Domain: Entity/Aggregate генерирует событие
    2. Application: Use Case публикует событие через IEventBus
    3. Infrastructure: EventBus доставляет event в handlers
    4. Frameworks: Event handlers запускают side-effects (notifications, logging)

    **Naming Convention**: {Aggregate}{Action}Event (UserCreatedEvent, StreamStartedEvent)

    **Implementation Pattern**:
        ```python
        from dataclasses import dataclass, field
        from datetime import datetime
        from src.shared.kernel.domain_event import DomainEvent
        from src.domain.value_objects.user_id import UserId

        @dataclass(frozen=True)
        class UserCreatedEvent(DomainEvent):
            user_id: UserId
            email: str
            event_id: str = field(default_factory=lambda: str(uuid4()))
            occurred_at: datetime = field(default_factory=datetime.utcnow)

        # Usage in Entity
        class User(Entity[UserId]):
            def __init__(self, id: UserId, email: Email):
                super().__init__(id)
                self.email = email
                self._events: list[DomainEvent] = [
                    UserCreatedEvent(user_id=id, email=email.value)
                ]

            def collect_events(self) -> list[DomainEvent]:
                events = self._events[:]
                self._events = []
                return events
        ```
    """

    # NOTE: Не используем @dataclass здесь, чтобы избежать проблем с полями defaults при наследовании
    # Дочерние классы должны быть @dataclass(frozen=True) и определять все поля, включая event_id и occurred_at
    
    event_id: str
    """Уникальный ID события (для idempotency checks в handlers)."""

    occurred_at: datetime
    """Timestamp когда событие произошло (UTC)."""

    def __eq__(self, other: Any) -> bool:
        """События равны по event_id (для deduplication)."""
        if not isinstance(other, DomainEvent):
            return False
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        """Hash based on event_id."""
        return hash(self.event_id)

    def __repr__(self) -> str:
        """Debug representation с event name и key attributes."""
        attrs = ", ".join(
            f"{k}={v!r}"
            for k, v in self.__dict__.items()
            if k not in {"event_id", "occurred_at"}
        )
        return f"{self.__class__.__name__}({attrs}, occurred_at={self.occurred_at!r})"


# Type hint для IEventBus port
DomainEventType = type[DomainEvent]
