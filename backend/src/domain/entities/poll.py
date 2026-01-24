"""
Poll Entity - интерактивный опрос для зрителей (T020).

**Architecture Layer**: Domain
**Dependencies**: PollId, ChatId, UserId Value Objects
**Usage**: Poll management, voting use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId


class PollStatus(str, Enum):
    """Состояние опроса."""
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class PollOption:
    """
    Вариант ответа в опросе.

    **Invariants**:
    - option_text не пустой
    - vote_count >= 0
    """

    id: str
    option_text: str
    vote_count: int = 0

    def __eq__(self, other: object) -> bool:
        """Options равны если имеют одинаковый ID."""
        if not isinstance(other, PollOption):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)


@dataclass
class Poll:
    """
    Интерактивный опрос для зрителей (Entity).

    **Invariants**:
    - question не пустой
    - Минимум 2 варианта ответа
    - Голосование только в ACTIVE статусе
    - Каждый пользователь может голосовать только один раз

    **Lifecycle**:
    1. Создание через create() factory (DRAFT status)
    2. publish() → ACTIVE
    3. vote() → добавляет голос
    4. close() → CLOSED (terminal state)

    **Business Rules**:
    - BR-001: Нельзя опубликовать опрос с менее чем 2 вариантами
    - BR-002: Нельзя голосовать в неактивном опросе
    - BR-003: Нельзя голосовать дважды в одном опросе
    - BR-004: Нельзя закрыть уже закрытый опрос
    """

    id: str
    stream_id: str
    chat_id: ChatId
    created_by: UserId
    question: str
    options: list[PollOption]
    status: PollStatus
    allow_multiple_votes: bool
    created_at: datetime
    published_at: datetime | None = None
    closed_at: datetime | None = None
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, Poll):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        poll_id: str,
        stream_id: str,
        chat_id: ChatId,
        created_by: UserId,
        question: str,
        options: list[PollOption],
        allow_multiple_votes: bool = False,
    ) -> "Poll":
        """
        Factory method для создания нового опроса.

        Args:
            poll_id: Уникальный ID опроса
            stream_id: ID потока, к которому привязан опрос
            chat_id: Telegram chat ID
            created_by: ID создателя опроса
            question: Текст вопроса
            options: Список вариантов ответа
            allow_multiple_votes: Разрешить голосовать за несколько вариантов

        Returns:
            Poll entity в DRAFT статусе.

        Raises:
            BusinessRuleViolationError: Если question пустой или options < 2
        """
        if not question or not question.strip():
            raise BusinessRuleViolationError("Poll question cannot be empty")

        if len(options) < 2:
            raise BusinessRuleViolationError(
                "Poll must have at least 2 options"
            )

        return Poll(
            id=poll_id,
            stream_id=stream_id,
            chat_id=chat_id,
            created_by=created_by,
            question=question,
            options=options,
            status=PollStatus.DRAFT,
            allow_multiple_votes=allow_multiple_votes,
            created_at=datetime.utcnow(),
        )

    def publish(self) -> None:
        """
        Публикует опрос (DRAFT → ACTIVE).

        **Business Rule BR-001**: Нельзя опубликовать опрос с менее чем 2 вариантами.

        Raises:
            BusinessRuleViolationError: Если опрос уже активен или закрыт.
        """
        if self.status != PollStatus.DRAFT:
            raise BusinessRuleViolationError(
                f"Poll {self.id} is not in DRAFT status (current: {self.status}), cannot publish"
            )

        self.status = PollStatus.ACTIVE
        self.published_at = datetime.utcnow()

    def vote(self, user_id: UserId, option_ids: list[str]) -> None:
        """
        Голосует в опросе.

        **Business Rule BR-002**: Можно голосовать только в активном опросе.
        **Business Rule BR-003**: Проверка повторного голосования выполняется в Application layer.

        Args:
            user_id: ID пользователя
            option_ids: Список ID выбранных вариантов

        Raises:
            BusinessRuleViolationError: Если опрос не активен или варианты не найдены.
        """
        if self.status != PollStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"Poll {self.id} is not active (current: {self.status}), cannot vote"
            )

        if not option_ids:
            raise BusinessRuleViolationError(
                "At least one option must be selected"
            )

        # Проверка на multiple votes
        if not self.allow_multiple_votes and len(option_ids) > 1:
            raise BusinessRuleViolationError(
                "Multiple votes are not allowed for this poll"
            )

        # Находим варианты и увеличиваем счетчики
        option_map = {opt.id: opt for opt in self.options}
        for option_id in option_ids:
            if option_id not in option_map:
                raise BusinessRuleViolationError(
                    f"Option {option_id} not found in poll"
                )
            option_map[option_id].vote_count += 1

    def close(self) -> None:
        """
        Закрывает опрос (ACTIVE → CLOSED).

        **Business Rule BR-004**: Нельзя закрыть уже закрытый опрос.

        Raises:
            BusinessRuleViolationError: Если опрос не активен.
        """
        if self.status != PollStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"Poll {self.id} is not active (current: {self.status}), cannot close"
            )

        self.status = PollStatus.CLOSED
        self.closed_at = datetime.utcnow()

    def get_results(self) -> dict[str, int]:
        """
        Возвращает результаты опроса.

        Returns:
            Словарь {option_id: vote_count}.
        """
        return {opt.id: opt.vote_count for opt in self.options}

    def total_votes(self) -> int:
        """
        Возвращает общее количество голосов.

        Returns:
            Общее количество голосов по всем вариантам.
        """
        return sum(opt.vote_count for opt in self.options)

    def is_active(self) -> bool:
        """True если опрос активен."""
        return self.status == PollStatus.ACTIVE

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
