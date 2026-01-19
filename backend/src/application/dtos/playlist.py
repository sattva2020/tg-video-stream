"""
Playlist DTOs (Data Transfer Objects)

Request/Response DTOs для Use Cases управления плейлистами.

**Phase 7**: Clean Architecture - DTO для границ слоёв
**Reference**: specs/025-clean-architecture-rules/tasks.md T070
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from .common import PaginationRequest, PaginationMeta


class PlaylistStatus(str, Enum):
    """Статусы плейлиста."""
    DRAFT = "draft"      # Черновик, не готов к воспроизведению
    READY = "ready"      # Готов к воспроизведению
    PLAYING = "playing"  # Сейчас воспроизводится
    ARCHIVED = "archived"  # Архивирован


class RepeatMode(str, Enum):
    """Режимы повтора плейлиста."""
    NONE = "none"        # Без повтора
    ONE = "one"          # Повтор текущего трека
    ALL = "all"          # Повтор всего плейлиста


# =============================================================================
# Track DTOs (nested in Playlist)
# =============================================================================

@dataclass(frozen=True)
class TrackDTO:
    """
    Представление трека в плейлисте.
    
    Attributes:
        id: Уникальный идентификатор трека
        title: Название трека
        artist: Исполнитель (optional)
        duration_seconds: Длительность в секундах
        file_path: Путь к файлу
        position: Позиция в плейлисте (0-based)
    """
    id: int
    title: str
    duration_seconds: int
    file_path: str
    position: int
    artist: Optional[str] = None


@dataclass(frozen=True)
class TrackSummaryDTO:
    """
    Краткое представление трека для списков.
    
    Attributes:
        id: ID трека
        title: Название
        duration_seconds: Длительность
    """
    id: int
    title: str
    duration_seconds: int


# =============================================================================
# Playlist DTOs (Read Operations)
# =============================================================================

@dataclass(frozen=True)
class PlaylistDTO:
    """
    Полное представление плейлиста для API ответов.
    
    Attributes:
        id: Уникальный идентификатор
        stream_id: ID связанного stream
        name: Название плейлиста
        status: Статус плейлиста
        repeat_mode: Режим повтора
        current_track_index: Индекс текущего трека
        tracks: Список треков
        total_duration_seconds: Общая длительность
        created_at: Время создания
        updated_at: Время последнего обновления
    """
    id: int
    stream_id: int
    name: str
    status: PlaylistStatus
    repeat_mode: RepeatMode
    current_track_index: int
    tracks: List[TrackDTO]
    total_duration_seconds: int
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class PlaylistSummaryDTO:
    """
    Краткое представление плейлиста для списков.
    
    Attributes:
        id: ID плейлиста
        name: Название
        track_count: Количество треков
        total_duration_seconds: Общая длительность
        status: Статус
    """
    id: int
    name: str
    track_count: int
    total_duration_seconds: int
    status: PlaylistStatus


# =============================================================================
# Playlist Request DTOs
# =============================================================================

@dataclass(frozen=True)
class GetPlaylistRequest:
    """
    Запрос на получение плейлиста по ID.
    
    Attributes:
        playlist_id: ID плейлиста
    """
    playlist_id: int


@dataclass(frozen=True)
class ListPlaylistsRequest:
    """
    Запрос на получение списка плейлистов.
    
    Attributes:
        pagination: Параметры пагинации
        stream_id: Фильтр по stream (optional)
        status: Фильтр по статусу (optional)
    """
    pagination: PaginationRequest
    stream_id: Optional[int] = None
    status: Optional[PlaylistStatus] = None


@dataclass(frozen=True)
class CreatePlaylistRequest:
    """
    Запрос на создание нового плейлиста.
    
    Attributes:
        stream_id: ID stream для привязки
        name: Название плейлиста
        track_ids: Список ID треков (optional)
        repeat_mode: Режим повтора (default: NONE)
    """
    stream_id: int
    name: str
    track_ids: List[int] = field(default_factory=list)
    repeat_mode: RepeatMode = RepeatMode.NONE


@dataclass(frozen=True)
class UpdatePlaylistRequest:
    """
    Запрос на обновление плейлиста.
    
    Attributes:
        playlist_id: ID плейлиста
        name: Новое название (optional)
        repeat_mode: Новый режим повтора (optional)
        status: Новый статус (optional)
    """
    playlist_id: int
    name: Optional[str] = None
    repeat_mode: Optional[RepeatMode] = None
    status: Optional[PlaylistStatus] = None


@dataclass(frozen=True)
class AddTracksRequest:
    """
    Запрос на добавление треков в плейлист.
    
    Attributes:
        playlist_id: ID плейлиста
        track_ids: Список ID треков для добавления
        position: Позиция вставки (optional, в конец по умолчанию)
    """
    playlist_id: int
    track_ids: List[int]
    position: Optional[int] = None


@dataclass(frozen=True)
class RemoveTracksRequest:
    """
    Запрос на удаление треков из плейлиста.
    
    Attributes:
        playlist_id: ID плейлиста
        track_ids: Список ID треков для удаления
    """
    playlist_id: int
    track_ids: List[int]


@dataclass(frozen=True)
class ReorderTracksRequest:
    """
    Запрос на изменение порядка треков.
    
    Attributes:
        playlist_id: ID плейлиста
        track_positions: Словарь {track_id: new_position}
    """
    playlist_id: int
    track_positions: dict  # {track_id: new_position}


@dataclass(frozen=True)
class DeletePlaylistRequest:
    """
    Запрос на удаление плейлиста.
    
    Attributes:
        playlist_id: ID плейлиста
    """
    playlist_id: int


# =============================================================================
# Playlist Response DTOs
# =============================================================================

@dataclass(frozen=True)
class CreatePlaylistResponse:
    """
    Результат создания плейлиста.
    
    Attributes:
        playlist: Созданный плейлист
    """
    playlist: PlaylistDTO


@dataclass(frozen=True)
class UpdatePlaylistResponse:
    """
    Результат обновления плейлиста.
    
    Attributes:
        playlist: Обновлённый плейлист
    """
    playlist: PlaylistDTO


@dataclass(frozen=True)
class ListPlaylistsResponse:
    """
    Результат запроса списка плейлистов.
    
    Attributes:
        playlists: Список плейлистов
        meta: Метаданные пагинации
    """
    playlists: List[PlaylistSummaryDTO]
    meta: PaginationMeta


@dataclass(frozen=True)
class AddTracksResponse:
    """
    Результат добавления треков.
    
    Attributes:
        playlist: Обновлённый плейлист
        added_count: Количество добавленных треков
    """
    playlist: PlaylistDTO
    added_count: int


@dataclass(frozen=True)
class RemoveTracksResponse:
    """
    Результат удаления треков.
    
    Attributes:
        playlist: Обновлённый плейлист
        removed_count: Количество удалённых треков
    """
    playlist: PlaylistDTO
    removed_count: int
