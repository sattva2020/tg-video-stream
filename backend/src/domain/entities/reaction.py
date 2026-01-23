"""
Reaction Entity - эмодзи-реакция зрителя (T020).

**Architecture Layer**: Domain
**Dependencies**: ReactionId, ChatId, UserId Value Objects
**Usage**: Reaction tracking, overlay display use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId


class ReactionType(str, Enum):
    """Тип реакции (эмодзи)."""
    HEART = "❤️"
    THUMBS_UP = "👍"
    THUMBS_DOWN = "👎"
    FIRE = "🔥"
    LAUGH = "😂"
    CRY = "😢"
    SURPRISE = "😮"
    CLAP = "👏"
    ROCKET = "🚀"
    STAR = "⭐"


@dataclass
class Reaction:
    """
    Эмодзи-реакция зрителя на поток (Entity).

    **Invariants**:
    - reaction_type валиден (из enum ReactionType)
    - count >= 1

    **Lifecycle**:
    1. Создание через create() factory
    2. increment() → увеличивает count

    **Business Rules**:
    - BR-001: Нельзя создать реакцию с count < 1
    - BR-002: Реакции истекают через время очищаются инфраструктурой
    """

    id: str
    stream_id: str
    chat_id: ChatId
    user_id: UserId
    reaction_type: ReactionType
    count: int
    created_at: datetime
    expires_at: datetime | None = None
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, Reaction):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        reaction_id: str,
        stream_id: str,
        chat_id: ChatId,
        user_id: UserId,
        reaction_type: ReactionType,
        ttl_seconds: int = 60,
    ) -> "Reaction":
        """
        Factory method для создания новой реакции.

        Args:
            reaction_id: Уникальный ID реакции
            stream_id: ID потока
            chat_id: Telegram chat ID
            user_id: ID пользователя
            reaction_type: Тип реакции (эмодзи)
            ttl_seconds: Время жизни реакции в секундах (по умолчанию 60)

        Returns:
            Reaction entity.

        Note:
            Реакции с истекшим TTL очищаются инфраструктурным слоем.
        """
        from datetime import timedelta

        if ttl_seconds <= 0:
            raise BusinessRuleViolationError("TTL must be positive")

        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(seconds=ttl_seconds)

        return Reaction(
            id=reaction_id,
            stream_id=stream_id,
            chat_id=chat_id,
            user_id=user_id,
            reaction_type=reaction_type,
            count=1,
            created_at=created_at,
            expires_at=expires_at,
        )

    def increment(self) -> None:
        """
        Увеличивает счетчик реакции.

        **Note**: Используется для группировки одинаковых реакций.
        """
        self.count += 1

    def is_expired(self) -> bool:
        """
        Проверяет, истекло ли время жизни реакции.

        Returns:
            True если реакция истекла.
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def get_emoji(self) -> str:
        """
        Возвращает эмодзи реакции.

        Returns:
            Эмодзи как строку.
        """
        return self.reaction_type.value

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
