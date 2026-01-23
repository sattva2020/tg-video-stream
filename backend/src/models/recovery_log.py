"""RecoveryLog ORM Model.

SQLAlchemy model для логирования попыток автоматического восстановления потоков.
Создан в рамках Feature 001 (Intelligent Auto-Recovery System).

**Purpose**: Хранение истории попыток восстановления с детальным контекстом для отладки
**Layer**: Infrastructure (persistence)
**Features**: Отслеживание failure types, exponential backoff, circuit breaker state

**Design Decision**:
- Отдельная таблица для истории всех попыток восстановления
- Позволяет анализировать recurring failures и оптимизировать recovery стратегии
- JSONB поля для гибкого хранения контекста и metadata
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, String, BigInteger, DateTime, Enum as SQLEnum, ForeignKey, func, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class RecoveryFailureType(str, PyEnum):
    """Типы failure, вызвавших необходимость восстановления."""
    NETWORK = "network"               # Потеря сетевого соединения
    API_RATE_LIMIT = "api_rate_limit" # Telegram API rate limit
    CODEC_ERROR = "codec_error"       # FFmpeg/video codec ошибка
    SESSION_EXPIRED = "session_expired"  # Telegram session истек
    PROCESS_CRASH = "process_crash"   # Процесс потокового сервиса упал
    UNKNOWN = "unknown"               # Неизвестная ошибка


class RecoveryStrategy(str, PyEnum):
    """Стратегии восстановления."""
    RESTART = "restart"               # Полный перезапуск потока
    RECONNECT = "reconnect"           # Переподключение без остановки
    FALLBACK = "fallback"             # Переключение на fallback URL/источник
    MANUAL = "manual"                 # Требует ручного вмешательства


class RecoveryStatus(str, PyEnum):
    """Статусы попытки восстановления."""
    PENDING = "pending"               # Запланирована, но не началась
    IN_PROGRESS = "in_progress"       # Выполняется
    SUCCESS = "success"               # Успешно завершено
    FAILED = "failed"                 # Не удалось (будет retry)
    ABANDONED = "abandoned"           # Превышен max retries, требуется ручное вмешательство


class RecoveryLog(Base):
    """ORM Model для логирования попыток автоматического восстановления.

    **Table**: recovery_logs
    **Purpose**: История всех попыток recovery с детальным контекстом

    **Relationships**:
    - stream: Stream (FK to streams.id)

    **Key Features**:
    - Отслеживание retry attempts с exponential backoff
    - Circuit breaker integration
    - Детальный контекст для отладки recurring failures
    """
    __tablename__ = "recovery_logs"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Failure Information
    failure_type = Column(
        SQLEnum(RecoveryFailureType, name="recovery_failure_type", create_type=True),
        nullable=False,
        index=True,
        comment="Тип failure, вызвавшего восстановление"
    )
    failure_reason = Column(
        Text,
        nullable=False,
        comment="Детальное описание причины failure"
    )
    error_code = Column(
        String(50),
        nullable=True,
        comment="Код ошибки (если применимо)"
    )

    # Recovery Configuration
    recovery_strategy = Column(
        SQLEnum(RecoveryStrategy, name="recovery_strategy", create_type=True),
        nullable=False,
        default=RecoveryStrategy.RESTART,
        comment="Выбранная стратегия восстановления"
    )
    status = Column(
        SQLEnum(RecoveryStatus, name="recovery_status", create_type=True),
        nullable=False,
        default=RecoveryStatus.PENDING,
        index=True,
        comment="Текущий статус попытки восстановления"
    )

    # Retry Tracking
    attempt_number = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Номер попытки (1-based)"
    )
    max_attempts = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Максимальное количество попыток"
    )
    backoff_seconds = Column(
        Integer,
        nullable=True,
        comment="Текущая задержка backoff в секундах"
    )

    # Timestamps
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Время начала попытки восстановления"
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время завершения (успех или failure)"
    )
    duration_ms = Column(
        BigInteger,
        nullable=True,
        comment="Длительность попытки в миллисекундах"
    )

    # Additional Context (JSONB for flexibility)
    error_details = Column(
        JSONB,
        nullable=True,
        comment="Детали ошибки: stack_trace, exception_type, context"
    )
    recovery_metadata = Column(
        JSONB,
        nullable=True,
        comment="Контекст восстановления: stream_state, environment, config"
    )
    circuit_breaker_state = Column(
        JSONB,
        nullable=True,
        comment="Состояние circuit breaker на момент попытки"
    )

    # Relationships
    stream = relationship(
        "src.models.stream.Stream",
        back_populates="recovery_logs",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<RecoveryLog(id={self.id}, stream_id={self.stream_id}, "
            f"failure_type={self.failure_type}, status={self.status}, "
            f"attempt={self.attempt_number}/{self.max_attempts})>"
        )

    @property
    def is_successful(self) -> bool:
        """Проверка, успешно ли завершено восстановление."""
        return self.status == RecoveryStatus.SUCCESS

    @property
    def is_final(self) -> bool:
        """Проверка, является ли это финальной попыткой (no more retries)."""
        return self.status in (RecoveryStatus.SUCCESS, RecoveryStatus.ABANDONED)

    @property
    def should_retry(self) -> bool:
        """Проверка, следует ли повторить попытку."""
        return (
            self.status == RecoveryStatus.FAILED and
            self.attempt_number < self.max_attempts
        )
