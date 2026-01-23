"""
Shoutout Entity - упоминание/приветствие зрителя (T020).

**Architecture Layer**: Domain
**Dependencies**: ShoutoutId, ChatId, UserId Value Objects
**Usage**: Shoutout management, overlay display use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId


class ShoutoutType(str, Enum):
    """Тип приветствия."""
    NEW_FOLLOWER = "new_follower"
    NEW_SUBSCRIBER = "new_subscriber"
    DONATION = "donation"
    RAID = "raid"
    CUSTOM = "custom"


@dataclass
class Shoutout:
    """
    Приветствие/упоминание зрителя на стриме (Entity).

    **Invariants**:
    - username не пустой
    - message опционален, но если указан - не пустой
    - display_duration >= 0

    **Lifecycle**:
    1. Создание через create() factory
    2. mark_as_displayed() → устанавливает displayed_at
    3. dismiss() → скрывает с экрана

    **Business Rules**:
    - BR-001: Нельзя создать приветствие с пустым username
    - BR-002: display_duration должен быть положительным
    - BR-003: Нельзя отметить как отображенный повторно
    """

    id: str
    stream_id: str
    chat_id: ChatId
    user_id: UserId | None  # None если пользователь не зарегистрирован
    username: str
    shoutout_type: ShoutoutType
    message: str | None
    display_duration: int  # в секундах
    created_at: datetime
    displayed_at: datetime | None = None
    dismissed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)  # Доп. данные (сумма доната и т.д.)
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, Shoutout):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        shoutout_id: str,
        stream_id: str,
        chat_id: ChatId,
        username: str,
        shoutout_type: ShoutoutType,
        user_id: UserId | None = None,
        message: str | None = None,
        display_duration: int = 10,
        metadata: dict | None = None,
    ) -> "Shoutout":
        """
        Factory method для создания нового приветствия.

        Args:
            shoutout_id: Уникальный ID приветствия
            stream_id: ID потока
            chat_id: Telegram chat ID
            username: Имя пользователя
            shoutout_type: Тип приветствия
            user_id: ID пользователя (None если не зарегистрирован)
            message: Опциональное сообщение
            display_duration: Длительность отображения в секундах
            metadata: Дополнительные данные (сумма доната, количество зрителей рейда и т.д.)

        Returns:
            Shoutout entity.

        Raises:
            BusinessRuleViolationError: Если username пустой или display_duration отрицательный.
        """
        if not username or not username.strip():
            raise BusinessRuleViolationError("Username cannot be empty")

        if display_duration <= 0:
            raise BusinessRuleViolationError(
                "Display duration must be positive"
            )

        if message is not None and not message.strip():
            raise BusinessRuleViolationError(
                "Message cannot be empty string"
            )

        return Shoutout(
            id=shoutout_id,
            stream_id=stream_id,
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            shoutout_type=shoutout_type,
            message=message,
            display_duration=display_duration,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    def mark_as_displayed(self) -> None:
        """
        Отмечает приветствие как отображенное на экране.

        **Business Rule BR-003**: Нельзя отметить как отображенный повторно.

        Raises:
            BusinessRuleViolationError: Если уже отображалось.
        """
        if self.displayed_at is not None:
            raise BusinessRuleViolationError(
                f"Shoutout {self.id} is already displayed"
            )

        self.displayed_at = datetime.utcnow()

    def dismiss(self) -> None:
        """
        Убирает приветствие с экрана.

        Note:
            Можно вызвать даже если не было отображено (например, отмена).
        """
        self.dismissed_at = datetime.utcnow()

    def is_displayed(self) -> bool:
        """True если приветствие было отображено."""
        return self.displayed_at is not None

    def is_dismissed(self) -> bool:
        """True если приветствие убрано с экрана."""
        return self.dismissed_at is not None

    def should_be_visible(self) -> bool:
        """
        Определяет, должно ли приветствие быть видимым сейчас.

        Returns:
            True если отображалось и еще неDismissed.
        """
        if not self.is_displayed():
            return False
        if self.is_dismissed():
            return False
        return True

    def get_type_display_name(self) -> str:
        """
        Возвращает отображаемое название типа.

        Returns:
            Название типа для отображения.
        """
        display_names = {
            ShoutoutType.NEW_FOLLOWER: "New Follower",
            ShoutoutType.NEW_SUBSCRIBER: "New Subscriber",
            ShoutoutType.DONATION: "Donation",
            ShoutoutType.RAID: "Raid",
            ShoutoutType.CUSTOM: "Shoutout",
        }
        return display_names.get(self.shoutout_type, "Shoutout")

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
