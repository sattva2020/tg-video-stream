"""
Analytics API schemas
Feature: 021-admin-analytics-menu
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

AnalyticsPeriod = Literal["7d", "30d", "90d", "all"]
HistoryInterval = Literal["hour", "day"]
InteractionPeriod = Literal["1h", "24h", "7d", "30d", "90d", "all"]


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


# === Interaction Analytics Schemas ===

class MostVotedPoll(BaseModel):
    """Самый популярный опрос."""
    id: str = Field(..., description="ID опроса")
    question: str = Field(..., description="Вопрос опроса")
    vote_count: int = Field(..., ge=0, description="Количество голосов")


class PollStatsResponse(BaseModel):
    """Статистика опросов."""
    total_polls: int = Field(..., ge=0, description="Всего опросов")
    active_polls: int = Field(..., ge=0, description="Активных опросов")
    total_votes: int = Field(..., ge=0, description="Всего голосов")
    unique_voters: int = Field(..., ge=0, description="Уникальных проголосовавших")
    avg_participation_rate: float = Field(..., ge=0, description="Средний уровень участия")
    most_voted_poll: Optional[MostVotedPoll] = Field(None, description="Самый популярный опрос")


class QAStatsResponse(BaseModel):
    """Статистика Q&A."""
    total_questions: int = Field(..., ge=0, description="Всего вопросов")
    pending_questions: int = Field(..., ge=0, description="Ожидающих ответа")
    answered_questions: int = Field(..., ge=0, description="Отвеченных вопросов")
    total_upvotes: int = Field(..., ge=0, description="Всего upvotes")
    unique_participants: int = Field(..., ge=0, description="Уникальных участников")
    avg_answer_time_hours: Optional[float] = Field(None, description="Среднее время ответа (часы)")


class EmojiUsage(BaseModel):
    """Использование эмодзи."""
    emoji: str = Field(..., description="Эмодзи")
    count: int = Field(..., ge=0, description="Количество использований")


class ReactionStatsResponse(BaseModel):
    """Статистика реакций."""
    total_reactions: int = Field(..., ge=0, description="Всего реакций")
    unique_users: int = Field(..., ge=0, description="Уникальных пользователей")
    top_emojis: List[EmojiUsage] = Field(default_factory=list, description="Топ эмодзи")
    reactions_per_hour: float = Field(..., ge=0, description="Реакций в час")


class ChatStatsResponse(BaseModel):
    """Статистика чата."""
    total_messages: int = Field(..., ge=0, description="Всего сообщений")
    unique_authors: int = Field(..., ge=0, description="Уникальных авторов")
    avg_message_length: float = Field(..., ge=0, description="Средняя длина сообщения")
    messages_per_hour: float = Field(..., ge=0, description="Сообщений в час")
    filtered_messages: int = Field(..., ge=0, description="Отфильтрованных сообщений")


class ActiveUser(BaseModel):
    """Активный пользователь."""
    user_id: int = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    interaction_count: int = Field(..., ge=0, description="Количество взаимодействий")


class EngagementSummaryResponse(BaseModel):
    """Сводная статистика взаимодействий."""
    total_interactions: int = Field(..., ge=0, description="Всего взаимодействий")
    poll_participation_rate: float = Field(..., ge=0, le=100, description="Участие в опросах (0-100)")
    qa_engagement_rate: float = Field(..., ge=0, le=100, description="Вовлеченность в Q&A (0-100)")
    reaction_intensity: float = Field(..., ge=0, le=100, description="Интенсивность реакций (0-100)")
    chat_activity_level: float = Field(..., ge=0, le=100, description="Активность чата (0-100)")
    most_active_users: List[ActiveUser] = Field(default_factory=list, description="Самые активные пользователи")
    peak_interaction_hour: Optional[str] = Field(None, description="Пиковый час взаимодействий")


class InteractionMetricsResponse(BaseModel):
    """Полные метрики взаимодействий."""
    period: InteractionPeriod = Field(..., description="Период данных")
    polls: PollStatsResponse = Field(..., description="Статистика опросов")
    qa: QAStatsResponse = Field(..., description="Статистика Q&A")
    reactions: ReactionStatsResponse = Field(..., description="Статистика реакций")
    chat: ChatStatsResponse = Field(..., description="Статистика чата")
    engagement: EngagementSummaryResponse = Field(..., description="Сводная статистика")
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Время кэширования")
