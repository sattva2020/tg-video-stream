"""
Pydantic schemas для Schedule API.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.models.schedule import RepeatType


class TimeSlotBase(BaseModel):
    """Базовый слот времени для шаблонов."""
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    playlist_id: Optional[str] = None
    title: Optional[str] = None
    color: str = "#3B82F6"


class ScheduleSlotCreate(BaseModel):
    """Создание слота расписания."""
    channel_id: str
    playlist_id: Optional[str] = None
    start_date: date
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    repeat_type: RepeatType = RepeatType.NONE
    repeat_days: Optional[List[int]] = None  # 0=Пн, 6=Вс
    repeat_until: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: str = "#3B82F6"
    priority: int = 0


class ScheduleSlotUpdate(BaseModel):
    """Обновление слота расписания."""
    playlist_id: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    repeat_type: Optional[RepeatType] = None
    repeat_days: Optional[List[int]] = None
    repeat_until: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ScheduleSlotResponse(BaseModel):
    """Ответ с данными слота."""
    id: str
    channel_id: str
    playlist_id: Optional[str]
    playlist_name: Optional[str] = None
    start_date: date
    start_time: str
    end_time: str
    repeat_type: RepeatType
    repeat_days: Optional[List[int]]
    repeat_until: Optional[date]
    title: Optional[str]
    description: Optional[str]
    color: str
    is_active: bool
    priority: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleTemplateCreate(BaseModel):
    """Создание шаблона расписания."""
    name: str
    description: Optional[str] = None
    channel_id: Optional[str] = None
    slots: List[TimeSlotBase]
    is_public: bool = False


class ScheduleTemplateResponse(BaseModel):
    """Ответ с данными шаблона."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    slots: List[dict]
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistCreate(BaseModel):
    """Создание плейлиста."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    channel_id: Optional[str] = None
    color: str = "#8B5CF6"
    source_type: str = "manual"
    source_url: Optional[str] = None
    items: List[dict] = []
    is_shuffled: bool = False


class PlaylistUpdate(BaseModel):
    """Обновление плейлиста."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    items: Optional[List[dict]] = None
    is_active: Optional[bool] = None
    is_shuffled: Optional[bool] = None
    is_public: Optional[bool] = None


class PlaylistResponse(BaseModel):
    """Ответ с данными плейлиста."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    group_id: Optional[str] = None
    position: int = 0
    color: str
    source_type: str
    source_url: Optional[str]
    items: List[dict]
    items_count: int
    total_duration: int
    is_active: bool
    is_shuffled: bool
    is_public: bool = False
    share_code: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistGroupCreate(BaseModel):
    """Создание группы плейлистов."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    channel_id: Optional[str] = None
    color: str = "#6366F1"
    icon: str = "folder"


class PlaylistGroupUpdate(BaseModel):
    """Обновление группы плейлистов."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    position: Optional[int] = None
    is_expanded: Optional[bool] = None
    is_active: Optional[bool] = None


class PlaylistGroupResponse(BaseModel):
    """Ответ с данными группы плейлистов."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    color: str
    icon: str
    position: int
    is_expanded: bool
    is_active: bool
    playlists_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistGroupWithPlaylistsResponse(PlaylistGroupResponse):
    """Группа с вложенными плейлистами."""
    playlists: List[PlaylistResponse] = []


class BulkCopyRequest(BaseModel):
    """Запрос на копирование расписания."""
    source_date: date
    target_dates: List[date]
    channel_id: str


class ApplyTemplateRequest(BaseModel):
    """Запрос на применение шаблона."""
    template_id: str
    channel_id: str
    target_dates: List[date]


class CalendarViewResponse(BaseModel):
    """Ответ для календарного представления."""
    date: date
    slots_count: int
    has_conflicts: bool = False
