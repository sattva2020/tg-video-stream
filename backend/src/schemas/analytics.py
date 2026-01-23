"""
Analytics API schemas
Feature: 021-admin-analytics-menu, 012-comprehensive-analytics-dashboard
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


# === Engagement Metrics Schemas ===

class EngagementTrendPoint(BaseModel):
    """Точка на графике вовлеченности."""
    timestamp: datetime = Field(..., description="Временная метка")
    message_count: int = Field(..., ge=0, description="Количество сообщений в чате")
    reaction_count: int = Field(..., ge=0, description="Количество реакций")
    unique_users: int = Field(..., ge=0, description="Количество уникальных пользователей")


class ActiveUserItem(BaseModel):
    """Активный пользователь в рейтинге."""
    user_id: Optional[int] = Field(None, description="ID пользователя")
    username: Optional[str] = Field(None, description="Имя пользователя")
    message_count: int = Field(..., ge=0, description="Количество сообщений")
    reaction_count: int = Field(..., ge=0, description="Количество реакций")
    last_activity: datetime = Field(..., description="Время последней активности")


class EngagementMetricsResponse(BaseModel):
    """Метрики вовлеченности за период."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    total_messages: int = Field(..., ge=0, description="Общее количество сообщений")
    total_reactions: int = Field(..., ge=0, description="Общее количество реакций")
    total_comments: int = Field(..., ge=0, description="Общее количество комментариев")
    unique_users: int = Field(..., ge=0, description="Количество уникальных пользователей")
    average_daily: float = Field(..., ge=0, description="Среднее количество событий в день")
    top_active_users: List[ActiveUserItem] = Field(default_factory=list, description="Топ активных пользователей")
    engagement_over_time: List[EngagementTrendPoint] = Field(default_factory=list, description="Данные для графика")
    cached_at: datetime = Field(..., description="Время кэширования")


# === Stream Performance Schemas ===

class QualityDistributionItem(BaseModel):
    """Распределение по качеству."""
    quality: str = Field(..., description="Уровень качества")
    count: int = Field(..., ge=0, description="Количество записей")
    percentage: float = Field(..., ge=0, le=100, description="Процент от общего количества")


class QualityTrendPoint(BaseModel):
    """Точка на графике качества потока."""
    timestamp: datetime = Field(..., description="Временная метка")
    overall_quality: str = Field(..., description="Общее качество")
    audio_bitrate_kbps: Optional[int] = Field(None, ge=0, description="Аудио битрейт")
    video_bitrate_kbps: Optional[int] = Field(None, ge=0, description="Видео битрейт")
    buffering_percentage: Optional[float] = Field(None, ge=0, le=100, description="Процент буферизации")


class StreamPerformanceResponse(BaseModel):
    """Показатели производительности потока."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    uptime_percentage: float = Field(..., ge=0, le=100, description="Процент аптайма")
    uptime_hours: float = Field(..., ge=0, description="Аптайм в часах")
    average_buffering_percentage: float = Field(..., ge=0, le=100, description="Средний процент буферизации")
    quality_changes_count: int = Field(..., ge=0, description="Количество изменений качества")
    bandwidth_usage_mbps: Optional[float] = Field(None, ge=0, description="Использование полосы пропускания")
    current_quality: str = Field(..., description="Текущее качество потока")
    quality_distribution: List[QualityDistributionItem] = Field(default_factory=list, description="Распределение по качеству")
    quality_over_time: List[QualityTrendPoint] = Field(default_factory=list, description="Данные для графика")
    cached_at: datetime = Field(..., description="Время кэширования")


# === Content Insights Schemas ===

class ContentPerformanceItem(BaseModel):
    """Элемент контента в рейтинге."""
    content_id: str = Field(..., description="ID контента")
    title: str = Field(..., description="Название контента")
    total_views: int = Field(..., ge=0, description="Общее количество просмотров")
    average_completion_percentage: float = Field(..., ge=0, le=100, description="Средний процент досмотра")
    total_watch_time_minutes: float = Field(..., ge=0, description="Общее время просмотра в минутах")
    average_watch_duration_seconds: float = Field(..., ge=0, description="Средняя длительность просмотра")


class DropOffPoint(BaseModel):
    """Точка отказа (drop-off point)."""
    position_seconds: int = Field(..., ge=0, description="Позиция в секундах")
    percentage: float = Field(..., ge=0, le=100, description="Процент зрителей, остановившихся здесь")
    viewers_count: int = Field(..., ge=0, description="Количество зрителей")
    cumulative_drop_off: float = Field(..., ge=0, le=100, description="Кумулятивный процент отказа")


class ContentInsightsResponse(BaseModel):
    """Аналитика контента."""
    period: AnalyticsPeriod = Field(..., description="Период данных")
    most_watched: List[ContentPerformanceItem] = Field(default_factory=list, description="Самый просматриваемый контент")
    drop_off_points: List[DropOffPoint] = Field(default_factory=list, description="Точки отказа")
    average_completion_rate: float = Field(..., ge=0, le=100, description="Средний рейтинг завершения")
    total_sessions: int = Field(..., ge=0, description="Общее количество сессий")
    average_session_duration_seconds: float = Field(..., ge=0, description="Средняя длительность сессии")
    cached_at: datetime = Field(..., description="Время кэширования")
