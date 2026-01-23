"""
Analytics API schemas
Feature: 021-admin-analytics-menu
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

AnalyticsPeriod = Literal["7d", "30d", "90d", "all"]
HistoryInterval = Literal["hour", "day"]


# === Listener Schemas ===

class ListenerStatsResponse(BaseModel):
    """Текущая статистика слушателей."""
    current: int = Field(..., description="Текущее количество слушателей")
    peak_today: int = Field(..., description="Пиковое значение за сегодня")
    peak_week: int = Field(..., description="Пиковое значение за неделю")
    average_week: float = Field(..., description="Среднее за неделю")


class ListenerHistoryPoint(BaseModel):
    """Точка на графике истории слушателей."""
    timestamp: datetime = Field(..., description="Временная метка")
    count: int = Field(..., ge=0, description="Количество слушателей")


class ListenerHistoryResponse(BaseModel):
    """История слушателей за период."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    data: List[ListenerHistoryPoint] = Field(default_factory=list, description="Данные для графика")


# === Top Tracks Schemas ===

class TopTrackItem(BaseModel):
    """Трек в топе."""
    track_id: int = Field(..., description="ID трека")
    title: str = Field(..., description="Название трека")
    artist: Optional[str] = Field(None, description="Исполнитель")
    play_count: int = Field(..., ge=0, description="Количество воспроизведений")
    total_duration_seconds: int = Field(..., ge=0, description="Общая длительность в секундах")


class TopTracksResponse(BaseModel):
    """Топ треков за период."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    tracks: List[TopTrackItem] = Field(default_factory=list, description="Список треков")


# === Summary Schema ===

class AnalyticsSummaryResponse(BaseModel):
    """Сводная статистика."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    total_plays: int = Field(..., ge=0, description="Общее количество воспроизведений")
    total_duration_hours: float = Field(..., ge=0, description="Общее время вещания в часах")
    unique_tracks: int = Field(..., ge=0, description="Количество уникальных треков")
    listeners: ListenerStatsResponse = Field(..., description="Статистика слушателей")
    cached_at: datetime = Field(..., description="Время кэширования")


# === Internal Schemas (for streamer) ===

class TrackPlayRequest(BaseModel):
    """Запрос на запись воспроизведения трека."""
    track_id: int = Field(..., description="ID трека")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Длительность в секундах")
    listeners_count: int = Field(..., ge=0, description="Количество слушателей")


class TrackPlayResponse(BaseModel):
    """Ответ на запись воспроизведения трека."""
    id: int = Field(..., description="ID записи")
    played_at: datetime = Field(..., description="Время записи")


# === Multi-Platform Analytics Schemas ===

class PlatformMetrics(BaseModel):
    """Метрики для отдельной платформы."""
    platform_type: str = Field(..., description="Тип платформы (youtube, twitch, etc.)")
    platform_name: str = Field(..., description="Название платформы")
    status: str = Field(..., description="Текущий статус")
    stream_count: int = Field(..., ge=0, description="Количество стримов")
    total_stream_hours: float = Field(..., ge=0, description="Общее время стриминга в часах")
    post_count: int = Field(..., ge=0, description="Количество постов")
    successful_posts: int = Field(..., ge=0, description="Успешные посты")
    failed_posts: int = Field(..., ge=0, description="Неудачные посты")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")


class MultiPlatformAnalyticsResponse(BaseModel):
    """Агрегированная аналитика по всем платформам."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    total_platforms: int = Field(..., ge=0, description="Общее количество платформ")
    active_platforms: int = Field(..., ge=0, description="Активные платформы")
    platforms: List[PlatformMetrics] = Field(default_factory=list, description="Метрики по платформам")
    total_streams: int = Field(..., ge=0, description="Общее количество стримов")
    total_stream_hours: float = Field(..., ge=0, description="Общее время стриминга в часах")
    total_posts: int = Field(..., ge=0, description="Общее количество постов")
    successful_posts_rate: float = Field(..., ge=0, le=100, description="Процент успешных постов")
    cached_at: datetime = Field(..., description="Время кэширования")
