"""
Stream Entity - Aggregate Root для потока вещания (T021).

**Architecture Layer**: Domain
**Dependencies**: StreamId, ChatId, UserId, Title Value Objects
**Usage**: Stream management, broadcasting use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from typing import TYPE_CHECKING, Optional

from src.domain.errors import BusinessRuleViolationError
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.title import Title
from src.domain.value_objects.user_id import UserId
from src.shared.kernel.entity import Entity

if TYPE_CHECKING:
    from src.domain.entities.playlist import Playlist


class StreamStatus(str, Enum):
    """Состояние потока вещания."""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class Stream:
    """
    Поток вещания (Aggregate Root).

    **Invariants**:
    - Title валиден (проверяется Title VO)
    - current_track_index >= 0
    - Статус переходит только по разрешённым путям (IDLE → ACTIVE → PAUSED/STOPPED)

    **Lifecycle**:
    1. Создание через create() factory (IDLE status)
    2. start() → ACTIVE
    3. pause() → PAUSED
    4. resume() → ACTIVE
    5. stop() → STOPPED (terminal state)

    **Business Rules**:
    - BR-001: Нельзя запустить уже активный стрим
    - BR-002: Нельзя приостановить неактивный стрим
    - BR-003: Нельзя возобновить не приостановленный стрим
    - BR-004: Нельзя остановить IDLE/STOPPED стрим
    """

    id: StreamId  # Entity identity
    chat_id: ChatId
    owner_id: UserId
    title: Title  # Value Object для названия потока
    status: StreamStatus
    current_track_index: int
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    playlist: Optional["Playlist"] = None  # Опциональная ссылка на плейлист
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, Stream):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        stream_id: StreamId,
        chat_id: ChatId,
        owner_id: UserId,
        title: Title,
    ) -> "Stream":
        """
        Factory method для создания нового потока.

        Args:
            stream_id: Уникальный ID потока
            chat_id: Telegram chat ID для вещания
            owner_id: ID владельца потока
            title: Title VO для названия потока

        Returns:
            Stream entity в IDLE статусе.

        Note:
            Валидация title выполняется в Title VO при создании.
        """
        return Stream(
            id=stream_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=title,
            status=StreamStatus.IDLE,
            current_track_index=0,
            created_at=datetime.utcnow(),
        )

    def start(self) -> None:
        """
        Запускает вещание (IDLE/STOPPED → ACTIVE).

        **Business Rule BR-001**: Нельзя запустить уже активный стрим.

        Raises:
            BusinessRuleViolationError: Если стрим уже активен.
        """
        if self.status == StreamStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"Stream {self.id} is already active, cannot start again"
            )

        self.status = StreamStatus.ACTIVE
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        """
        Приостанавливает вещание (ACTIVE → PAUSED).

        **Business Rule BR-002**: Можно приостановить только активный стрим.

        Raises:
            BusinessRuleViolationError: Если стрим не активен.
        """
        if self.status != StreamStatus.ACTIVE:
            raise BusinessRuleViolationError(
                f"Stream {self.id} is not active (current: {self.status}), cannot pause"
            )

        self.status = StreamStatus.PAUSED

    def resume(self) -> None:
        """
        Возобновляет вещание (PAUSED → ACTIVE).

        **Business Rule BR-003**: Можно возобновить только приостановленный стрим.

        Raises:
            BusinessRuleViolationError: Если стрим не приостановлен.
        """
        if self.status != StreamStatus.PAUSED:
            raise BusinessRuleViolationError(
                f"Stream {self.id} is not paused (current: {self.status}), cannot resume"
            )

        self.status = StreamStatus.ACTIVE

    def stop(self) -> None:
        """
        Останавливает вещание (ACTIVE/PAUSED → STOPPED).

        **Business Rule BR-004**: Можно остановить только активный/приостановленный стрим.

        Raises:
            BusinessRuleViolationError: Если стрим не в активном/приостановленном состоянии.
        """
        if self.status not in [StreamStatus.ACTIVE, StreamStatus.PAUSED]:
            raise BusinessRuleViolationError(
                f"Stream {self.id} cannot be stopped from status {self.status}"
            )

        self.status = StreamStatus.STOPPED
        self.stopped_at = datetime.utcnow()

    def next_track(self) -> None:
        """
        Переключает на следующий трек (увеличивает current_track_index).

        **Note**: Валидация существования трека - ответственность Application layer.
        """
        self.current_track_index += 1

    def is_running(self) -> bool:
        """True если стрим активен или приостановлен."""
        return self.status in [StreamStatus.ACTIVE, StreamStatus.PAUSED]

    def collect_domain_events(self) -> list:
        """Собирает и очищает domain events для публикации."""
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
