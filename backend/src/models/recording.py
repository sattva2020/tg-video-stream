"""Recording ORM Model.

SQLAlchemy model для персистентности Recording Entity (архивы записей live streams).
Создан в рамках Feature 019 (Real-Time Live Streaming Capabilities).

**Purpose**: Хранение метаданных о записях live streams для последующего воспроизведения
**Layer**: Infrastructure (persistence)
**Table**: recordings

**Design Decision**:
- Отдельная таблица для хранения метаданных записей
- Связь с LiveStream через FK (live_stream_id)
- Поддержка статусов обработки записи (recording, processing, ready, error)

**Schema Reference**: См. specs/019-real-time-live-streaming-capabilities/spec.md
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Text, Integer, func
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class RecordingStatus(str, PyEnum):
    """Статусы записи live stream."""
    RECORDING = "recording"       # Запись в процессе
    PROCESSING = "processing"     # Пост-обработка (транскодинг, сжатие)
    READY = "ready"              # Запись готова к воспроизведению
    ERROR = "error"              # Ошибка при записи или обработке
    DELETED = "deleted"          # Запись удалена


class RecordingFormat(str, PyEnum):
    """Форматы записи."""
    MP4 = "mp4"                  # H.264/AAC в MP4 контейнере
    WEBM = "webm"                # VP8/VP9/Opus в WebM контейнере
    MKV = "mkv"                  # Matroska контейнер
    HLS = "hls"                  # HLS плейлист с сегментами


class Recording(Base):
    """ORM Model для записей live streams.

    **Table**: recordings
    **Purpose**: Хранение метаданных о записях live streams

    **Relationships**:
    - live_stream: LiveStream (FK to live_streams.id, cascade delete)

    **Core Fields**:
    - file_path: Путь к файлу записи в файловой системе
    - file_url: URL для доступа к записи (для воспроизведения через API)
    - duration: Длительность записи в секундах
    - file_size: Размер файла в байтах

    **Status Tracking**:
    - status: Текущий статус записи (RECORDING, PROCESSING, READY, ERROR, DELETED)
    - started_at: Время начала записи
    - ended_at: Время окончания записи (NULL если запись активна)

    **Format & Quality**:
    - format: Формат записи (MP4, WEBM, MKV, HLS)
    - bitrate: Средний битрейт в kbps
    - resolution: Разрешение видео (напр. "1920x1080", NULL если только аудио)
    - video_codec: Видеокодек (напр. "h264", "vp9", NULL если только аудио)
    - audio_codec: Аудиокодек (напр. "aac", "opus")

    **Preview & Thumbnails**:
    - thumbnail_url: URL для превью изображения (первый кадр)
    - preview_url: URL для превью видео (короткий фрагмент)

    **Error Handling**:
    - error_message: Сообщение об ошибке если status=ERROR

    **Timestamps**:
    - created_at: Время создания записи в БД
    - updated_at: Время последнего обновления записи
    """
    __tablename__ = "recordings"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    live_stream_id = Column(
        GUID(),
        ForeignKey("live_streams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to live_streams table"
    )

    # File Information
    file_path = Column(
        String(1024),
        nullable=False,
        comment="Путь к файлу записи в файловой системе"
    )
    file_url = Column(
        String(1024),
        nullable=True,
        comment="URL для доступа к записи через API"
    )

    # Recording Metrics
    duration = Column(
        BigInteger,
        nullable=True,
        comment="Длительность записи в секундах (NULL если запись в процессе)"
    )
    file_size = Column(
        BigInteger,
        nullable=True,
        comment="Размер файла в байтах (NULL если запись в процессе)"
    )

    # Status
    status = Column(
        SQLEnum(RecordingStatus, name="recording_status", create_type=True),
        nullable=False,
        default=RecordingStatus.RECORDING,
        comment="Текущий статус записи"
    )

    # Timestamps
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время начала записи"
    )
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время окончания записи (NULL если запись активна)"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания записи в БД"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Время последнего обновления записи"
    )

    # Format & Quality
    format = Column(
        SQLEnum(RecordingFormat, name="recording_format", create_type=True),
        nullable=True,
        comment="Формат записи (MP4, WEBM, MKV, HLS)"
    )
    bitrate = Column(
        Integer,
        nullable=True,
        comment="Средний битрейт в kbps"
    )
    resolution = Column(
        String(20),
        nullable=True,
        comment="Разрешение видео (напр. '1920x1080', NULL если только аудио)"
    )
    video_codec = Column(
        String(50),
        nullable=True,
        comment="Видеокодек (напр. 'h264', 'vp9', NULL если только аудио)"
    )
    audio_codec = Column(
        String(50),
        nullable=True,
        comment="Аудиокодек (напр. 'aac', 'opus')"
    )

    # Preview & Thumbnails
    thumbnail_url = Column(
        String(1024),
        nullable=True,
        comment="URL для превью изображения (первый кадр)"
    )
    preview_url = Column(
        String(1024),
        nullable=True,
        comment="URL для превью видео (короткий фрагмент)"
    )

    # Error Handling
    error_message = Column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке если status=ERROR"
    )

    # Relationships
    live_stream = relationship(
        "src.models.live_stream.LiveStream",
        back_populates="recordings",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Recording(id={self.id}, live_stream_id={self.live_stream_id}, status={self.status}, duration={self.duration}s)>"

    def is_recording(self) -> bool:
        """Проверяет, идет ли запись в данный момент."""
        return self.status == RecordingStatus.RECORDING

    def is_ready(self) -> bool:
        """Проверяет, готова ли запись к воспроизведению."""
        return self.status == RecordingStatus.READY

    def is_processing(self) -> bool:
        """Проверяет, обрабатывается ли запись."""
        return self.status == RecordingStatus.PROCESSING

    def is_failed(self) -> bool:
        """Проверяет, завершилась ли запись с ошибкой."""
        return self.status == RecordingStatus.ERROR

    def is_deleted(self) -> bool:
        """Проверяет, удалена ли запись."""
        return self.status == RecordingStatus.DELETED

    def mark_as_processing(self) -> None:
        """Помечает запись как 'в процессе обработки'."""
        self.status = RecordingStatus.PROCESSING

    def mark_as_ready(self, file_url: str, duration: int, file_size: int) -> None:
        """Помечает запись как готовую.

        Args:
            file_url: URL для доступа к записи
            duration: Длительность в секундах
            file_size: Размер файла в байтах
        """
        self.status = RecordingStatus.READY
        self.file_url = file_url
        self.duration = duration
        self.file_size = file_size
        self.ended_at = datetime.utcnow()

    def mark_as_failed(self, error_message: str) -> None:
        """Помечает запись как завершившуюся с ошибкой.

        Args:
            error_message: Описание ошибки
        """
        self.status = RecordingStatus.ERROR
        self.error_message = error_message
        self.ended_at = datetime.utcnow()

    def mark_as_deleted(self) -> None:
        """Помечает запись как удаленную."""
        self.status = RecordingStatus.DELETED

    def get_duration_minutes(self) -> float:
        """Возвращает длительность записи в минутах."""
        if self.duration is None:
            return 0.0
        return round(self.duration / 60, 2)

    def get_file_size_mb(self) -> float:
        """Возвращает размер файла в мегабайтах."""
        if self.file_size is None:
            return 0.0
        return round(self.file_size / (1024 * 1024), 2)
