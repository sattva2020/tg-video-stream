"""
Comprehensive tests for PollService

Модуль тестирует:
- Инициализацию и PostgreSQL соединение
- CRUD операции (create, get_by_id, get_by_stream, get_active_by_chat, get_by_user, delete)
- Lifecycle операции (publish, close)
- Voting операции (vote, get_results)
- Utility операции (is_active)
- Обработку ошибок (PollNotFoundError, PollClosedError, DuplicateVoteError, InvalidOptionsError)
- Граничные случаи и edge cases

Coverage target: 70%+
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.services.poll_service import (
    PollService,
    PollServiceError,
    PollNotFoundError,
    PollClosedError,
    DuplicateVoteError,
    InvalidOptionsError,
)
from src.domain.entities.poll import Poll, PollOption, PollStatus
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId


# ==================== Fixtures ====================

@pytest.fixture
def mock_session():
    """Mock SQLAlchemy async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_repository():
    """Mock Poll repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_stream_id = AsyncMock(return_value=[])
    repo.get_active_by_chat = AsyncMock(return_value=[])
    repo.get_by_user = AsyncMock(return_value=[])
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def poll_service(mock_session, mock_repository):
    """PollService с мокнутым repository и session."""
    service = PollService(session=mock_session)
    service._repository = mock_repository
    return service


@pytest.fixture
def sample_poll():
    """Пример Poll entity для тестов."""
    poll_id = str(uuid4())
    options = [
        PollOption(id=str(uuid4()), option_text="Option 1", vote_count=5),
        PollOption(id=str(uuid4()), option_text="Option 2", vote_count=3),
        PollOption(id=str(uuid4()), option_text="Option 3", vote_count=2),
    ]

    poll = Poll(
        id=poll_id,
        stream_id=str(uuid4()),
        chat_id=ChatId(value=123),
        created_by=UserId(value=uuid4()),
        question="Test Question?",
        options=options,
        allow_multiple_votes=False,
        status=PollStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc)
    )
    return poll


@pytest.fixture
def sample_draft_poll():
    """Пример Poll в статусе DRAFT."""
    poll_id = str(uuid4())
    options = [
        PollOption(id=str(uuid4()), option_text="Yes", vote_count=0),
        PollOption(id=str(uuid4()), option_text="No", vote_count=0),
    ]

    poll = Poll(
        id=poll_id,
        stream_id=str(uuid4()),
        chat_id=ChatId(value=456),
        created_by=UserId(value=uuid4()),
        question="Draft Question?",
        options=options,
        allow_multiple_votes=False,
        status=PollStatus.DRAFT,
        created_at=datetime.now(timezone.utc)
    )
    return poll


# ==================== Test Classes ====================

class TestPollServiceInit:
    """Тесты инициализации PollService."""

    def test_init_with_session(self, mock_session):
        """Тест инициализации с сессией."""
        with patch("src.services.poll_service.SqlAlchemyPollRepository") as mock_repo_class:
            mock_repo_class.return_value = AsyncMock()

            service = PollService(session=mock_session)

            assert service._session is mock_session
            mock_repo_class.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_repository_initialization(self, mock_session):
        """Тест что repository создается корректно."""
        with patch("src.services.poll_service.SqlAlchemyPollRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            service = PollService(session=mock_session)

            assert service._repository is mock_repo


class TestPollServiceCreate:
    """Тесты создания опросов."""

    @pytest.mark.asyncio
    async def test_create_poll_success(self, poll_service, mock_repository, mock_session):
        """Т успешного создания опроса."""
        stream_id = str(uuid4())
        created_by = str(uuid4())
        question = "What is your favorite color?"
        options = ["Red", "Blue", "Green"]

        poll_service._repository.save = AsyncMock()

        poll = await poll_service.create(
            stream_id=stream_id,
            chat_id=123,
            created_by=created_by,
            question=question,
            options=options,
            allow_multiple_votes=False
        )

        assert isinstance(poll, Poll)
        assert poll.question == question
        assert poll.status == PollStatus.DRAFT
        assert len(poll.options) == 3
        assert poll.allow_multiple_votes is False

        mock_repository.save.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_poll_with_multiple_choice(self, poll_service, mock_repository, mock_session):
        """Тест создания опроса с множественным выбором."""
        stream_id = str(uuid4())
        created_by = str(uuid4())
        question = "Select all that apply"
        options = ["Option A", "Option B", "Option C", "Option D"]

        poll_service._repository.save = AsyncMock()

        poll = await poll_service.create(
            stream_id=stream_id,
            chat_id=456,
            created_by=created_by,
            question=question,
            options=options,
            allow_multiple_votes=True,
            description="Choose multiple options"
        )

        assert poll.allow_multiple_votes is True
        assert len(poll.options) == 4

    @pytest.mark.asyncio
    async def test_create_poll_invalid_options_empty(self, poll_service):
        """Тест ошибки при пустом списке вариантов."""
        with pytest.raises(InvalidOptionsError) as exc_info:
            await poll_service.create(
                stream_id=str(uuid4()),
                chat_id=123,
                created_by=str(uuid4()),
                question="Test?",
                options=[]
            )

        assert "минимум 2 варианта" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_poll_invalid_options_single(self, poll_service):
        """Тест ошибки при одном варианте."""
        with pytest.raises(InvalidOptionsError) as exc_info:
            await poll_service.create(
                stream_id=str(uuid4()),
                chat_id=123,
                created_by=str(uuid4()),
                question="Test?",
                options=["Only option"]
            )

        assert "минимум 2 варианта" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_poll_with_description(self, poll_service, mock_repository):
        """Тест создания опроса с описанием."""
        poll_service._repository.save = AsyncMock()

        poll = await poll_service.create(
            stream_id=str(uuid4()),
            chat_id=123,
            created_by=str(uuid4()),
            question="Main Question",
            options=["Yes", "No"],
            description="Additional context for the poll"
        )

        # Description is stored but not directly exposed in entity
        mock_repository.save.assert_called_once()


class TestPollServiceGet:
    """Тесты получения опросов."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, poll_service, mock_repository, sample_poll):
        """Тест получения опроса по ID."""
        mock_repository.get_by_id.return_value = sample_poll

        poll = await poll_service.get_by_id(sample_poll.id)

        assert poll is sample_poll
        mock_repository.get_by_id.assert_called_once_with(sample_poll.id)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, poll_service, mock_repository):
        """Тест получения несуществующего опроса."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PollNotFoundError) as exc_info:
            await poll_service.get_by_id("nonexistent-id")

        assert "не найден" in str(exc_info.value)
        mock_repository.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_stream(self, poll_service, mock_repository, sample_poll):
        """Тест получения опросов по stream_id."""
        stream_id = str(uuid4())
        mock_repository.get_by_stream_id.return_value = [sample_poll]

        polls = await poll_service.get_by_stream(stream_id)

        assert isinstance(polls, list)
        assert len(polls) >= 0
        mock_repository.get_by_stream_id.assert_called_once_with(stream_id)

    @pytest.mark.asyncio
    async def test_get_active_by_chat(self, poll_service, mock_repository, sample_poll):
        """Тест получения активных опросов по chat_id."""
        chat_id = 123
        target_chat_id = ChatId(value=chat_id)
        mock_repository.get_active_by_chat.return_value = [sample_poll]

        polls = await poll_service.get_active_by_chat(chat_id)

        assert isinstance(polls, list)
        mock_repository.get_active_by_chat.assert_called_once_with(target_chat_id)

    @pytest.mark.asyncio
    async def test_get_by_user(self, poll_service, mock_repository, sample_poll):
        """Тест получения опросов по user_id."""
        user_id = str(uuid4())
        owner_id = UserId(value=UUID(user_id))
        mock_repository.get_by_user.return_value = [sample_poll]

        polls = await poll_service.get_by_user(user_id)

        assert isinstance(polls, list)
        mock_repository.get_by_user.assert_called_once_with(owner_id)


class TestPollServiceLifecycle:
    """Тесты lifecycle операций (publish, close)."""

    @pytest.mark.asyncio
    async def test_publish_poll_success(self, poll_service, mock_repository, sample_draft_poll, mock_session):
        """Тест успешной публикации опроса."""
        mock_repository.get_by_id.return_value = sample_draft_poll
        mock_repository.save = AsyncMock()

        # Mock WebSocket notification
        with patch("src.services.poll_service.notify_poll_created", new_callable=AsyncMock) as mock_notify:
            poll = await poll_service.publish(sample_draft_poll.id)

            assert poll.status == PollStatus.ACTIVE
            assert poll.published_at is not None
            mock_repository.save.assert_called_once_with(sample_draft_poll)
            mock_session.commit.assert_called_once()
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_poll_not_found(self, poll_service, mock_repository):
        """Тест публикации несуществующего опроса."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PollNotFoundError):
            await poll_service.publish("nonexistent-id")

    @pytest.mark.asyncio
    async def test_close_poll_success(self, poll_service, mock_repository, sample_poll, mock_session):
        """Тест успешного закрытия опроса."""
        mock_repository.get_by_id.return_value = sample_poll
        mock_repository.save = AsyncMock()

        # Mock WebSocket notification
        with patch("src.services.poll_service.notify_poll_updated", new_callable=AsyncMock) as mock_notify:
            poll = await poll_service.close(sample_poll.id)

            assert poll.status == PollStatus.CLOSED
            assert poll.closed_at is not None
            mock_repository.save.assert_called_once_with(sample_poll)
            mock_session.commit.assert_called_once()
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_poll_not_found(self, poll_service, mock_repository):
        """Тест закрытия несуществующего опроса."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PollNotFoundError):
            await poll_service.close("nonexistent-id")


class TestPollServiceVoting:
    """Тесты голосования."""

    @pytest.mark.asyncio
    async def test_vote_single_choice_success(self, poll_service, mock_repository, sample_poll, mock_session):
        """Т успешного голосования (single choice)."""
        mock_repository.get_by_id.return_value = sample_poll
        mock_repository.save = AsyncMock()

        option_id = sample_poll.options[0].id
        user_id = str(uuid4())

        with patch("src.services.poll_service.notify_vote_cast", new_callable=AsyncMock) as mock_notify:
            poll = await poll_service.vote(
                poll_id=sample_poll.id,
                user_id=user_id,
                option_ids=[option_id],
                is_anonymous=True
            )

            assert poll.status == PollStatus.ACTIVE
            mock_repository.save.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_multiple_choice_success(self, poll_service, mock_repository, mock_session):
        """Т успешного голосования (multiple choice)."""
        # Create poll with allow_multiple_votes=True
        poll_id = str(uuid4())
        options = [
            PollOption(id=str(uuid4()), option_text="A", vote_count=0),
            PollOption(id=str(uuid4()), option_text="B", vote_count=0),
        ]
        poll = Poll(
            id=poll_id,
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="Multiple?",
            options=options,
            allow_multiple_votes=True,
            status=PollStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc)
        )

        poll_service._repository.get_by_id.return_value = poll
        poll_service._repository.save = AsyncMock()

        option_ids = [opt.id for opt in options]
        user_id = str(uuid4())

        with patch("src.services.poll_service.notify_vote_cast", new_callable=AsyncMock):
            result_poll = await poll_service.vote(
                poll_id=poll.id,
                user_id=user_id,
                option_ids=option_ids,
                is_anonymous=True
            )

            assert result_poll.id == poll_id

    @pytest.mark.asyncio
    async def test_vote_closed_poll_raises_error(self, poll_service, mock_repository):
        """Тест голосования в закрытый опрос."""
        closed_poll = Poll(
            id=str(uuid4()),
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="Closed?",
            options=[PollOption(id=str(uuid4()), option_text="X", vote_count=0)],
            allow_multiple_votes=False,
            status=PollStatus.CLOSED,
            created_at=datetime.now(timezone.utc)
        )

        mock_repository.get_by_id.return_value = closed_poll

        with pytest.raises(PollClosedError) as exc_info:
            await poll_service.vote(
                poll_id=closed_poll.id,
                user_id=str(uuid4()),
                option_ids=[closed_poll.options[0].id]
            )

        assert "не активен" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_vote_empty_options_raises_error(self, poll_service, mock_repository, sample_poll):
        """Тест голосования без выбора вариантов."""
        mock_repository.get_by_id.return_value = sample_poll

        with pytest.raises(InvalidOptionsError) as exc_info:
            await poll_service.vote(
                poll_id=sample_poll.id,
                user_id=str(uuid4()),
                option_ids=[]
            )

        assert "Не выбран ни один вариант" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_vote_multiple_on_single_choice_raises_error(self, poll_service, mock_repository, sample_poll):
        """Тест выбора нескольких вариантов в single choice опросе."""
        mock_repository.get_by_id.return_value = sample_poll

        with pytest.raises(InvalidOptionsError) as exc_info:
            await poll_service.vote(
                poll_id=sample_poll.id,
                user_id=str(uuid4()),
                option_ids=[sample_poll.options[0].id, sample_poll.options[1].id]
            )

        assert "не поддерживает multiple choice" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_vote_invalid_option_raises_error(self, poll_service, mock_repository, sample_poll):
        """Тест голосования за несуществующий вариант."""
        mock_repository.get_by_id.return_value = sample_poll

        with pytest.raises(InvalidOptionsError) as exc_info:
            await poll_service.vote(
                poll_id=sample_poll.id,
                user_id=str(uuid4()),
                option_ids=[str(uuid4())]  # Non-existent option
            )

        assert "не найден в опросе" in str(exc_info.value)


class TestPollServiceResults:
    """Тесты получения результатов."""

    @pytest.mark.asyncio
    async def test_get_results_success(self, poll_service, mock_repository, sample_poll):
        """Тест успешного получения результатов."""
        mock_repository.get_by_id.return_value = sample_poll

        results = await poll_service.get_results(sample_poll.id)

        assert isinstance(results, dict)
        assert "poll_id" in results
        assert "question" in results
        assert "total_votes" in results
        assert "options" in results
        assert "status" in results
        assert results["poll_id"] == sample_poll.id
        assert results["question"] == sample_poll.question
        assert len(results["options"]) == 3

    @pytest.mark.asyncio
    async def test_get_results_percentages(self, poll_service, mock_repository):
        """Тест расчета процентов в результатах."""
        poll_id = str(uuid4())
        options = [
            PollOption(id=str(uuid4()), option_text="A", vote_count=10),
            PollOption(id=str(uuid4()), option_text="B", vote_count=20),
            PollOption(id=str(uuid4()), option_text="C", vote_count=20),
        ]
        poll = Poll(
            id=poll_id,
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="Percentage test?",
            options=options,
            allow_multiple_votes=False,
            status=PollStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )

        mock_repository.get_by_id.return_value = poll

        results = await poll_service.get_results(poll_id)

        # Total: 50 votes, A=20%, B=40%, C=40%
        assert results["total_votes"] == 50
        option_results = {opt["id"]: opt for opt in results["options"]}

        assert option_results[options[0].id]["vote_count"] == 10
        assert option_results[options[0].id]["percentage"] == 20.0
        assert option_results[options[1].id]["percentage"] == 40.0
        assert option_results[options[2].id]["percentage"] == 40.0

    @pytest.mark.asyncio
    async def test_get_results_no_votes(self, poll_service, mock_repository):
        """Тест результатов опроса без голосов."""
        poll_id = str(uuid4())
        options = [
            PollOption(id=str(uuid4()), option_text="A", vote_count=0),
            PollOption(id=str(uuid4()), option_text="B", vote_count=0),
        ]
        poll = Poll(
            id=poll_id,
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="No votes?",
            options=options,
            allow_multiple_votes=False,
            status=PollStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )

        mock_repository.get_by_id.return_value = poll

        results = await poll_service.get_results(poll_id)

        assert results["total_votes"] == 0
        for opt in results["options"]:
            assert opt["vote_count"] == 0
            assert opt["percentage"] == 0


class TestPollServiceUtility:
    """Тесты utility операций."""

    @pytest.mark.asyncio
    async def test_is_active_true(self, poll_service, mock_repository, sample_poll):
        """Тест проверки активного опроса."""
        mock_repository.get_by_id.return_value = sample_poll

        assert await poll_service.is_active(sample_poll.id) is True

    @pytest.mark.asyncio
    async def test_is_active_false_closed(self, poll_service, mock_repository):
        """Тест проверки закрытого опроса."""
        closed_poll = Poll(
            id=str(uuid4()),
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="Closed?",
            options=[PollOption(id=str(uuid4()), option_text="X", vote_count=0)],
            allow_multiple_votes=False,
            status=PollStatus.CLOSED,
            created_at=datetime.now(timezone.utc)
        )

        mock_repository.get_by_id.return_value = closed_poll

        assert await poll_service.is_active(closed_poll.id) is False

    @pytest.mark.asyncio
    async def test_is_active_false_not_found(self, poll_service, mock_repository):
        """Тест проверки несуществующего опроса."""
        mock_repository.get_by_id.return_value = None

        assert await poll_service.is_active("nonexistent") is False

    @pytest.mark.asyncio
    async def test_delete_poll_success(self, poll_service, mock_repository, mock_session):
        """Тест успешного удаления опроса."""
        poll_id = str(uuid4())
        mock_repository.get_by_id.return_value = sample_poll  # Mock exists
        mock_repository.delete = AsyncMock()

        await poll_service.delete(poll_id)

        mock_repository.delete.assert_called_once_with(poll_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_poll_not_found(self, poll_service, mock_repository):
        """Тест удаления несуществующего опроса."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(PollNotFoundError):
            await poll_service.delete("nonexistent-id")


class TestPollServiceEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_vote_on_draft_poll(self, poll_service, mock_repository):
        """Тест голосования в черновике (неактивный)."""
        draft_poll = Poll(
            id=str(uuid4()),
            stream_id=str(uuid4()),
            chat_id=ChatId(value=123),
            created_by=UserId(value=uuid4()),
            question="Draft?",
            options=[PollOption(id=str(uuid4()), option_text="X", vote_count=0)],
            allow_multiple_votes=False,
            status=PollStatus.DRAFT,
            created_at=datetime.now(timezone.utc)
        )

        mock_repository.get_by_id.return_value = draft_poll

        with pytest.raises(PollClosedError):
            await poll_service.vote(
                poll_id=draft_poll.id,
                user_id=str(uuid4()),
                option_ids=[draft_poll.options[0].id]
            )

    @pytest.mark.asyncio
    async def test_get_results_with_timestamps(self, poll_service, mock_repository, sample_poll):
        """Тест что результаты включают временные метки."""
        mock_repository.get_by_id.return_value = sample_poll

        results = await poll_service.get_results(sample_poll.id)

        assert "created_at" in results
        assert "published_at" in results
        assert "closed_at" in results
        # ISO format strings
        assert isinstance(results["created_at"], str)

    @pytest.mark.asyncio
    async def test_create_many_options(self, poll_service, mock_repository):
        """Тест создания опроса с большим количеством вариантов."""
        poll_service._repository.save = AsyncMock()

        options = [f"Option {i}" for i in range(10)]
        poll = await poll_service.create(
            stream_id=str(uuid4()),
            chat_id=123,
            created_by=str(uuid4()),
            question="Choose one",
            options=options
        )

        assert len(poll.options) == 10


class TestPollServiceNotifications:
    """Тесты WebSocket уведомлений."""

    @pytest.mark.asyncio
    async def test_publish_sends_notification(self, poll_service, mock_repository, sample_draft_poll, mock_session):
        """Тест что publish отправляет уведомление."""
        mock_repository.get_by_id.return_value = sample_draft_poll
        mock_repository.save = AsyncMock()

        with patch("src.services.poll_service.notify_poll_created", new_callable=AsyncMock) as mock_notify:
            await poll_service.publish(sample_draft_poll.id)

            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[0][0] == sample_draft_poll

    @pytest.mark.asyncio
    async def test_vote_sends_notification(self, poll_service, mock_repository, sample_poll, mock_session):
        """Тест что vote отправляет уведомление."""
        mock_repository.get_by_id.return_value = sample_poll
        mock_repository.save = AsyncMock()

        with patch("src.services.poll_service.notify_vote_cast", new_callable=AsyncMock) as mock_notify:
            option_id = sample_poll.options[0].id
            await poll_service.vote(
                poll_id=sample_poll.id,
                user_id=str(uuid4()),
                option_ids=[option_id]
            )

            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[1]["poll_id"] == sample_poll.id
            assert call_args[1]["option_id"] == option_id
