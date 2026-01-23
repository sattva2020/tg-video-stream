"""
Comprehensive tests for InteractionAnalyticsService

Модуль тестирует:
- Инициализацию и Redis кэширование
- Poll статистика (get_poll_stats)
- Q&A статистика (get_qa_stats)
- Reaction статистика (get_reaction_stats)
- Chat статистика (get_chat_stats)
- Engagement summary (get_engagement_summary)
- Кэширование в Redis
- Периоды фильтрации (1h, 24h, 7d, 30d, 90d, all)

Coverage target: 70%+
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

from src.services.interaction_analytics_service import (
    InteractionAnalyticsService,
    PollStats,
    QAStats,
    ReactionStats,
    ChatStats,
    EngagementSummary,
    _period_to_days,
)
from src.models.poll import Poll, PollVote, PollStatus
from src.models.qa import Question, QuestionUpvote, QuestionStatus
from src.models.interaction import EmojiReaction, ChatMessage
from src.models.stream import Stream


# ==================== Fixtures ====================

@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session."""
    db = Mock()
    db.execute = Mock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def analytics_service(mock_db, mock_redis):
    """InteractionAnalyticsService с мокнутым db и redis."""
    return InteractionAnalyticsService(db=mock_db, redis_client=mock_redis)


# ==================== Test Classes ====================

class TestPeriodToDays:
    """Тесты конвертации периодов."""

    def test_period_to_days_1h(self):
        """Тест конвертации 1h."""
        assert _period_to_days("1h") == 1/24

    def test_period_to_days_24h(self):
        """Тест конвертации 24h."""
        assert _period_to_days("24h") == 1

    def test_period_to_days_7d(self):
        """Тест конвертации 7d."""
        assert _period_to_days("7d") == 7

    def test_period_to_days_30d(self):
        """Тест конвертации 30d."""
        assert _period_to_days("30d") == 30

    def test_period_to_days_90d(self):
        """Тест конвертации 90d."""
        assert _period_to_days("90d") == 90

    def test_period_to_days_all(self):
        """Тест конвертации all."""
        assert _period_to_days("all") is None

    def test_period_to_days_invalid(self):
        """Тест конвертации невалидного периода."""
        assert _period_to_days("invalid") is None


class TestInteractionAnalyticsInit:
    """Тесты инициализации сервиса."""

    def test_init_with_redis(self, mock_db, mock_redis):
        """Тест инициализации с Redis."""
        service = InteractionAnalyticsService(db=mock_db, redis_client=mock_redis)

        assert service.db is mock_db
        assert service.redis is mock_redis

    def test_init_without_redis(self, mock_db):
        """Тест инициализации без Redis."""
        service = InteractionAnalyticsService(db=mock_db, redis_client=None)

        assert service.db is mock_db
        assert service.redis is None


class TestAnalyticsCaching:
    """Тесты Redis кэширования."""

    @pytest.mark.asyncio
    async def test_get_from_cache_hit(self, analytics_service, mock_redis):
        """Тест попадания в кэш."""
        import json
        cached_data = {"total_polls": 10}
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        result = await analytics_service._get_from_cache("test_key")

        assert result == cached_data
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_from_cache_miss(self, analytics_service, mock_redis):
        """Тест промаха кэша."""
        mock_redis.get.return_value = None

        result = await analytics_service._get_from_cache("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_cache_error(self, analytics_service, mock_redis):
        """Тест обработки ошибки Redis."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await analytics_service._get_from_cache("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_to_cache_success(self, analytics_service, mock_redis):
        """Тест успешной записи в кэш."""
        data = {"total_polls": 10}

        await analytics_service._set_to_cache("test_key", data, ttl=60)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 60

    @pytest.mark.asyncio
    async def test_set_to_cache_no_redis(self, analytics_service):
        """Тест записи в кэш без Redis."""
        analytics_service.redis = None

        # Should not raise
        await analytics_service._set_to_cache("test_key", {"data": 1})


class TestPollStats:
    """Тесты Poll статистики."""

    @pytest.mark.asyncio
    async def test_get_poll_stats_basic(self, analytics_service, mock_db, mock_redis):
        """Тест базовой статистики опросов."""
        # Mock cache miss
        mock_redis.get.return_value = None

        # Mock DB queries
        def mock_execute_func(query):
            result = Mock()
            # Return different values for different queries
            if "count(polls.id)" in str(query).lower():
                result.scalar.return_value = 5
            elif "active" in str(query).lower():
                result.scalar.return_value = 2
            elif "poll_votes" in str(query).lower():
                if "distinct" in str(query).lower():
                    result.scalar.return_value = 10
                else:
                    result.scalar.return_value = 15
            elif "group by" in str(query).lower():
                result.first.return_value = (uuid4(), "Test Poll?", 15)
            else:
                result.scalar.return_value = 0
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_poll_stats(period="7d")

        assert isinstance(stats, PollStats)
        assert stats.total_polls == 5
        assert stats.active_polls == 2
        assert stats.total_votes == 15

    @pytest.mark.asyncio
    async def test_get_poll_stats_from_cache(self, analytics_service, mock_redis):
        """Тест получения статистики из кэша."""
        import json
        cached_data = {
            "total_polls": 10,
            "active_polls": 5,
            "total_votes": 50,
            "unique_voters": 30,
            "avg_participation_rate": 5.0,
            "most_voted_poll": None
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        stats = await analytics_service.get_poll_stats(period="7d")

        assert stats.total_polls == 10
        assert stats.active_polls == 5
        # DB should not be called
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_poll_stats_caches_result(self, analytics_service, mock_db, mock_redis):
        """Тест что результат кэшируется."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.scalar.return_value = 0
            result.first.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_func

        await analytics_service.get_poll_stats(period="24h")

        # Verify cache set was called
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_poll_stats_with_most_voted(self, analytics_service, mock_db):
        """Тест статистики с самым популярным опросом."""
        mock_redis.get.return_value = None

        poll_id = uuid4()

        def mock_execute_func(query):
            result = Mock()
            result.scalar.return_value = 0
            result.first.return_value = (poll_id, "Popular Question?", 42)
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_poll_stats(period="7d")

        assert stats.most_voted_poll is not None
        assert stats.most_voted_poll["vote_count"] == 42


class TestQAStats:
    """Тесты Q&A статистики."""

    @pytest.mark.asyncio
    async def test_get_qa_stats_basic(self, analytics_service, mock_db):
        """Тест базовой Q&A статистики."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.scalar.return_value = 10
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_qa_stats(period="7d")

        assert isinstance(stats, QAStats)
        assert stats.total_questions == 10
        assert stats.pending_questions == 10
        assert stats.answered_questions == 10
        assert stats.total_upvotes == 10
        assert stats.unique_participants == 20  # 10 + 10 from registered + anonymous

    @pytest.mark.asyncio
    async def test_get_qa_stats_from_cache(self, analytics_service, mock_redis):
        """Тест Q&A статистики из кэша."""
        import json
        cached_data = {
            "total_questions": 20,
            "pending_questions": 5,
            "answered_questions": 15,
            "total_upvotes": 50,
            "unique_participants": 30,
            "avg_answer_time_hours": 2.5
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        stats = await analytics_service.get_qa_stats(period="7d")

        assert stats.total_questions == 20
        assert stats.avg_answer_time_hours == 2.5

    @pytest.mark.asyncio
    async def test_get_qa_stats_avg_time_none(self, analytics_service, mock_db):
        """Тест среднего времени ответа (None)."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            if "avg" in str(query).lower():
                result.scalar.return_value = None
            else:
                result.scalar.return_value = 0
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_qa_stats(period="7d")

        assert stats.avg_answer_time_hours is None


class TestReactionStats:
    """Тесты Reaction статистики."""

    @pytest.mark.asyncio
    async def test_get_reaction_stats_basic(self, analytics_service, mock_db):
        """Тест базовой статистики реакций."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            if "fetchall" in str(type(query)):
                # Mock top emojis
                rows = [
                    ("😀", 10),
                    ("❤️", 8),
                    ("👍", 5)
                ]
                result.fetchall.return_value = rows
            elif "count" in str(query).lower():
                result.scalar.return_value = 23
            else:
                result.scalar.return_value = 0
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_reaction_stats(period="7d")

        assert isinstance(stats, ReactionStats)
        assert stats.total_reactions == 23
        assert len(stats.top_emojis) == 3
        assert stats.top_emojis[0]["emoji"] == "😀"
        assert stats.top_emojis[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_get_reaction_stats_per_hour(self, analytics_service, mock_db):
        """Тест расчета реакций в час."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.fetchall.return_value = []
            result.scalar.return_value = 168  # 1 week = 168 hours
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_reaction_stats(period="7d")

        assert stats.reactions_per_hour == 168.0


class TestChatStats:
    """Тесты Chat статистики."""

    @pytest.mark.asyncio
    async def test_get_chat_stats_basic(self, analytics_service, mock_db):
        """Тест базовой статистики чата."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            if "avg" in str(query).lower() and "length" in str(query).lower():
                result.scalar.return_value = 45.5
            else:
                result.scalar.return_value = 100
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_chat_stats(period="7d")

        assert isinstance(stats, ChatStats)
        assert stats.total_messages == 100
        assert stats.unique_authors == 200  # 100 + 100
        assert stats.avg_message_length == 45.5

    @pytest.mark.asyncio
    async def test_get_chat_stats_with_filtered(self, analytics_service, mock_db):
        """Тест статистики с отфильтрованными сообщениями."""
        mock_redis.get.return_value = None

        call_count = [0]

        def mock_execute_func(query):
            result = Mock()
            if "filtered" in str(query).lower():
                result.scalar.return_value = 5
            else:
                result.scalar.return_value = 100
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_chat_stats(period="7d")

        assert stats.filtered_messages == 5

    @pytest.mark.asyncio
    async def test_get_chat_stats_messages_per_hour(self, analytics_service, mock_db):
        """Тест сообщений в час."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.scalar.return_value = 168
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_chat_stats(period="7d")

        assert stats.messages_per_hour == 168.0


class TestEngagementSummary:
    """Тесты сводной статистики."""

    @pytest.mark.asyncio
    async def test_get_engagement_summary_basic(self, analytics_service, mock_redis):
        """Тест базовой сводной статистики."""
        # Cache miss for all stats
        mock_redis.get.return_value = None

        # Mock individual stats methods
        with patch.object(analytics_service, 'get_poll_stats') as mock_poll, \
             patch.object(analytics_service, 'get_qa_stats') as mock_qa, \
             patch.object(analytics_service, 'get_reaction_stats') as mock_reaction, \
             patch.object(analytics_service, 'get_chat_stats') as mock_chat:

            mock_poll.return_value = PollStats(
                total_polls=5, active_polls=2, total_votes=50,
                unique_voters=30, avg_participation_rate=10.0,
                most_voted_poll=None
            )
            mock_qa.return_value = QAStats(
                total_questions=10, pending_questions=5,
                answered_questions=5, total_upvotes=20,
                unique_participants=15, avg_answer_time_hours=1.5
            )
            mock_reaction.return_value = ReactionStats(
                total_reactions=100, unique_users=50,
                top_emojis=[], reactions_per_hour=10.0
            )
            mock_chat.return_value = ChatStats(
                total_messages=200, unique_authors=80,
                avg_message_length=45.0, messages_per_hour=20.0,
                filtered_messages=2
            )

            summary = await analytics_service.get_engagement_summary(period="7d")

            assert isinstance(summary, EngagementSummary)
            assert summary.total_interactions == 370  # 50 + 20 + 100 + 200
            assert summary.poll_participation_rate == 100.0  # min(10.0 * 10, 100)
            assert summary.qa_engagement_rate == 100.0  # min(20 * 5, 100)
            assert summary.reaction_intensity == 100.0  # min(10.0 * 10, 100)
            assert summary.chat_activity_level == 100.0  # min(20.0 * 5, 100)

    @pytest.mark.asyncio
    async def test_get_engagement_summary_from_cache(self, analytics_service, mock_redis):
        """Тест сводной статистики из кэша."""
        import json
        cached_data = {
            "total_interactions": 500,
            "poll_participation_rate": 75.5,
            "qa_engagement_rate": 60.0,
            "reaction_intensity": 80.0,
            "chat_activity_level": 90.0,
            "most_active_users": [],
            "peak_interaction_hour": None
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        summary = await analytics_service.get_engagement_summary(period="7d")

        assert summary.total_interactions == 500
        assert summary.poll_participation_rate == 75.5

    @pytest.mark.asyncio
    async def test_get_engagement_summary_normalizes_metrics(self, analytics_service, mock_redis):
        """Тест нормализации метрик (0-100)."""
        mock_redis.get.return_value = None

        with patch.object(analytics_service, 'get_poll_stats') as mock_poll, \
             patch.object(analytics_service, 'get_qa_stats') as mock_qa, \
             patch.object(analytics_service, 'get_reaction_stats') as mock_reaction, \
             patch.object(analytics_service, 'get_chat_stats') as mock_chat:

            # Low engagement values
            mock_poll.return_value = PollStats(
                total_polls=5, active_polls=2, total_votes=2,
                unique_voters=2, avg_participation_rate=0.4,
                most_voted_poll=None
            )
            mock_qa.return_value = QAStats(
                total_questions=10, pending_questions=10,
                answered_questions=0, total_upvotes=1,
                unique_participants=5, avg_answer_time_hours=None
            )
            mock_reaction.return_value = ReactionStats(
                total_reactions=5, unique_users=5,
                top_emojis=[], reactions_per_hour=0.5
            )
            mock_chat.return_value = ChatStats(
                total_messages=10, unique_authors=8,
                avg_message_length=30.0, messages_per_hour=1.0,
                filtered_messages=0
            )

            summary = await analytics_service.get_engagement_summary(period="7d")

            # Should be normalized to 0-100 range
            assert 0 <= summary.poll_participation_rate <= 100
            assert 0 <= summary.qa_engagement_rate <= 100
            assert 0 <= summary.reaction_intensity <= 100
            assert 0 <= summary.chat_activity_level <= 100


class TestPeriodFilter:
    """Тесты фильтрации по периоду."""

    @pytest.mark.asyncio
    async def test_get_period_filter_7d(self, analytics_service):
        """Тест фильтра за 7 дней."""
        filter_dt = analytics_service._get_period_filter("7d")

        assert filter_dt is not None
        expected = datetime.now(timezone.utc) - timedelta(days=7)
        # Allow 1 second tolerance
        assert abs((filter_dt - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_get_period_filter_all(self, analytics_service):
        """Тест фильтра за все время."""
        filter_dt = analytics_service._get_period_filter("all")

        assert filter_dt is None


class TestDataClasses:
    """Тесты data classes."""

    def test_poll_stats_model_dump(self):
        """Тест PollStats.model_dump()."""
        stats = PollStats(
            total_polls=10,
            active_polls=5,
            total_votes=50,
            unique_voters=30,
            avg_participation_rate=5.0,
            most_voted_poll={"id": "123", "question": "Test", "vote_count": 25}
        )

        data = stats.model_dump()

        assert data["total_polls"] == 10
        assert data["active_polls"] == 5
        assert data["most_voted_poll"]["question"] == "Test"

    def test_qa_stats_model_dump(self):
        """Тест QAStats.model_dump()."""
        stats = QAStats(
            total_questions=20,
            pending_questions=5,
            answered_questions=15,
            total_upvotes=50,
            unique_participants=30,
            avg_answer_time_hours=2.5
        )

        data = stats.model_dump()

        assert data["total_questions"] == 20
        assert data["avg_answer_time_hours"] == 2.5

    def test_reaction_stats_model_dump(self):
        """Тест ReactionStats.model_dump()."""
        stats = ReactionStats(
            total_reactions=100,
            unique_users=50,
            top_emojis=[{"emoji": "😀", "count": 10}],
            reactions_per_hour=10.0
        )

        data = stats.model_dump()

        assert data["total_reactions"] == 100
        assert len(data["top_emojis"]) == 1

    def test_chat_stats_model_dump(self):
        """Тест ChatStats.model_dump()."""
        stats = ChatStats(
            total_messages=200,
            unique_authors=80,
            avg_message_length=45.0,
            messages_per_hour=20.0,
            filtered_messages=2
        )

        data = stats.model_dump()

        assert data["total_messages"] == 200
        assert data["filtered_messages"] == 2

    def test_engagement_summary_model_dump(self):
        """Тест EngagementSummary.model_dump()."""
        summary = EngagementSummary(
            total_interactions=500,
            poll_participation_rate=75.5,
            qa_engagement_rate=60.0,
            reaction_intensity=80.0,
            chat_activity_level=90.0,
            most_active_users=[],
            peak_interaction_hour="18:00"
        )

        data = summary.model_dump()

        assert data["total_interactions"] == 500
        assert data["peak_interaction_hour"] == "18:00"


class TestEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_poll_stats_zero_division(self, analytics_service, mock_db):
        """Тест деления на ноль (нет опросов)."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.scalar.return_value = 0  # No polls
            result.first.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_poll_stats(period="7d")

        # Should handle division by zero
        assert stats.avg_participation_rate == 0

    @pytest.mark.asyncio
    async def test_chat_stats_avg_length_zero(self, analytics_service, mock_db):
        """Тест средней длины сообщения (None)."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            if "avg" in str(query).lower() and "length" in str(query).lower():
                result.scalar.return_value = None
            else:
                result.scalar.return_value = 0
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_chat_stats(period="7d")

        assert stats.avg_message_length == 0

    @pytest.mark.asyncio
    async def test_reaction_stats_zero_hours(self, analytics_service, mock_db):
        """Тест реакций в час при period='all'."""
        mock_redis.get.return_value = None

        def mock_execute_func(query):
            result = Mock()
            result.fetchall.return_value = []
            result.scalar.return_value = 0
            return result

        mock_db.execute.side_effect = mock_execute_func

        stats = await analytics_service.get_reaction_stats(period="all")

        # Should default to 24h period
        assert stats.reactions_per_hour >= 0

    @pytest.mark.asyncio
    async def test_engagement_summary_zero_questions(self, analytics_service, mock_redis):
        """Тест сводной статистики без вопросов."""
        mock_redis.get.return_value = None

        with patch.object(analytics_service, 'get_poll_stats') as mock_poll, \
             patch.object(analytics_service, 'get_qa_stats') as mock_qa, \
             patch.object(analytics_service, 'get_reaction_stats') as mock_reaction, \
             patch.object(analytics_service, 'get_chat_stats') as mock_chat:

            # Zero questions
            mock_qa.return_value = QAStats(
                total_questions=0, pending_questions=0,
                answered_questions=0, total_upvotes=0,
                unique_participants=0, avg_answer_time_hours=None
            )
            mock_poll.return_value = PollStats(
                total_polls=0, active_polls=0, total_votes=0,
                unique_voters=0, avg_participation_rate=0,
                most_voted_poll=None
            )
            mock_reaction.return_value = ReactionStats(
                total_reactions=0, unique_users=0,
                top_emojis=[], reactions_per_hour=0
            )
            mock_chat.return_value = ChatStats(
                total_messages=0, unique_authors=0,
                avg_message_length=0, messages_per_hour=0,
                filtered_messages=0
            )

            summary = await analytics_service.get_engagement_summary(period="7d")

            assert summary.total_interactions == 0
            assert summary.qa_engagement_rate == 0
