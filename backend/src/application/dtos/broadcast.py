"""
Broadcast DTOs

Request/Response DTOs для Use Cases управления трансляциями.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StartBroadcastRequest:
    """
    Запрос на запуск трансляции.
    
    Attributes:
        stream_id: ID потока для запуска (UUID строка)
        user_id: ID пользователя, запускающего трансляцию (UUID строка)
    """
    stream_id: str  # UUID string
    user_id: str    # UUID string


@dataclass(frozen=True)
class StartBroadcastResponse:
    """
    Результат запуска трансляции.
    
    Attributes:
        stream_id: ID потока (UUID строка)
        status: Новый статус (ACTIVE)
        started_at: Время запуска трансляции
        chat_id: ID чата с активной трансляцией
        current_track_index: Индекс текущего трека
    """
    stream_id: str  # UUID string
    status: str
    started_at: datetime
    chat_id: int | str
    current_track_index: int


@dataclass(frozen=True)
class PauseBroadcastRequest:
    """
    Запрос на паузу трансляции.
    
    Attributes:
        stream_id: ID потока для паузы
        user_id: ID пользователя, ставящего на паузу
    """
    stream_id: int
    user_id: int


@dataclass(frozen=True)
class PauseBroadcastResponse:
    """
    Результат паузы трансляции.
    
    Attributes:
        stream_id: ID потока
        status: Новый статус (PAUSED)
        paused_at: Время паузы трансляции
    """
    stream_id: int
    status: str
    paused_at: datetime


@dataclass(frozen=True)
class ResumeBroadcastRequest:
    """
    Запрос на возобновление трансляции.
    
    Attributes:
        stream_id: ID потока для возобновления
        user_id: ID пользователя, возобновляющего трансляцию
    """
    stream_id: int
    user_id: int


@dataclass(frozen=True)
class ResumeBroadcastResponse:
    """
    Результат возобновления трансляции.
    
    Attributes:
        stream_id: ID потока
        status: Новый статус (ACTIVE)
        resumed_at: Время возобновления трансляции
    """
    stream_id: int
    status: str
    resumed_at: datetime


@dataclass(frozen=True)
class StopBroadcastRequest:
    """
    Запрос на остановку трансляции.
    
    Attributes:
        stream_id: ID потока для остановки
        user_id: ID пользователя, останавливающего трансляцию
    """
    stream_id: int
    user_id: int


@dataclass(frozen=True)
class StopBroadcastResponse:
    """
    Результат остановки трансляции.
    
    Attributes:
        stream_id: ID потока
        status: Новый статус (STOPPED)
        stopped_at: Время остановки трансляции
    """
    stream_id: int
    status: str
    stopped_at: datetime
