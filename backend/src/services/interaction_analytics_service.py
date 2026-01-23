"""
Interaction Analytics Service
Feature: 020-viewer-interaction-engagement-features

Сервис для сбора и кэширования аналитики взаимодействий:
- Статистика опросов (participation rate, total votes)
- Аналитика Q&A (questions submitted, answered, upvoted)
- Статистика реакций (emoji usage, activity patterns)
- Аналитика чата (message volume, active users)
- Сводная статистика взаимодействий
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.poll import Poll, PollOption, PollVote, PollStatus
from src.models.qa import Question, QuestionUpvote, QuestionStatus
from src.models.interaction import EmojiReaction, ChatMessage, ReactionDisplayStatus, ChatMessageStatus
from src.models.engagement import Shoutout, CTA
from src.models.user import User
from src.models.stream import Stream

from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "interaction_analytics:"
CACHE_POLL_STATS_KEY = f"{CACHE_PREFIX}poll_stats:{{period}}:{{stream_id}}"
CACHE_QA_STATS_KEY = f"{CACHE_PREFIX}qa_stats:{{period}}:{{stream_id}}"
CACHE_REACTION_STATS_KEY = f"{CACHE_PREFIX}reaction_stats:{{period}}:{{stream_id}}"
CACHE_CHAT_STATS_KEY = f"{CACHE_PREFIX}chat_stats:{{period}}:{{stream_id}}"
CACHE_ENGAGEMENT_SUMMARY_KEY = f"{CACHE_PREFIX}engagement_summary:{{period}}:{{stream_id}}"
CACHE_TTL = 300  # 5 minutes


class PollStats:
    """Статистика опросов."""
    def __init__(
        self,
        total_polls: int,
        active_polls: int,
        total_votes: int,
        unique_voters: int,
        avg_participation_rate: float,
        most_voted_poll: Optional[Dict[str, Any]]
    ):
        self.total_polls = total_polls
        self.active_polls = active_polls
        self.total_votes = total_votes
        self.unique_voters = unique_voters
        self.avg_participation_rate = avg_participation_rate
        self.most_voted_poll = most_voted_poll

    def model_dump(self) -> Dict[str, Any]:
        return {
            "total_polls": self.total_polls,
            "active_polls": self.active_polls,
            "total_votes": self.total_votes,
            "unique_voters": self.unique_voters,
            "avg_participation_rate": self.avg_participation_rate,
            "most_voted_poll": self.most_voted_poll
        }


class QAStats:
    """Статистика Q&A."""
    def __init__(
        self,
        total_questions: int,
        pending_questions: int,
        answered_questions: int,
        total_upvotes: int,
        unique_participants: int,
        avg_answer_time_hours: Optional[float]
    ):
        self.total_questions = total_questions
        self.pending_questions = pending_questions
        self.answered_questions = answered_questions
        self.total_upvotes = total_upvotes
        self.unique_participants = unique_participants
        self.avg_answer_time_hours = avg_answer_time_hours

    def model_dump(self) -> Dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "pending_questions": self.pending_questions,
            "answered_questions": self.answered_questions,
            "total_upvotes": self.total_upvotes,
            "unique_participants": self.unique_participants,
            "avg_answer_time_hours": self.avg_answer_time_hours
        }


class ReactionStats:
    """Статистика реакций."""
    def __init__(
        self,
        total_reactions: int,
        unique_users: int,
        top_emojis: List[Dict[str, Any]],
        reactions_per_hour: float
    ):
        self.total_reactions = total_reactions
        self.unique_users = unique_users
        self.top_emojis = top_emojis
        self.reactions_per_hour = reactions_per_hour

    def model_dump(self) -> Dict[str, Any]:
        return {
            "total_reactions": self.total_reactions,
            "unique_users": self.unique_users,
            "top_emojis": self.top_emojis,
            "reactions_per_hour": self.reactions_per_hour
        }


class ChatStats:
    """Статистика чата."""
    def __init__(
        self,
        total_messages: int,
        unique_authors: int,
        avg_message_length: float,
        messages_per_hour: float,
        filtered_messages: int
    ):
        self.total_messages = total_messages
        self.unique_authors = unique_authors
        self.avg_message_length = avg_message_length
        self.messages_per_hour = messages_per_hour
        self.filtered_messages = filtered_messages

    def model_dump(self) -> Dict[str, Any]:
        return {
            "total_messages": self.total_messages,
            "unique_authors": self.unique_authors,
            "avg_message_length": self.avg_message_length,
            "messages_per_hour": self.messages_per_hour,
            "filtered_messages": self.filtered_messages
        }


class EngagementSummary:
    """Сводная статистика взаимодействий."""
    def __init__(
        self,
        total_interactions: int,
        poll_participation_rate: float,
        qa_engagement_rate: float,
        reaction_intensity: float,
        chat_activity_level: float,
        most_active_users: List[Dict[str, Any]],
        peak_interaction_hour: Optional[str]
    ):
        self.total_interactions = total_interactions
        self.poll_participation_rate = poll_participation_rate
        self.qa_engagement_rate = qa_engagement_rate
        self.reaction_intensity = reaction_intensity
        self.chat_activity_level = chat_activity_level
        self.most_active_users = most_active_users
        self.peak_interaction_hour = peak_interaction_hour

    def model_dump(self) -> Dict[str, Any]:
        return {
            "total_interactions": self.total_interactions,
            "poll_participation_rate": self.poll_participation_rate,
            "qa_engagement_rate": self.qa_engagement_rate,
            "reaction_intensity": self.reaction_intensity,
            "chat_activity_level": self.chat_activity_level,
            "most_active_users": self.most_active_users,
            "peak_interaction_hour": self.peak_interaction_hour
        }


def _period_to_days(period: str) -> Optional[int]:
    """Конвертация периода в количество дней."""
    mapping = {"1h": 1/24, "24h": 1, "7d": 7, "30d": 30, "90d": 90, "all": None}
    return mapping.get(period)


class InteractionAnalyticsService:
    """
    Сервис аналитики взаимодействий с Redis кэшированием.

    Методы:
    - get_poll_stats: Статистика опросов
    - get_qa_stats: Статистика Q&A
    - get_reaction_stats: Статистика реакций
    - get_chat_stats: Статистика чата
    - get_engagement_summary: Сводная статистика взаимодействий
    """

    def __init__(self, db: Session, redis_client: Optional["aioredis.Redis"] = None):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
            redis_client: Опциональный Redis клиент для кэширования
        """
        self.db = db
        self.redis = redis_client

    async def _get_from_cache(self, key: str) -> Optional[dict]:
        """Получение данных из кэша Redis."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    async def _set_to_cache(self, key: str, data: dict, ttl: int = CACHE_TTL) -> None:
        """Сохранение данных в кэш Redis."""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    def _get_period_filter(self, period: str) -> Optional[datetime]:
        """Получение фильтра по времени для периода."""
        days = _period_to_days(period)
        if days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=days)

    async def get_poll_stats(
        self,
        period: str = "7d",
        stream_id: Optional[UUID] = None
    ) -> PollStats:
        """
        Получение статистики опросов.

        Args:
            period: Период данных (1h, 24h, 7d, 30d, 90d, all)
            stream_id: Опциональный ID стрима для фильтрации (резервировано для будущего использования)

        Returns:
            PollStats с метриками опросов
        """
        cache_key = CACHE_POLL_STATS_KEY.format(period=period, stream_id=stream_id or "all")
        cached = await self._get_from_cache(cache_key)
        if cached:
            return PollStats(**cached)

        period_start = self._get_period_filter(period)

        # Всего опросов
        poll_count_query = select(func.count(Poll.id))
        if period_start:
            poll_count_query = poll_count_query.where(Poll.created_at >= period_start)
        total_polls = self.db.execute(poll_count_query).scalar() or 0

        # Активные опросы
        active_polls_query = select(func.count(Poll.id)).where(Poll.status == PollStatus.ACTIVE)
        if period_start:
            active_polls_query = active_polls_query.where(Poll.created_at >= period_start)
        active_polls = self.db.execute(active_polls_query).scalar() or 0

        # Всего голосов
        vote_count_query = select(func.count(PollVote.id))
        if period_start:
            vote_count_query = vote_count_query.where(PollVote.voted_at >= period_start)
        total_votes = self.db.execute(vote_count_query).scalar() or 0

        # Уникальных голосователей
        unique_voters_query = select(
            func.count(func.distinct(PollVote.user_id))
        ).where(PollVote.user_id.isnot(None))
        if period_start:
            unique_voters_query = unique_voters_query.where(PollVote.voted_at >= period_start)
        registered_voters = self.db.execute(unique_voters_query).scalar() or 0

        # Уникальных anonymous voters
        anonymous_voters_query = select(
            func.count(func.distinct(PollVote.telegram_user_id))
        ).where(PollVote.telegram_user_id.isnot(None))
        if period_start:
            anonymous_voters_query = anonymous_voters_query.where(PollVote.voted_at >= period_start)
        anonymous_voter_count = self.db.execute(anonymous_voters_query).scalar() or 0

        unique_voters = registered_voters + anonymous_voter_count

        # Средний participation rate (голоса / опросы)
        avg_participation_rate = round(
            total_votes / total_polls if total_polls > 0 else 0, 2
        )

        # Самый популярный опрос
        most_voted_query = select(
            Poll.id,
            Poll.question,
            func.count(PollVote.id).label('vote_count')
        ).join(PollVote, Poll.id == PollVote.poll_id)

        if period_start:
            most_voted_query = most_voted_query.where(Poll.created_at >= period_start)

        most_voted_query = most_voted_query.group_by(Poll.id, Poll.question).order_by(desc('vote_count')).limit(1)
        most_voted_poll_result = self.db.execute(most_voted_query).first()

        most_voted_poll = None
        if most_voted_poll_result:
            most_voted_poll = {
                "id": str(most_voted_poll_result[0]),
                "question": most_voted_poll_result[1],
                "vote_count": most_voted_poll_result[2]
            }

        result = PollStats(
            total_polls=total_polls,
            active_polls=active_polls,
            total_votes=total_votes,
            unique_voters=unique_voters,
            avg_participation_rate=avg_participation_rate,
            most_voted_poll=most_voted_poll
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_qa_stats(
        self,
        period: str = "7d",
        stream_id: Optional[UUID] = None
    ) -> QAStats:
        """
        Получение статистики Q&A.

        Args:
            period: Период данных (1h, 24h, 7d, 30d, 90d, all)
            stream_id: Опциональный ID стрима для фильтрации

        Returns:
            QAStats с метриками вопросов и ответов
        """
        cache_key = CACHE_QA_STATS_KEY.format(period=period, stream_id=stream_id or "all")
        cached = await self._get_from_cache(cache_key)
        if cached:
            return QAStats(**cached)

        period_start = self._get_period_filter(period)

        # Базовый фильтр по времени
        time_filter = Question.created_at >= period_start if period_start else literal_column('1=1')

        # Всего вопросов
        total_questions = self.db.execute(
            select(func.count(Question.id)).where(time_filter)
        ).scalar() or 0

        # Ожидающие ответа
        pending_questions = self.db.execute(
            select(func.count(Question.id)).where(
                and_(time_filter, Question.status == QuestionStatus.PENDING)
            )
        ).scalar() or 0

        # Отвеченные вопросы
        answered_questions = self.db.execute(
            select(func.count(Question.id)).where(
                and_(time_filter, Question.status == QuestionStatus.ANSWERED)
            )
        ).scalar() or 0

        # Всего upvotes
        total_upvotes = self.db.execute(
            select(func.count(QuestionUpvote.id))
            .join(Question, QuestionUpvote.question_id == Question.id)
            .where(time_filter)
        ).scalar() or 0

        # Уникальных участников (registered)
        registered_participants = self.db.execute(
            select(func.count(func.distinct(Question.author_id)))
            .where(and_(time_filter, Question.author_id.isnot(None)))
        ).scalar() or 0

        # Уникальных участников (anonymous)
        anonymous_participants = self.db.execute(
            select(func.count(func.distinct(Question.telegram_user_id)))
            .where(and_(time_filter, Question.telegram_user_id.isnot(None)))
        ).scalar() or 0

        unique_participants = registered_participants + anonymous_participants

        # Среднее время ответа (в часах)
        avg_time_result = self.db.execute(
            select(func.avg(
                func.extract('epoch', Question.answered_at - Question.created_at) / 3600
            ))
            .where(
                and_(
                    time_filter,
                    Question.status == QuestionStatus.ANSWERED,
                    Question.answered_at.isnot(None)
                )
            )
        ).scalar()
        avg_answer_time_hours = round(float(avg_time_result), 2) if avg_time_result else None

        result = QAStats(
            total_questions=total_questions,
            pending_questions=pending_questions,
            answered_questions=answered_questions,
            total_upvotes=total_upvotes,
            unique_participants=unique_participants,
            avg_answer_time_hours=avg_answer_time_hours
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_reaction_stats(
        self,
        period: str = "7d",
        stream_id: Optional[UUID] = None
    ) -> ReactionStats:
        """
        Получение статистики реакций.

        Args:
            period: Период данных (1h, 24h, 7d, 30d, 90d, all)
            stream_id: Опциональный ID стрима для фильтрации

        Returns:
            ReactionStats с метриками эмодзи-реакций
        """
        cache_key = CACHE_REACTION_STATS_KEY.format(period=period, stream_id=stream_id or "all")
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ReactionStats(**cached)

        period_start = self._get_period_filter(period)

        # Базовый фильтр по времени
        time_filter = EmojiReaction.created_at >= period_start if period_start else literal_column('1=1')

        # Фильтр по стриму
        stream_filter = EmojiReaction.stream_id == stream_id if stream_id else literal_column('1=1')

        combined_filter = and_(time_filter, stream_filter)

        # Всего реакций
        total_reactions = self.db.execute(
            select(func.count(EmojiReaction.id)).where(combined_filter)
        ).scalar() or 0

        # Уникальных пользователей (registered)
        registered_users = self.db.execute(
            select(func.count(func.distinct(EmojiReaction.user_id)))
            .where(and_(combined_filter, EmojiReaction.user_id.isnot(None)))
        ).scalar() or 0

        # Уникальных пользователей (anonymous)
        anonymous_users = self.db.execute(
            select(func.count(func.distinct(EmojiReaction.telegram_user_id)))
            .where(and_(combined_filter, EmojiReaction.telegram_user_id.isnot(None)))
        ).scalar() or 0

        unique_users = registered_users + anonymous_users

        # Топ эмодзи
        top_emojis_rows = self.db.execute(
            select(
                EmojiReaction.emoji,
                func.count(EmojiReaction.id).label('count')
            )
            .where(combined_filter)
            .group_by(EmojiReaction.emoji)
            .order_by(desc('count'))
            .limit(10)
        ).fetchall()

        top_emojis = [
            {"emoji": row[0], "count": row[1]}
            for row in top_emojis_rows
        ]

        # Реакций в час
        days = _period_to_days(period)
        hours = days * 24 if days else 24  # Default to 24h if period is "all"
        reactions_per_hour = round(total_reactions / hours, 2) if hours > 0 else 0

        result = ReactionStats(
            total_reactions=total_reactions,
            unique_users=unique_users,
            top_emojis=top_emojis,
            reactions_per_hour=reactions_per_hour
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_chat_stats(
        self,
        period: str = "7d",
        stream_id: Optional[UUID] = None
    ) -> ChatStats:
        """
        Получение статистики чата.

        Args:
            period: Период данных (1h, 24h, 7d, 30d, 90d, all)
            stream_id: Опциональный ID стрима для фильтрации

        Returns:
            ChatStats с метриками чат-сообщений
        """
        cache_key = CACHE_CHAT_STATS_KEY.format(period=period, stream_id=stream_id or "all")
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ChatStats(**cached)

        period_start = self._get_period_filter(period)

        # Базовый фильтр по времени
        time_filter = ChatMessage.created_at >= period_start if period_start else literal_column('1=1')

        # Фильтр по стриму
        stream_filter = ChatMessage.stream_id == stream_id if stream_id else literal_column('1=1')

        combined_filter = and_(time_filter, stream_filter)

        # Всего сообщений
        total_messages = self.db.execute(
            select(func.count(ChatMessage.id)).where(combined_filter)
        ).scalar() or 0

        # Уникальных авторов (registered)
        registered_authors = self.db.execute(
            select(func.count(func.distinct(ChatMessage.author_id)))
            .where(and_(combined_filter, ChatMessage.author_id.isnot(None)))
        ).scalar() or 0

        # Уникальных авторов (anonymous)
        anonymous_authors = self.db.execute(
            select(func.count(func.distinct(ChatMessage.telegram_user_id)))
            .where(and_(combined_filter, ChatMessage.telegram_user_id.isnot(None)))
        ).scalar() or 0

        unique_authors = registered_authors + anonymous_authors

        # Средняя длина сообщения
        avg_length = self.db.execute(
            select(func.avg(func.length(ChatMessage.content))).where(combined_filter)
        ).scalar()
        avg_message_length = round(float(avg_length), 2) if avg_length else 0

        # Сообщений в час
        days = _period_to_days(period)
        hours = days * 24 if days else 24  # Default to 24h if period is "all"
        messages_per_hour = round(total_messages / hours, 2) if hours > 0 else 0

        # Отфильтрованные сообщения
        filtered_messages = self.db.execute(
            select(func.count(ChatMessage.id)).where(
                and_(combined_filter, ChatMessage.is_filtered == True)
            )
        ).scalar() or 0

        result = ChatStats(
            total_messages=total_messages,
            unique_authors=unique_authors,
            avg_message_length=avg_message_length,
            messages_per_hour=messages_per_hour,
            filtered_messages=filtered_messages
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def get_engagement_summary(
        self,
        period: str = "7d",
        stream_id: Optional[UUID] = None
    ) -> EngagementSummary:
        """
        Получение сводной статистики взаимодействий.

        Args:
            period: Период данных (1h, 24h, 7d, 30d, 90d, all)
            stream_id: Опциональный ID стрима для фильтрации

        Returns:
            EngagementSummary с агрегированными метриками
        """
        cache_key = CACHE_ENGAGEMENT_SUMMARY_KEY.format(period=period, stream_id=stream_id or "all")
        cached = await self._get_from_cache(cache_key)
        if cached:
            return EngagementSummary(**cached)

        # Получаем статистику по каждому типу взаимодействий
        poll_stats = await self.get_poll_stats(period, stream_id)
        qa_stats = await self.get_qa_stats(period, stream_id)
        reaction_stats = await self.get_reaction_stats(period, stream_id)
        chat_stats = await self.get_chat_stats(period, stream_id)

        # Всего взаимодействий
        total_interactions = (
            poll_stats.total_votes +
            qa_stats.total_upvotes +
            reaction_stats.total_reactions +
            chat_stats.total_messages
        )

        # Participation rates (нормализованные метрики 0-100)
        poll_participation_rate = min(poll_stats.avg_participation_rate * 10, 100)
        qa_engagement_rate = min(qa_stats.total_upvotes * 5, 100) if qa_stats.total_questions > 0 else 0
        reaction_intensity = min(reaction_stats.reactions_per_hour * 10, 100)
        chat_activity_level = min(chat_stats.messages_per_hour * 5, 100)

        # Самые активные пользователи (агрегация по всем типам взаимодействий)
        # Упрощенная версия - может быть расширена
        most_active_users = []  # TODO: Implement user aggregation

        # Пиковый час взаимодействий
        peak_interaction_hour = None  # TODO: Implement hourly aggregation

        result = EngagementSummary(
            total_interactions=total_interactions,
            poll_participation_rate=round(poll_participation_rate, 2),
            qa_engagement_rate=round(qa_engagement_rate, 2),
            reaction_intensity=round(reaction_intensity, 2),
            chat_activity_level=round(chat_activity_level, 2),
            most_active_users=most_active_users,
            peak_interaction_hour=peak_interaction_hour
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result
