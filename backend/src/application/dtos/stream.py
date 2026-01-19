"""
Stream DTOs

Request/Response DTOs для Use Cases управления потоками вещания.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class CreateStreamRequest:
    """
    Запрос на создание нового потока вещания.
    
    Attributes:
        owner_id: ID владельца потока
        chat_id: ID Telegram чата для вещания
        title: Название потока
        track_ids: Список ID треков для плейлиста (optional)
    """
    owner_id: int
    chat_id: int | str  # может быть username с @
    title: str
    track_ids: List[int] | None = None


@dataclass(frozen=True)
class CreateStreamResponse:
    """
    Результат создания потока.
    
    Attributes:
        stream_id: ID созданного потока
        owner_id: ID владельца
        chat_id: ID чата
        title: Название потока
        status: Статус потока (IDLE)
        created_at: Время создания
    """
    stream_id: int
    owner_id: int
    chat_id: int | str
    title: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class GetStreamStatusRequest:
    """
    Запрос на получение статуса потока.
    
    Attributes:
        stream_id: ID потока
    """
    stream_id: int


@dataclass(frozen=True)
class GetStreamStatusResponse:
    """
    Текущий статус потока.
    
    Attributes:
        stream_id: ID потока
        status: Статус потока (IDLE, ACTIVE, PAUSED, STOPPED)
        current_track_index: Индекс текущего трека
        title: Название потока
        owner_id: ID владельца
        chat_id: ID чата
        started_at: Время запуска (если активен)
    """
    stream_id: int
    status: str
    current_track_index: int
    title: str
    owner_id: int
    chat_id: int | str
    started_at: datetime | None = None
