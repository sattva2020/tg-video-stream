"""LiveStream ORM Model.

SQLAlchemy model для персистентности LiveStream Entity (живые трансляции).
Создан в рамках Feature 019 (Real-Time Live Streaming Capabilities).

**Purpose**: Хранение состояния live streaming broadcasts в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется LiveStreamMapper для конвертации LiveStream Entity ↔ LiveStream ORM

**Design Decision**:
- NEW model (отдельная таблица от Stream ORM)
- Stream - для scheduled playlist streams
- LiveStream - для live broadcasts с RTMP/SRT/WebRTC ingestion

**Schema Reference**: См. specs/019-real-time-live-streaming-capabilities/spec.md
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Boolean, Integer, BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class IngestionType(str, PyEnum):
    """Тип входящего потока для живого вещания (синхронизирован с domain/entities/stream.py)."""
    RTMP = "rtmp"  # RTMP ingestion (OBS, FFmpeg)
    SRT = "srt"  # SRT ingestion
    WEBRTC_CAMERA = "webrtc_camera"  # WebRTC from browser camera
    WEBRTC_SCREEN = "webrtc_screen"  # WebRTC from browser screen share


class LiveStreamStatus(str, PyEnum):
    """Статусы live stream (синхронизирован с domain/entities/stream.py)."""
    IDLE = "idle"           # Stream создан, но не запущен
    ACTIVE = "active"       # Stream активно транслирует
    PAUSED = "paused"       # Stream приостановлен
    STOPPED = "stopped"     # Stream остановлен
    ERROR = "error"         # Ошибка при трансляции


class LiveStream(Base):
    """ORM Model для live streaming broadcasts.

    **Table**: live_streams
    **Entity Mapping**: См. infrastructure/persistence/mappers/live_stream_mapper.py

    **Relationships**:
    - owner: User (FK to users.id)
    - guest_sessions: List[GuestSession] (one-to-many, cascade delete)
    - recordings: List[Recording] (one-to-many, cascade delete)

    **Timestamps**:
    - created_at: Время создания stream
    - started_at: Время последнего запуска (NULL если никогда не запускался)
    - stopped_at: Время последней остановки (NULL если не останавливался)
    - went_live_at: Время когда stream стал LIVE (NULL если scheduled)
    """
    __tablename__ = "live_streams"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Core Fields
    chat_id = Column(BigInteger, nullable=False, index=True, comment="Telegram chat ID для трансляции")
    title = Column(String(255), nullable=False, comment="Название live stream")
    status = Column(
        SQLEnum(LiveStreamStatus, name="live_stream_status", create_type=True),
        nullable=False,
        default=LiveStreamStatus.IDLE,
        comment="Текущий статус live stream"
    )

    # Live Streaming Fields
    ingestion_type = Column(
        SQLEnum(IngestionType, name="ingestion_type", create_type=True),
        nullable=False,
        comment="Тип входящего потока (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)"
    )
    ingestion_url = Column(String(512), nullable=True, comment="URL для RTMP/SRT ingestion")
    stream_key = Column(String(255), nullable=True, unique=True, comment="Уникальный ключ для RTMP ingestion")

    # Viewer & Latency Metrics
    viewer_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Текущее количество зрителей"
    )
    latency_ms = Column(
        Integer,
        nullable=True,
        comment="Текущая задержка в миллисекундах (NULL если не измеряется)"
    )

    # Preview & Recording
    preview_url = Column(String(512), nullable=True, comment="URL для превью потока (HLS/DASH)")
    recording_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Автоматическая запись потока"
    )
    active_recording_id = Column(
        GUID(),
        nullable=True,
        comment="ID активной записи (NULL если запись не идет)"
    )

    # Guest Co-Hosting
    max_guests = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Максимальное количество со-ведущих"
    )
    current_guest_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Текущее количество активных гостей"
    )

    # Stream Configuration
    quality_preset = Column(
        String(50),
        nullable=True,
        comment="Пресет качества (low, medium, high, ultra)"
    )
    is_chat_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Включен ли чат во время трансляции"
    )

    # Error Handling
    last_error = Column(
        Text,
        nullable=True,
        comment="Последняя ошибка если status=ERROR"
    )
    error_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество ошибок с момента последнего запуска"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания live stream"
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего запуска live stream (NULL если никогда не запускался)"
    )
    stopped_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней остановки live stream (NULL если не останавливался)"
    )
    went_live_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время когда stream стал LIVE (NULL если создан как live)"
    )
    last_viewer_update = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего обновления счетчика зрителей"
    )

    # Relationships
    owner = relationship("src.models.user.User", back_populates="live_streams", lazy="joined")
    guest_sessions = relationship(
        "src.models.guest_session.GuestSession",
        back_populates="live_stream",
        cascade="all, delete-orphan",
        lazy="select"
    )
    recordings = relationship(
        "src.models.recording.Recording",
        back_populates="live_stream",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<LiveStream(id={self.id}, title='{self.title}', status={self.status}, ingestion_type={self.ingestion_type}, chat_id={self.chat_id})>"
