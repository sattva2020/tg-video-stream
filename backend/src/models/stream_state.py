"""Пайдантик-модели для хранения состояния стрима и auto-end таймера."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StreamStatus(str, Enum):
    """Поддерживаемые статусы аудио-стрима."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    PLACEHOLDER = "placeholder"


class StreamState(BaseModel):
    """Актуальное состояние стрима, которое хранится в Redis Hash."""

    channel_id: int = Field(..., description="ID Telegram канала")
    status: StreamStatus = Field(StreamStatus.STOPPED, description="Текущий статус")
    current_item_id: Optional[str] = Field(None, description="UUID текущего QueueItem")
    started_at: Optional[datetime] = Field(None, description="Время запуска текущего трека")
    current_position: int = Field(0, ge=0, description="Позиция воспроизведения в секундах")
    listeners_count: int = Field(0, ge=0, description="Количество слушателей")
    is_placeholder: bool = Field(False, description="Флаг placeholder контента")
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        """Любой статус, кроме STOPPED, считаем активным."""

        return self.status != StreamStatus.STOPPED

    def can_transition_to(self, new_status: StreamStatus) -> bool:
        """Проверка, допускается ли переход между статусами."""

        allowed = {
            StreamStatus.STOPPED: {StreamStatus.PLAYING, StreamStatus.PLACEHOLDER},
            StreamStatus.PLAYING: {StreamStatus.PAUSED, StreamStatus.STOPPED, StreamStatus.PLACEHOLDER},
            StreamStatus.PAUSED: {StreamStatus.PLAYING, StreamStatus.STOPPED},
            StreamStatus.PLACEHOLDER: {StreamStatus.PLAYING, StreamStatus.STOPPED},
        }
        return new_status in allowed.get(self.status, set())


class AutoEndTimer(BaseModel):
    """Redis-сущность для auto-end таймера."""

    channel_id: int = Field(..., description="ID канала")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_at: datetime = Field(..., description="ISO timestamp срабатывания")
    timeout_minutes: int = Field(5, ge=1, le=60, description="Таймаут в минутах")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "channel_id": -1001234567890,
                "started_at": "2025-12-01T10:30:00Z",
                "timeout_at": "2025-12-01T10:35:00Z",
                "timeout_minutes": 5,
            }
        }
    )

    @classmethod
    def create(cls, channel_id: int, timeout_minutes: int = 5) -> AutoEndTimer:
        now = datetime.now(timezone.utc)
        return cls(
            channel_id=channel_id,
            started_at=now,
            timeout_at=now + timedelta(minutes=timeout_minutes),
            timeout_minutes=timeout_minutes,
        )

    @staticmethod
    def get_redis_key(channel_id: Union[int, str]) -> str:
        return f"auto_end_timer:{channel_id}"

    @property
    def remaining_seconds(self) -> int:
        remaining = (self.timeout_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.timeout_at

    def to_redis_json(self) -> str:
        payload = self.model_dump()
        payload["started_at"] = self.started_at.isoformat()
        payload["timeout_at"] = self.timeout_at.isoformat()
        return json.dumps(payload)

    @classmethod
    def from_redis_json(cls, json_str: str) -> AutoEndTimer:
        data = json.loads(json_str)
        return cls(**data)

    def to_warning(self, remaining_seconds: Optional[int] = None) -> AutoEndWarning:
        remaining = remaining_seconds if remaining_seconds is not None else self.remaining_seconds
        return AutoEndWarning(
            channel_id=self.channel_id,
            remaining_seconds=remaining,
            timeout_at=self.timeout_at,
        )


class AutoEndWarning(BaseModel):
    """Структура предупреждения о скором завершении стрима."""

    channel_id: int = Field(..., description="ID канала")
    remaining_seconds: int = Field(..., ge=0, description="Оставшееся время в секундах")
    timeout_at: datetime = Field(..., description="Время завершения таймера")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "channel_id": -1001234567890,
                "remaining_seconds": 45,
                "timeout_at": "2025-12-01T10:35:00Z",
                "timestamp": "2025-12-01T10:34:15Z",
            }
        }
    )

    @classmethod
    def from_timer(cls, timer: AutoEndTimer, remaining_seconds: Optional[int] = None) -> AutoEndWarning:
        return timer.to_warning(remaining_seconds)

    def to_websocket_payload(self) -> dict:
        return {
            "type": "auto_end_warning",
            "channel_id": self.channel_id,
            "remaining_seconds": self.remaining_seconds,
            "timeout_at": self.timeout_at.isoformat(),
            "timestamp": self.timestamp.isoformat(),
        }


class StreamEndReason(str, Enum):
    """Причины остановки стрима для логов и метрик."""

    AUTO_END = "auto_end"
    MANUAL = "manual"
    ERROR = "error"


class StreamStateUpdate(BaseModel):
    """Сообщение для WebSocket о состоянии стрима."""

    channel_id: int
    status: StreamStatus
    current_item_id: Optional[str] = None
    listeners_count: int = 0
    is_placeholder: bool = False
    queue_size: int = 0
    current_position: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
