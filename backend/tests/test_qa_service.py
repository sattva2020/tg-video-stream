"""
Comprehensive tests for QAService

Модуль тестирует:
- Инициализацию и PostgreSQL соединение
- Question CRUD операции (create_question, get_question, get_questions_by_stream, delete_question)
- Moderation операции (approve_question, reject_question, filter_question, mark_as_answered)
- Upvote/Downvote операции (upvote_question, downvote_question, has_user_voted)
- Statistics операции (get_question_stats)
- Обработку ошибок (QuestionNotFoundError, DuplicateVoteError, InvalidStatusTransitionError, EmptyQuestionError)
- Граничные случаи и edge cases

Coverage target: 70%+
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from src.services.qa_service import (
    QAService,
    QAServiceError,
    QuestionNotFoundError,
    DuplicateVoteError,
    InvalidStatusTransitionError,
    EmptyQuestionError,
)
from src.models.qa import Question, QuestionUpvote, QuestionStatus


# ==================== Fixtures ====================

@pytest.fixture
def mock_session():
    """Mock SQLAlchemy async session."""
    session = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def qa_service(mock_session):
    """QAService с мокнутой session."""
    return QAService(session=mock_session)


@pytest.fixture
def sample_question():
    """Пример Question для тестов."""
    return Question(
        id=str(uuid4()),
        stream_id=str(uuid4()),
        author_id=str(uuid4()),
        telegram_user_id=None,
        author_name="Test User",
        content="What is the meaning of life?",
        status=QuestionStatus.PENDING,
        is_pinned=False,
        upvote_count=5,
        is_filtered=False,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_upvote():
    """Пример QuestionUpvote для тестов."""
    return QuestionUpvote(
        id=str(uuid4()),
        question_id=str(uuid4()),
        user_id=str(uuid4()),
        telegram_user_id=None,
        created_at=datetime.now(timezone.utc)
    )


# ==================== Test Classes ====================

class TestQAServiceInit:
    """Тесты инициализации QAService."""

    def test_init_with_session(self, mock_session):
        """Тест инициализации с сессией."""
        service = QAService(session=mock_session)

        assert service._session is mock_session
        assert service._owned_session is False

    def test_init_without_session(self):
        """Тест инициализации без сессии (lazy init)."""
        service = QAService(session=None)

        assert service._session is None
        assert service._owned_session is True

    @pytest.mark.asyncio
    async def test_get_session_lazy(self):
        """Тест ленивой инициализации сессии."""
        with patch("src.services.qa_service.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value = mock_session

            service = QAService(session=None)
            session = await service._get_session()

            assert session is mock_session
            mock_get_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        """Тест закрытия owned сессии."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        service = QAService(session=None)
        service._session = mock_session

        await service.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_non_owned_session(self, mock_session):
        """Тест что non-owned сессия не закрывается."""
        service = QAService(session=mock_session)

        await service.close()

        mock_session.close.assert_not_called()


class TestQAServiceCreateQuestion:
    """Тесты создания вопросов."""

    @pytest.mark.asyncio
    async def test_create_question_success(self, qa_service, mock_session):
        """Тест успешного создания вопроса."""
        stream_id = str(uuid4())
        content = "How does this work?"

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        question = await qa_service.create_question(
            stream_id=stream_id,
            content=content,
            author_id=str(uuid4()),
            author_name="Curious User"
        )

        assert isinstance(question, Question)
        assert question.content == content
        assert question.stream_id == stream_id
        assert question.status == QuestionStatus.PENDING
        assert question.upvote_count == 0

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_question_anonymous(self, qa_service, mock_session):
        """Тест создания анонимного вопроса."""
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        question = await qa_service.create_question(
            stream_id=str(uuid4()),
            content="Anonymous question",
            telegram_user_id=123456,
            author_name="Anonymous"
        )

        assert question.telegram_user_id == 123456
        assert question.author_id is None

    @pytest.mark.asyncio
    async def test_create_question_empty_raises_error(self, qa_service):
        """Тест ошибки при пустом содержимом."""
        with pytest.raises(EmptyQuestionError) as exc_info:
            await qa_service.create_question(
                stream_id=str(uuid4()),
                content=""
            )

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_question_whitespace_raises_error(self, qa_service):
        """Тест ошибки при пробелах вместо содержимого."""
        with pytest.raises(EmptyQuestionError):
            await qa_service.create_question(
                stream_id=str(uuid4()),
                content="   \n\t   "
            )

    @pytest.mark.asyncio
    async def test_create_question_trims_content(self, qa_service, mock_session):
        """Тест что пробелы обрезаются."""
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        question = await qa_service.create_question(
            stream_id=str(uuid4()),
            content="  Test question  "
        )

        assert question.content == "Test question"


class TestQAServiceGetQuestion:
    """Тесты получения вопросов."""

    @pytest.mark.asyncio
    async def test_get_question_found(self, qa_service, mock_session, sample_question):
        """Тест получения существующего вопроса."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_question
        mock_session.execute.return_value = mock_result

        question = await qa_service.get_question(sample_question.id)

        assert question is sample_question
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_question_not_found(self, qa_service, mock_session):
        """Тест получения несуществующего вопроса."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        question = await qa_service.get_question("nonexistent-id")

        assert question is None

    @pytest.mark.asyncio
    async def test_get_questions_by_stream(self, qa_service, mock_session, sample_question):
        """Тест получения вопросов по stream_id."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_question]
        mock_session.execute.return_value = mock_result

        questions = await qa_service.get_questions_by_stream(
            stream_id=sample_question.stream_id,
            status=QuestionStatus.PENDING,
            limit=50
        )

        assert isinstance(questions, list)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_questions_with_pagination(self, qa_service, mock_session):
        """Тест пагинации вопросов."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await qa_service.get_questions_by_stream(
            stream_id=str(uuid4()),
            limit=10,
            offset=20
        )

        # Verify query execution
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_questions(self, qa_service, mock_session):
        """Тест получения ожидающих вопросов."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        questions = await qa_service.get_pending_questions(stream_id=str(uuid4()))

        assert isinstance(questions, list)

    @pytest.mark.asyncio
    async def test_get_answered_questions(self, qa_service, mock_session):
        """Тест получения отвеченных вопросов."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        questions = await qa_service.get_answered_questions(stream_id=str(uuid4()))

        assert isinstance(questions, list)


class TestQAServiceModeration:
    """Тесты модерации вопросов."""

    @pytest.mark.asyncio
    async def test_approve_question_success(self, qa_service, mock_session, sample_question):
        """Тест успешного одобрения вопроса."""
        # Mock get_question call
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            await qa_service.approve_question(sample_question.id)

            assert sample_question.status == QuestionStatus.PINNED
            assert sample_question.is_pinned is True
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_question_not_found(self, qa_service, mock_session):
        """Тест одобрения несуществующего вопроса."""
        with patch.object(qa_service, 'get_question', return_value=None):
            with pytest.raises(QuestionNotFoundError):
                await qa_service.approve_question("nonexistent-id")

    @pytest.mark.asyncio
    async def test_approve_invalid_status(self, qa_service, mock_session, sample_question):
        """Тест одобрения вопроса с некорректным статусом."""
        sample_question.status = QuestionStatus.ANSWERED

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            with pytest.raises(InvalidStatusTransitionError):
                await qa_service.approve_question(sample_question.id)

    @pytest.mark.asyncio
    async def test_reject_question_success(self, qa_service, mock_session, sample_question):
        """Тест успешного отклонения вопроса."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            await qa_service.reject_question(
                sample_question.id,
                reason="Inappropriate content"
            )

            assert sample_question.status == QuestionStatus.REJECTED
            assert sample_question.filter_reason == "Inappropriate content"

    @pytest.mark.asyncio
    async def test_reject_already_answered(self, qa_service, mock_session, sample_question):
        """Тест отклонения уже отвеченного вопроса."""
        sample_question.status = QuestionStatus.ANSWERED

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            with pytest.raises(InvalidStatusTransitionError) as exc_info:
                await qa_service.reject_question(sample_question.id)

            assert "already answered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_filter_question_success(self, qa_service, mock_session, sample_question):
        """Тест фильтрации вопроса."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            await qa_service.filter_question(
                sample_question.id,
                reason="Spam"
            )

            assert sample_question.is_filtered is True
            assert sample_question.filter_reason == "Spam"

    @pytest.mark.asyncio
    async def test_mark_as_answered_success(self, qa_service, mock_session, sample_question):
        """Тест отметки вопроса как отвеченного."""
        sample_question.status = QuestionStatus.PINNED

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            answer = "The answer is 42"
            await qa_service.mark_as_answered(sample_question.id, answer)

            assert sample_question.status == QuestionStatus.ANSWERED
            assert sample_question.answer == answer
            assert sample_question.answered_at is not None

    @pytest.mark.asyncio
    async def test_mark_as_answered_empty_answer(self, qa_service):
        """Тест отметки вопроса с пустым ответом."""
        with pytest.raises(EmptyQuestionError) as exc_info:
            await qa_service.mark_as_answered("some-id", "")

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_as_answered_invalid_status(self, qa_service, mock_session, sample_question):
        """Тест отметки вопроса с некорректным статусом."""
        sample_question.status = QuestionStatus.PENDING

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            with pytest.raises(InvalidStatusTransitionError):
                await qa_service.mark_as_answered(sample_question.id, "Answer")


class TestQAServiceUpvote:
    """Тесты upvote/downvote операций."""

    @pytest.mark.asyncio
    async def test_upvote_question_success(self, qa_service, mock_session, sample_question):
        """Тест успешного upvote."""
        # Mock question exists
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            # Mock no existing vote
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            await qa_service.upvote_question(
                question_id=sample_question.id,
                user_id=str(uuid4())
            )

            assert sample_question.upvote_count == 6  # Was 5
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upvote_question_not_found(self, qa_service):
        """Тест upvote несуществующего вопроса."""
        with patch.object(qa_service, 'get_question', return_value=None):
            with pytest.raises(QuestionNotFoundError):
                await qa_service.upvote_question(
                    question_id="nonexistent",
                    user_id=str(uuid4())
                )

    @pytest.mark.asyncio
    async def test_upvote_duplicate_vote(self, qa_service, mock_session, sample_question, sample_upvote):
        """Тест повторного upvote (duplicate)."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            # Mock existing vote
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = sample_upvote
            mock_session.execute.return_value = mock_result

            with pytest.raises(DuplicateVoteError):
                await qa_service.upvote_question(
                    question_id=sample_question.id,
                    user_id=sample_upvote.user_id
                )

    @pytest.mark.asyncio
    async def test_upvote_anonymous(self, qa_service, mock_session, sample_question):
        """Тест upvote от анонимного пользователя."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            await qa_service.upvote_question(
                question_id=sample_question.id,
                telegram_user_id=123456
            )

            assert sample_question.upvote_count == 6

    @pytest.mark.asyncio
    async def test_upvote_no_identifier_raises_error(self, qa_service, sample_question):
        """Тест upvote без идентификатора пользователя."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            with pytest.raises(QAServiceError):
                await qa_service.upvote_question(
                    question_id=sample_question.id,
                    user_id=None,
                    telegram_user_id=None
                )

    @pytest.mark.asyncio
    async def test_downvote_question_success(self, qa_service, mock_session, sample_question, sample_upvote):
        """Тест успешного downvote."""
        sample_question.upvote_count = 5

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            # Mock existing vote
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = sample_upvote
            mock_session.execute.return_value = mock_result

            await qa_service.downvote_question(
                question_id=sample_question.id,
                user_id=sample_upvote.user_id
            )

            assert sample_question.upvote_count == 4
            mock_session.delete.assert_called_once_with(sample_upvote)

    @pytest.mark.asyncio
    async def test_downvote_no_existing_vote(self, qa_service, mock_session, sample_question):
        """Тест downvote без существующего голоса."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            with pytest.raises(QAServiceError) as exc_info:
                await qa_service.downvote_question(
                    question_id=sample_question.id,
                    user_id=str(uuid4())
                )

            assert "has not voted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_has_user_voted_true(self, qa_service, mock_session):
        """Тест проверки голоса (проголосовал)."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Mock()  # Vote exists
        mock_session.execute.return_value = mock_result

        has_voted = await qa_service.has_user_voted(
            question_id=str(uuid4()),
            user_id=str(uuid4())
        )

        assert has_voted is True

    @pytest.mark.asyncio
    async def test_has_user_voted_false(self, qa_service, mock_session):
        """Тест проверки голоса (не проголосовал)."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        has_voted = await qa_service.has_user_voted(
            question_id=str(uuid4()),
            user_id=str(uuid4())
        )

        assert has_voted is False

    @pytest.mark.asyncio
    async def test_has_user_voted_no_identifier(self, qa_service):
        """Тест проверки голоса без идентификатора."""
        has_voted = await qa_service.has_user_voted(
            question_id=str(uuid4()),
            user_id=None,
            telegram_user_id=None
        )

        assert has_voted is False


class TestQAServiceStats:
    """Тесты статистики."""

    @pytest.mark.asyncio
    async def test_get_question_stats(self, qa_service, mock_session):
        """Тест получения статистики вопросов."""
        # Mock various count queries
        def mock_execute(query):
            mock_result = Mock()
            mock_result.scalar.return_value = 10  # Default count
            return mock_result

        mock_session.execute.side_effect = mock_execute

        stats = await qa_service.get_question_stats(stream_id=str(uuid4()))

        assert isinstance(stats, dict)
        assert "total_questions" in stats
        assert "pending_questions" in stats
        assert "answered_questions" in stats
        assert "rejected_questions" in stats
        assert "filtered_questions" in stats
        assert "total_votes" in stats

    @pytest.mark.asyncio
    async def test_get_question_stats_zero_counts(self, qa_service, mock_session):
        """Тест статистики с нулевыми значениями."""
        def mock_execute(query):
            mock_result = Mock()
            mock_result.scalar.return_value = 0
            return mock_result

        mock_session.execute.side_effect = mock_execute

        stats = await qa_service.get_question_stats(stream_id=str(uuid4()))

        assert stats["total_questions"] == 0
        assert stats["total_votes"] == 0


class TestQAServiceDelete:
    """Тесты удаления вопросов."""

    @pytest.mark.asyncio
    async def test_delete_question_success(self, qa_service, mock_session, sample_question):
        """Тест успешного удаления вопроса."""
        with patch.object(qa_service, 'get_question', return_value=sample_question):
            result = await qa_service.delete_question(sample_question.id)

            assert result is True
            mock_session.delete.assert_called_once_with(sample_question)
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_question_not_found(self, qa_service):
        """Тест удаления несуществующего вопроса."""
        with patch.object(qa_service, 'get_question', return_value=None):
            with pytest.raises(QuestionNotFoundError):
                await qa_service.delete_question("nonexistent-id")


class TestQAServiceEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_create_very_long_question(self, qa_service, mock_session):
        """Тест создания очень длинного вопроса."""
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        long_content = "Why " + "very " * 100 + "long question?"

        question = await qa_service.create_question(
            stream_id=str(uuid4()),
            content=long_content,
            author_id=str(uuid4())
        )

        assert question.content == long_content

    @pytest.mark.asyncio
    async def test_get_questions_include_filtered(self, qa_service, mock_session):
        """Тест получения вопросов включая отфильтрованные."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await qa_service.get_questions_by_stream(
            stream_id=str(uuid4()),
            include_filtered=True
        )

        # Verify query was executed
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_sql_error_handling(self, qa_service, mock_session):
        """Тест обработки SQLAlchemy ошибок."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_session.execute.side_effect = SQLAlchemyError("DB Error")

        with pytest.raises(QAServiceError):
            await qa_service.get_question("some-id")

    @pytest.mark.asyncio
    async def test_reject_already_rejected(self, qa_service, mock_session, sample_question):
        """Тест повторного отклонения вопроса."""
        sample_question.status = QuestionStatus.REJECTED

        with patch.object(qa_service, 'get_question', return_value=sample_question):
            with pytest.raises(InvalidStatusTransitionError):
                await qa_service.reject_question(sample_question.id)


class TestQAServiceSingleton:
    """Тесты singleton функций."""

    def test_get_qa_service_singleton(self):
        """Тест получения singleton экземпляра."""
        with patch("src.services.qa_service._qa_service", None):
            from src.services.qa_service import get_qa_service

            service1 = get_qa_service()
            service2 = get_qa_service()

            assert service1 is service2

    @pytest.mark.asyncio
    async def test_shutdown_qa_service(self):
        """Тест shutdown singleton."""
        from src.services.qa_service import _qa_service, shutdown_qa_service

        mock_service = AsyncMock()
        mock_service.close = AsyncMock()

        with patch("src.services.qa_service._qa_service", mock_service):
            await shutdown_qa_service()

            mock_service.close.assert_called_once()
