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


class StreamType(str, Enum):
    """Тип потока вещания."""
    SCHEDULED = "scheduled"  # Плановый стрим из плейлиста
    LIVE = "live"  # Прямой эфир


class IngestionType(str, Enum):
    """Тип входящего потока для живого вещания."""
    RTMP = "rtmp"  # RTMP ingestion (OBS, FFmpeg)
    SRT = "srt"  # SRT ingestion
    WEBRTC_CAMERA = "webrtc_camera"  # WebRTC from browser camera
    WEBRTC_SCREEN = "webrtc_screen"  # WebRTC from browser screen share


@dataclass
class Stream:
    """
    Поток вещания (Aggregate Root).

    **Invariants**:
    - Title валиден (проверяется Title VO)
    - current_track_index >= 0
    - Статус переходит только по разрешённым путям (IDLE → ACTIVE → PAUSED/STOPPED)

    **Lifecycle**:
    1. Создание через create() factory (IDLE status, SCHEDULED type)
    2. create_live() для живых трансляций
    3. start() → ACTIVE
    4. pause() → PAUSED
    5. resume() → ACTIVE
    6. stop() → STOPPED (terminal state)

    **Business Rules**:
    - BR-001: Нельзя запустить уже активный стрим
    - BR-002: Нельзя приостановить неактивный стрим
    - BR-003: Нельзя возобновить не приостановленный стрим
    - BR-004: Нельзя остановить IDLE/STOPPED стрим
    - BR-005: Нельзя изменить тип потока во время трансляции
    - BR-006: Количество гостей не должно превышать max_guests
    - BR-007: Латность не должна превышать заданный порог
    """

    id: StreamId  # Entity identity
    chat_id: ChatId
    owner_id: UserId
    title: Title  # Value Object для названия потока
    status: StreamStatus
    stream_type: StreamType = StreamType.SCHEDULED  # Тип потока
    current_track_index: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    playlist: Optional["Playlist"] = None  # Опциональная ссылка на плейлист

    # Live streaming fields
    ingestion_type: Optional[IngestionType] = None  # Тип входящего потока для LIVE
    ingestion_url: Optional[str] = None  # URL для RTMP/SRT ingestion
    viewer_count: int = 0  # Текущее количество зрителей
    latency_ms: Optional[int] = None  # Текущая задержка в миллисекундах
    preview_url: Optional[str] = None  # URL для превью потока
    recording_enabled: bool = False  # Автоматическая запись потока
    recording_id: Optional[str] = None  # ID записи если идет запись
    max_guests: int = 5  # Максимальное количество со-ведущих
    guest_sessions: list[str] = field(default_factory=list)  # ID активных гостевых сессий

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
        Factory method для создания нового планового потока.

        Args:
            stream_id: Уникальный ID потока
            chat_id: Telegram chat ID для вещания
            owner_id: ID владельца потока
            title: Title VO для названия потока

        Returns:
            Stream entity в IDLE статусе с типом SCHEDULED.

        Note:
            Валидация title выполняется в Title VO при создании.
        """
        return Stream(
            id=stream_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=title,
            status=StreamStatus.IDLE,
            stream_type=StreamType.SCHEDULED,
            current_track_index=0,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def create_live(
        stream_id: StreamId,
        chat_id: ChatId,
        owner_id: UserId,
        title: Title,
        ingestion_type: IngestionType,
        ingestion_url: Optional[str] = None,
        max_guests: int = 5,
        recording_enabled: bool = True,
    ) -> "Stream":
        """
        Factory method для создания живого потока.

        Args:
            stream_id: Уникальный ID потока
            chat_id: Telegram chat ID для вещания
            owner_id: ID владельца потока
            title: Title VO для названия потока
            ingestion_type: Тип входящего потока (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)
            ingestion_url: URL для RTMP/SRT ingestion (опционально для WebRTC)
            max_guests: Максимальное количество со-ведущих (по умолчанию 5)
            recording_enabled: Включить автоматическую запись (по умолчанию True)

        Returns:
            Stream entity в IDLE статусе с типом LIVE.

        Raises:
            ValueError: Если ingestion_type требует ingestion_url, но он не предоставлен.

        Note:
            Валидация title выполняется в Title VO при создании.
        """
        # Валидация: RTMP и SRT требуют ingestion_url
        if ingestion_type in [IngestionType.RTMP, IngestionType.SRT] and not ingestion_url:
            raise ValueError(
                f"ingestion_url is required for {ingestion_type.value} streams"
            )

        return Stream(
            id=stream_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=title,
            status=StreamStatus.IDLE,
            stream_type=StreamType.LIVE,
            ingestion_type=ingestion_type,
            ingestion_url=ingestion_url,
            max_guests=max_guests,
            recording_enabled=recording_enabled,
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

        # Останавливаем запись если была активна
        if self.recording_id:
            self.stop_recording()

    def switch_to_live(
        self,
        ingestion_type: IngestionType,
        ingestion_url: Optional[str] = None,
    ) -> None:
        """
        Переключает поток на живой режим.

        **Business Rule BR-005**: Нельзя изменить тип потока во время трансляции.

        Args:
            ingestion_type: Тип входящего потока
            ingestion_url: URL для RTMP/SRT ingestion

        Raises:
            BusinessRuleViolationError: Если поток активен
            ValueError: Если ingestion_type требует ingestion_url
        """
        if self.is_running():
            raise BusinessRuleViolationError(
                f"Stream {self.id} is running, cannot switch type to LIVE"
            )

        if ingestion_type in [IngestionType.RTMP, IngestionType.SRT] and not ingestion_url:
            raise ValueError(
                f"ingestion_url is required for {ingestion_type.value} streams"
            )

        self.stream_type = StreamType.LIVE
        self.ingestion_type = ingestion_type
        self.ingestion_url = ingestion_url

    def add_guest(self, guest_session_id: str) -> None:
        """
        Добавляет гостя в живой поток.

        **Business Rule BR-006**: Количество гостей не должно превышать max_guests.

        Args:
            guest_session_id: Уникальный ID гостевой сессии

        Raises:
            BusinessRuleViolationError: Если превышен лимит гостей
            ValueError: Если гость уже добавлен
        """
        if not self.can_add_guest():
            raise BusinessRuleViolationError(
                f"Stream {self.id} has reached maximum guest limit ({self.max_guests})"
            )

        if guest_session_id in self.guest_sessions:
            raise ValueError(
                f"Guest {guest_session_id} is already in the stream"
            )

        self.guest_sessions.append(guest_session_id)

    def remove_guest(self, guest_session_id: str) -> None:
        """
        Удаляет гостя из живого потока.

        Args:
            guest_session_id: ID гостевой сессии для удаления

        Raises:
            ValueError: Если гость не найден в списке
        """
        if guest_session_id not in self.guest_sessions:
            raise ValueError(
                f"Guest {guest_session_id} not found in stream"
            )

        self.guest_sessions.remove(guest_session_id)

    def can_add_guest(self) -> bool:
        """
        Проверяет, можно ли добавить еще одного гостя.

        Returns:
            True если лимит гостей не превышен
        """
        return len(self.guest_sessions) < self.max_guests

    def update_latency(self, latency_ms: int) -> None:
        """
        Обновляет текущую задержку потока.

        Args:
            latency_ms: Задержка в миллисекундах
        """
        self.latency_ms = latency_ms

    def is_over_latency_threshold(self, threshold_ms: int = 5000) -> bool:
        """
        Проверяет, превышает ли задержка пороговое значение.

        **Business Rule BR-007**: Латность не должна превышать заданный порог.

        Args:
            threshold_ms: Пороговое значение в миллисекундах (по умолчанию 5000ms = 5s)

        Returns:
            True если задержка превышает порог
        """
        if self.latency_ms is None:
            return False
        return self.latency_ms > threshold_ms

    def update_viewer_count(self, count: int) -> None:
        """
        Обновляет количество зрителей.

        Args:
            count: Новое количество зрителей
        """
        self.viewer_count = max(0, count)

    def start_recording(self, recording_id: str) -> None:
        """
        Начинает запись потока.

        Args:
            recording_id: Уникальный ID записи

        Raises:
            BusinessRuleViolationError: Если запись уже активна
        """
        if self.recording_id:
            raise BusinessRuleViolationError(
                f"Stream {self.id} is already being recorded (recording_id: {self.recording_id})"
            )

        self.recording_id = recording_id

    def stop_recording(self) -> None:
        """
        Останавливает запись потока.

        Note:
            Если запись не была активна, метод ничего не делает.
        """
        self.recording_id = None

    def is_live(self) -> bool:
        """
        Проверяет, является ли поток живым.

        Returns:
            True если тип потока LIVE
        """
        return self.stream_type == StreamType.LIVE

    def is_recording(self) -> bool:
        """
        Проверяет, идет ли запись потока.

        Returns:
            True если активна запись
        """
        return self.recording_id is not None

    def has_guests(self) -> bool:
        """
        Проверяет, есть ли активные гости.

        Returns:
            True если есть хотя бы один гость
        """
        return len(self.guest_sessions) > 0

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
