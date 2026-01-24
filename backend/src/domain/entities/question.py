"""
Question Entity - вопрос от зрителя в Q&A сессии (T020).

**Architecture Layer**: Domain
**Dependencies**: QuestionId, ChatId, UserId Value Objects
**Usage**: Q&A management, question voting use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId


class QuestionStatus(str, Enum):
    """Статус вопроса."""
    PENDING = "pending"
    APPROVED = "approved"
    ANSWERED = "answered"
    REJECTED = "rejected"


@dataclass
class Question:
    """
    Вопрос зрителя в Q&A сессии (Entity).

    **Invariants**:
    - question_text не пустой
    - vote_count >= 0
    - Статус переходит по разрешённым путям

    **Lifecycle**:
    1. Создание через create() factory (PENDING status)
    2. approve() → APPROVED
    3. upvote() → увеличивает vote_count
    4. mark_as_answered() → ANSWERED
    5. reject() → REJECTED (terminal state)

    **Business Rules**:
    - BR-001: Нельзя одобрить уже одобренный/отвеченный/отклоненный вопрос
    - BR-002: Нельзя голосовать за отклоненный вопрос
    - BR-003: Нельзя отметить как отвеченный не одобренный вопрос
    - BR-004: Нельзя отклонить уже отвеченный вопрос
    """

    id: str
    stream_id: str
    chat_id: ChatId
    user_id: UserId
    question_text: str
    status: QuestionStatus
    vote_count: int
    created_at: datetime
    approved_at: datetime | None = None
    answered_at: datetime | None = None
    rejected_at: datetime | None = None
    answer: str | None = None
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, Question):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        question_id: str,
        stream_id: str,
        chat_id: ChatId,
        user_id: UserId,
        question_text: str,
    ) -> "Question":
        """
        Factory method для создания нового вопроса.

        Args:
            question_id: Уникальный ID вопроса
            stream_id: ID потока
            chat_id: Telegram chat ID
            user_id: ID автора вопроса
            question_text: Текст вопроса

        Returns:
            Question entity в PENDING статусе.

        Raises:
            BusinessRuleViolationError: Если question_text пустой.
        """
        if not question_text or not question_text.strip():
            raise BusinessRuleViolationError("Question text cannot be empty")

        return Question(
            id=question_id,
            stream_id=stream_id,
            chat_id=chat_id,
            user_id=user_id,
            question_text=question_text,
            status=QuestionStatus.PENDING,
            vote_count=0,
            created_at=datetime.utcnow(),
        )

    def approve(self) -> None:
        """
        Одобряет вопрос (PENDING → APPROVED).

        **Business Rule BR-001**: Нельзя одобрить уже обработанный вопрос.

        Raises:
            BusinessRuleViolationError: Если вопрос не в ожидании.
        """
        if self.status != QuestionStatus.PENDING:
            raise BusinessRuleViolationError(
                f"Question {self.id} is not pending (current: {self.status}), cannot approve"
            )

        self.status = QuestionStatus.APPROVED
        self.approved_at = datetime.utcnow()

    def upvote(self) -> None:
        """
        Голосует за вопрос.

        **Business Rule BR-002**: Нельзя голосовать за отклоненный вопрос.

        Raises:
            BusinessRuleViolationError: Если вопрос отклонен.
        """
        if self.status == QuestionStatus.REJECTED:
            raise BusinessRuleViolationError(
                f"Question {self.id} is rejected, cannot upvote"
            )

        self.vote_count += 1

    def downvote(self) -> None:
        """
        Забирает голос у вопроса.

        **Business Rule**: vote_count не может быть отрицательным.

        Raises:
            BusinessRuleViolationError: Если vote_count уже 0.
        """
        if self.vote_count <= 0:
            raise BusinessRuleViolationError(
                f"Question {self.id} has no votes to downvote"
            )

        self.vote_count -= 1

    def mark_as_answered(self, answer: str) -> None:
        """
        Отмечает вопрос как отвеченный (APPROVED → ANSWERED).

        **Business Rule BR-003**: Можно ответить только на одобренный вопрос.

        Args:
            answer: Текст ответа

        Raises:
            BusinessRuleViolationError: Если вопрос не одобрен.
        """
        if self.status != QuestionStatus.APPROVED:
            raise BusinessRuleViolationError(
                f"Question {self.id} is not approved (current: {self.status}), cannot mark as answered"
            )

        if not answer or not answer.strip():
            raise BusinessRuleViolationError("Answer cannot be empty")

        self.status = QuestionStatus.ANSWERED
        self.answered_at = datetime.utcnow()
        self.answer = answer

    def reject(self) -> None:
        """
        Отклоняет вопрос (PENDING/APPROVED → REJECTED).

        **Business Rule BR-004**: Нельзя отклонить уже отвеченный вопрос.

        Raises:
            BusinessRuleViolationError: Если вопрос уже отвечен.
        """
        if self.status == QuestionStatus.ANSWERED:
            raise BusinessRuleViolationError(
                f"Question {self.id} is already answered, cannot reject"
            )

        if self.status == QuestionStatus.REJECTED:
            raise BusinessRuleViolationError(
                f"Question {self.id} is already rejected"
            )

        self.status = QuestionStatus.REJECTED
        self.rejected_at = datetime.utcnow()

    def is_approved(self) -> bool:
        """True если вопрос одобрен."""
        return self.status == QuestionStatus.APPROVED

    def is_answered(self) -> bool:
        """True если вопрос отвечен."""
        return self.status == QuestionStatus.ANSWERED

    def is_rejected(self) -> bool:
        """True если вопрос отклонен."""
        return self.status == QuestionStatus.REJECTED

    def can_be_voted(self) -> bool:
        """True если за вопрос можно голосовать."""
        return self.status not in [QuestionStatus.REJECTED]

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
