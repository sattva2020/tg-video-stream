"""
CTA Entity - призыв к действию для зрителей (T020).

**Architecture Layer**: Domain
**Dependencies**: CTAId, ChatId, UserId Value Objects
**Usage**: CTA management, interactive prompts use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId


class CTAStatus(str, Enum):
    """Статус призыва к действию."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


class CTAAction(str, Enum):
    """Тип действия."""
    SUBSCRIBE = "subscribe"
    FOLLOW = "follow"
    VISIT_LINK = "visit_link"
    DONATE = "donate"
    JOIN_GROUP = "join_group"
    CUSTOM = "custom"


@dataclass
class CTA:
    """
    Призыв к действию для зрителей (Entity).

    **Invariants**:
    - title не пустой
    - action валиден (из enum CTAAction)
    - Статус переходит по разрешённым путям

    **Lifecycle**:
    1. Создание через create() factory (DRAFT status)
    2. activate() → ACTIVE
    3. pause() → PAUSED
    4. resume() → ACTIVE
    5. expire() → EXPIRED (terminal state)

    **Business Rules**:
    - BR-001: Нельзя активировать CTA с пустым title
    - BR-002: Нельзя приостановить неактивный CTA
    - BR-003: Нельзя возобновить не приостановленный CTA
    - BR-004: Нельзя истечь CTA, который не активен или приостановлен
    - BR-005: Для VISIT_LINK action должен быть указан link
    """

    id: str
    stream_id: str
    chat_id: ChatId
    created_by: UserId
    title: str
    action: CTAAction
    status: CTAStatus
    description: str | None
    link: str | None  # URL для VISIT_LINK
    button_text: str | None  # Текст на кнопке
    display_duration: int | None  # Длительность отображения в секундах (None = постоянно)
    created_at: datetime
    activated_at: datetime | None = None
    paused_at: datetime | None = None
    expired_at: datetime | None = None
    click_count: int = 0
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, CTA):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        cta_id: str,
        stream_id: str,
        chat_id: ChatId,
        created_by: UserId,
        title: str,
        action: CTAAction,
        description: str | None = None,
        link: str | None = None,
        button_text: str | None = None,
        display_duration: int | None = None,
    ) -> "CTA":
        """
        Factory method для создания нового CTA.

        Args:
            cta_id: Уникальный ID CTA
            stream_id: ID потока
            chat_id: Telegram chat ID
            created_by: ID создателя
            title: Заголовок призыва
            action: Тип действия
            description: Описание
            link: URL (обязателен для VISIT_LINK)
            button_text: Текст на кнопке
            display_duration: Длительность отображения (None = постоянно)

        Returns:
            CTA entity в DRAFT статусе.

        Raises:
            BusinessRuleViolationError: Если title пустой или VISIT_LINK без URL.
        """
        if not title or not title.strip():
            raise BusinessRuleViolationError("CTA title cannot be empty")

        if action == CTAAction.VISIT_LINK and not link:
            raise BusinessRuleViolationError(
                "Link is required for VISIT_LINK action"
            )

        if display_duration is not None and display_duration <= 0:
            raise BusinessRuleViolationError(
                "Display duration must be positive"
            )

        return CTA(
            id=cta_id,
            stream_id=stream_id,
            chat_id=chat_id,
            created_by=created_by,
            title=title,
            action=action,
            status=CTAStatus.DRAFT,
            description=description,
            link=link,
            button_text=button_text,
            display_duration=display_duration,
            created_at=datetime.utcnow(),
        )

    def activate(self) -> None:
        """
        Активирует CTA (DRAFT/PAUSED → ACTIVE).

        **Business Rule**: Нельзя активировать уже активный или истекший CTA.

        Raises:
            BusinessRuleViolationError: Если CTA уже активен или истек.
        """
        if self.status == CTAStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"CTA {self.id} is already active"
            )

        if self.status == CTAStatus.EXPIRED:
            raise BusinessRuleViolationError(
                f"CTA {self.id} is expired, cannot activate"
            )

        self.status = CTAStatus.ACTIVE
        self.activated_at = datetime.utcnow()

    def pause(self) -> None:
        """
        Приостанавливает CTA (ACTIVE → PAUSED).

        **Business Rule BR-002**: Можно приостановить только активный CTA.

        Raises:
            BusinessRuleViolationError: Если CTA не активен.
        """
        if self.status != CTAStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"CTA {self.id} is not active (current: {self.status}), cannot pause"
            )

        self.status = CTAStatus.PAUSED
        self.paused_at = datetime.utcnow()

    def resume(self) -> None:
        """
        Возобновляет CTA (PAUSED → ACTIVE).

        **Business Rule BR-003**: Можно возобновить только приостановленный CTA.

        Raises:
            BusinessRuleViolationError: Если CTA не приостановлен.
        """
        if self.status != CTAStatus.PAUSED:
            raise BusinessRuleViolationError(
                f"CTA {self.id} is not paused (current: {self.status}), cannot resume"
            )

        self.status = CTAStatus.ACTIVE

    def expire(self) -> None:
        """
        Истекает CTA (ACTIVE/PAUSED → EXPIRED).

        **Business Rule BR-004**: Можно истечь только активный или приостановленный CTA.

        Raises:
            BusinessRuleViolationError: Если CTA не активен и не приостановлен.
        """
        if self.status not in [CTAStatus.ACTIVE, CTAStatus.PAUSED]:
            raise BusinessRuleViolationError(
                f"CTA {self.id} cannot be expired from status {self.status}"
            )

        self.status = CTAStatus.EXPIRED
        self.expired_at = datetime.utcnow()

    def register_click(self) -> None:
        """
        Регистрирует клик по CTA.

        Note:
            Можно кликать только на активный CTA (проверка в Application layer).
        """
        self.click_count += 1

    def is_active(self) -> bool:
        """True если CTA активен."""
        return self.status == CTAStatus.ACTIVE

    def is_expired(self) -> bool:
        """True если CTA истек."""
        return self.status == CTAStatus.EXPIRED

    def should_display(self) -> bool:
        """
        Определяет, должен ли CTA отображаться.

        Returns:
            True если CTA активен и display_duration еще не истек.
        """
        if not self.is_active():
            return False

        if self.display_duration is None:
            return True  # Отображать постоянно

        if self.activated_at is None:
            return False

        from datetime import timedelta
        expiry_time = self.activated_at + timedelta(seconds=self.display_duration)
        return datetime.utcnow() < expiry_time

    def get_action_display_name(self) -> str:
        """
        Возвращает отображаемое название действия.

        Returns:
            Название действия для отображения.
        """
        display_names = {
            CTAAction.SUBSCRIBE: "Subscribe",
            CTAAction.FOLLOW: "Follow",
            CTAAction.VISIT_LINK: "Visit Link",
            CTAAction.DONATE: "Donate",
            CTAAction.JOIN_GROUP: "Join Group",
            CTAAction.CUSTOM: "Action",
        }
        return display_names.get(self.action, "Action")

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
