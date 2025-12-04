"""
Модели данных для системы очередей стримов.

Определяет Pydantic-модели для:
- QueueItem: элемент очереди воспроизведения
- QueueInfo: информация об очереди канала
- QueueOperations: операции с очередью (add, remove, move, skip)

Storage: Redis List (stream_queue:{channel_id})

Автор: Sattva Team
Дата: 2025-12-01
Спецификация: specs/016-github-integrations/data-model.md
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional, ClassVar

from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict


class QueueSource(str, Enum):
    """Источник контента для элемента очереди."""

    YOUTUBE = "youtube"
    FILE = "file"
    STREAM = "stream"


class QueueItem(BaseModel):
    """
    Элемент очереди воспроизведения.

    Хранится как JSON в Redis List.
    Lifecycle: создается при добавлении → удаляется при воспроизведении/skip.

    Attributes:
        id: Уникальный UUID элемента
        channel_id: ID Telegram канала (отрицательное число для каналов/групп)
        title: Название трека (1-500 символов)
        url: URL аудио/видео контента
        duration: Длительность в секундах (опционально)
        source: Источник контента (youtube, file, stream)
        requested_by: Telegram user_id того, кто добавил (опционально)
        added_at: Время добавления в очередь
        metadata: Дополнительные данные (thumbnail, artist и т.д.)
    """

    QUEUE_KEY_PREFIX: ClassVar[str] = "stream_queue"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: int = Field(..., description="ID Telegram канала")
    title: str = Field(..., min_length=1, max_length=500, description="Название трека")
    url: str = Field(..., description="URL аудио/видео")
    duration: Optional[int] = Field(None, ge=0, description="Длительность в секундах")
    source: QueueSource = Field(..., description="Источник контента")
    requested_by: Optional[int] = Field(None, description="Telegram user_id")
    added_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Валидация URL (базовая проверка формата)."""
        if not v.startswith(("http://", "https://", "file://")):
            raise ValueError("URL must start with http://, https://, or file://")
        return v

    def to_redis_json(self) -> str:
        """Сериализация для хранения в Redis."""
        import json

        data = self.model_dump()
        data["added_at"] = self.added_at.isoformat()
        return json.dumps(data)

    @classmethod
    def from_redis_json(cls, json_str: str) -> "QueueItem":
        """Десериализация из Redis."""
        import json

        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def get_queue_key(cls, channel_id: int | str) -> str:
        """Получить Redis-ключ для очереди канала."""
        return f"{cls.QUEUE_KEY_PREFIX}:{channel_id}"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "channel_id": -1001234567890,
                "title": "Meditation Music - 1 Hour",
                "url": "https://youtube.com/watch?v=abc123",
                "duration": 3600,
                "source": "youtube",
                "requested_by": 123456789,
                "added_at": "2025-12-01T10:30:00Z",
                "metadata": {
                    "thumbnail": "https://i.ytimg.com/vi/abc123/default.jpg",
                    "artist": "Relaxing Sounds",
                },
            }
        }
    )


class QueueItemCreate(BaseModel):
    """Модель для создания элемента очереди (входные данные API)."""

    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., description="URL аудио/видео")
    duration: Optional[int] = Field(None, ge=0)
    source: QueueSource = QueueSource.YOUTUBE
    requested_by: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    position: Optional[int] = Field(
        None, ge=0, description="Позиция в очереди (None = в конец)"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Валидация URL."""
        if not v.startswith(("http://", "https://", "file://")):
            raise ValueError("URL must start with http://, https://, or file://")
        return v


class QueueInfo(BaseModel):
    """
    Информация об очереди канала.

    Возвращается при GET /api/v1/queue/{channel_id}.
    """

    channel_id: int
    items: list[QueueItem]
    total_items: int = Field(..., ge=0, description="Количество элементов в очереди")
    total_duration: Optional[int] = Field(None, ge=0, description="Общая длительность в секундах")
    current_index: int = Field(0, ge=0, description="Индекс текущего трека")
    is_playing: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "channel_id": -1001234567890,
                "items": [],
                "total_items": 0,
                "total_duration": 0,
                "current_index": 0,
                "is_playing": False,
            }
        }
    )

    @property
    def total_count(self) -> int:
        """Обратная совместимость со старым именем поля."""
        return self.total_items


class QueueOperationResult(BaseModel):
    """Результат операции с очередью."""

    success: bool
    message: str
    item: Optional[QueueItem] = None
    queue_size: int = 0


class QueueMoveRequest(BaseModel):
    """Запрос на перемещение элемента в очереди."""

    item_id: str = Field(..., description="ID элемента для перемещения")
    new_position: int = Field(..., ge=0, description="Новая позиция в очереди")


class QueueBulkAddRequest(BaseModel):
    """Запрос на добавление нескольких элементов."""

    items: list[QueueItemCreate] = Field(..., min_length=1, max_length=100)


class QueueOperationType(str, Enum):
    """Типы операций очереди для уведомлений/WebSocket."""

    ADD = "add"
    REMOVE = "remove"
    MOVE = "move"
    CLEAR = "clear"
    SKIP = "skip"
    PRIORITY_ADD = "priority_add"


class QueueOperation(BaseModel):
    """Модель операции очереди для событий и метрик."""

    operation: QueueOperationType | str = Field(..., description="Тип операции")
    channel_id: int = Field(..., description="ID канала")
    item_id: Optional[str] = Field(None, description="ID элемента очереди")
    position: Optional[int] = Field(None, ge=0, description="Позиция элемента")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC время события")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "operation": "add",
                "channel_id": -1001234567890,
                "item_id": "550e8400-e29b-41d4-a716-446655440000",
                "position": 0,
                "timestamp": "2025-12-01T10:30:00Z",
            }
        }
    )
