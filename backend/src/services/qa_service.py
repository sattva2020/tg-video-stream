"""
QA Service - управление вопросами и ответами

Сервис обеспечивает:
- Создание вопросов зрителями
- Модерацию вопросов (фильтрация, одобрение, отклонение)
- Upvote/downvote логику
- Ответы на вопросы
- Получение вопросов с сортировкой по голосам
- PostgreSQL persistence через ORM модели

Storage: PostgreSQL (questions, question_upvotes tables)
"""

from datetime import datetime, timezone
from typing import Optional, List
import logging
from uuid import uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.models.qa import Question, QuestionUpvote, QuestionStatus
from src.database import get_db

logger = logging.getLogger(__name__)


class QAServiceError(Exception):
    """Базовое исключение для ошибок QAService."""
    pass


class QuestionNotFoundError(QAServiceError):
    """Вопрос не найден."""
    pass


class DuplicateVoteError(QAServiceError):
    """Пользователь уже голосовал за этот вопрос."""
    pass


class InvalidStatusTransitionError(QAServiceError):
    """Недопустимый переход статуса вопроса."""
    pass


class EmptyQuestionError(QAServiceError):
    """Текст вопроса не может быть пустым."""
    pass


class QAService:
    """
    Сервис управления Q&A сессиями.

    Использует PostgreSQL для хранения вопросов и голосов:
    - questions → таблица вопросов
    - question_upvotes → таблица голосов

    Attributes:
        session: Async SQLAlchemy сессия
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Инициализация QAService.

        Args:
            session: Async SQLAlchemy сессия (если None, создается новая)
        """
        self._session = session
        self._owned_session = session is None

    async def _get_session(self) -> AsyncSession:
        """Получение сессии с lazy initialization."""
        if self._session is None:
            # Используем get_db() для получения новой сессии
            self._session = get_db()
        return self._session

    async def close(self) -> None:
        """Закрытие сессии (если мы её создавали)."""
        if self._owned_session and self._session is not None:
            await self._session.close()
            self._session = None

    # ========== Question CRUD Operations ==========

    async def create_question(
        self,
        stream_id: str,
        content: str,
        author_id: Optional[str] = None,
        telegram_user_id: Optional[int] = None,
        author_name: Optional[str] = None
    ) -> Question:
        """
        Создать новый вопрос.

        Args:
            stream_id: ID потока
            content: Текст вопроса
            author_id: ID автора (registered user)
            telegram_user_id: Telegram ID для анонимных пользователей
            author_name: Имя автора (для анонимных или отображения)

        Returns:
            Созданный Question

        Raises:
            EmptyQuestionError: Если текст вопроса пустой
        """
        if not content or not content.strip():
            raise EmptyQuestionError("Question content cannot be empty")

        session = await self._get_session()

        question = Question(
            id=str(uuid4()),
            stream_id=stream_id,
            author_id=author_id,
            telegram_user_id=telegram_user_id,
            author_name=author_name,
            content=content.strip(),
            status=QuestionStatus.PENDING,
            is_pinned=False,
            upvote_count=0,
            is_filtered=False,
            created_at=datetime.now(timezone.utc)
        )

        try:
            session.add(question)
            await session.flush()
            await session.refresh(question)

            logger.info(
                f"Создан вопрос: id={question.id}, stream={stream_id}, "
                f"author={author_name or telegram_user_id}"
            )

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to create question: {e}") from e

    async def get_question(self, question_id: str) -> Optional[Question]:
        """
        Получить вопрос по ID.

        Args:
            question_id: UUID вопроса

        Returns:
            Question или None если не найден
        """
        session = await self._get_session()

        try:
            stmt = select(Question).where(Question.id == question_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise QAServiceError(f"Failed to get question {question_id}: {e}") from e

    async def get_questions_by_stream(
        self,
        stream_id: str,
        status: Optional[QuestionStatus] = None,
        include_filtered: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Question]:
        """
        Получить вопросы для потока с пагинацией.

        Args:
            stream_id: ID потока
            status: Фильтр по статусу (опционально)
            include_filtered: Включать отфильтрованные вопросы
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список Question, отсортированных по upvote_count DESC, created_at ASC
        """
        session = await self._get_session()

        try:
            query = select(Question).where(Question.stream_id == stream_id)

            if status:
                query = query.where(Question.status == status)

            if not include_filtered:
                query = query.where(Question.is_filtered == False)

            # Сортировка: сначала по голосам (DESC), затем по времени (ASC)
            query = query.order_by(
                Question.upvote_count.desc(),
                Question.created_at.asc()
            )

            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise QAServiceError(f"Failed to get questions for stream {stream_id}: {e}") from e

    async def get_pending_questions(
        self,
        stream_id: str,
        limit: int = 50
    ) -> List[Question]:
        """
        Получить ожидающие вопросы (для модерации/отображения).

        Args:
            stream_id: ID потока
            limit: Максимальное количество

        Returns:
            Список Question в статусе PENDING, отсортированных по голосам
        """
        return await self.get_questions_by_stream(
            stream_id=stream_id,
            status=QuestionStatus.PENDING,
            include_filtered=False,
            limit=limit
        )

    async def get_answered_questions(
        self,
        stream_id: str,
        limit: int = 50
    ) -> List[Question]:
        """
        Получить отвеченные вопросы.

        Args:
            stream_id: ID потока
            limit: Максимальное количество

        Returns:
            Список Question в статусе ANSWERED
        """
        return await self.get_questions_by_stream(
            stream_id=stream_id,
            status=QuestionStatus.ANSWERED,
            include_filtered=False,
            limit=limit
        )

    # ========== Moderation Operations ==========

    async def approve_question(self, question_id: str) -> Question:
        """
        Одобрить вопрос (PENDING → PINNED).

        Args:
            question_id: UUID вопроса

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
            InvalidStatusTransitionError: Если статус не PENDING
        """
        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            if question.status != QuestionStatus.PENDING:
                raise InvalidStatusTransitionError(
                    f"Question {question_id} is not pending (current: {question.status})"
                )

            question.status = QuestionStatus.PINNED
            question.is_pinned = True
            await session.flush()
            await session.refresh(question)

            logger.info(f"Вопрос одобрен: id={question_id}")

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to approve question {question_id}: {e}") from e

    async def reject_question(
        self,
        question_id: str,
        reason: Optional[str] = None
    ) -> Question:
        """
        Отклонить вопрос (PENDING/PINNED → REJECTED).

        Args:
            question_id: UUID вопроса
            reason: Причина отклонения (опционально)

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
            InvalidStatusTransitionError: Если вопрос уже отвечен
        """
        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            if question.status == QuestionStatus.ANSWERED:
                raise InvalidStatusTransitionError(
                    f"Question {question_id} is already answered"
                )

            if question.status == QuestionStatus.REJECTED:
                raise InvalidStatusTransitionError(
                    f"Question {question_id} is already rejected"
                )

            question.status = QuestionStatus.REJECTED
            question.filter_reason = reason
            await session.flush()
            await session.refresh(question)

            logger.info(f"Вопрос отклонен: id={question_id}, reason={reason}")

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to reject question {question_id}: {e}") from e

    async def filter_question(
        self,
        question_id: str,
        reason: Optional[str] = None
    ) -> Question:
        """
        Отфильтровать вопрос (скрыть без изменения статуса).

        Args:
            question_id: UUID вопроса
            reason: Причина фильтрации

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
        """
        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            question.is_filtered = True
            question.filter_reason = reason
            await session.flush()
            await session.refresh(question)

            logger.info(f"Вопрос отфильтрован: id={question_id}, reason={reason}")

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to filter question {question_id}: {e}") from e

    async def mark_as_answered(
        self,
        question_id: str,
        answer: str
    ) -> Question:
        """
        Отметить вопрос как отвеченный (PINNED → ANSWERED).

        Args:
            question_id: UUID вопроса
            answer: Текст ответа

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
            EmptyQuestionError: Если ответ пустой
            InvalidStatusTransitionError: Если вопрос не одобрен
        """
        if not answer or not answer.strip():
            raise EmptyQuestionError("Answer cannot be empty")

        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            if question.status != QuestionStatus.PINNED:
                raise InvalidStatusTransitionError(
                    f"Question {question_id} is not approved (current: {question.status})"
                )

            question.status = QuestionStatus.ANSWERED
            question.answer = answer.strip()
            question.answered_at = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(question)

            logger.info(f"Вопрос отмечен как отвеченный: id={question_id}")

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to mark question {question_id} as answered: {e}") from e

    # ========== Upvote/Downvote Operations ==========

    async def upvote_question(
        self,
        question_id: str,
        user_id: Optional[str] = None,
        telegram_user_id: Optional[int] = None
    ) -> Question:
        """
        Проголосовать за вопрос.

        Args:
            question_id: UUID вопроса
            user_id: ID пользователя (registered)
            telegram_user_id: Telegram ID (для анонимных)

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
            DuplicateVoteError: Если пользователь уже голосовал
        """
        if not user_id and not telegram_user_id:
            raise QAServiceError("Either user_id or telegram_user_id must be provided")

        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            # Проверка на дубликат голоса
            stmt = select(QuestionUpvote).where(
                and_(
                    QuestionUpvote.question_id == question_id,
                    or_(
                        QuestionUpvote.user_id == user_id,
                        QuestionUpvote.telegram_user_id == telegram_user_id
                    )
                )
            )
            result = await session.execute(stmt)
            existing_vote = result.scalar_one_or_none()

            if existing_vote:
                raise DuplicateVoteError(
                    f"User already voted for question {question_id}"
                )

            # Создаем запись о голосе
            upvote = QuestionUpvote(
                id=str(uuid4()),
                question_id=question_id,
                user_id=user_id,
                telegram_user_id=telegram_user_id,
                created_at=datetime.now(timezone.utc)
            )
            session.add(upvote)

            # Увеличиваем счетчик
            question.upvote_count += 1
            await session.flush()
            await session.refresh(question)

            logger.info(
                f"Upvote добавлен: question={question_id}, "
                f"user={user_id or telegram_user_id}"
            )

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to upvote question {question_id}: {e}") from e

    async def downvote_question(
        self,
        question_id: str,
        user_id: Optional[str] = None,
        telegram_user_id: Optional[int] = None
    ) -> Question:
        """
        Убрать голос с вопроса.

        Args:
            question_id: UUID вопроса
            user_id: ID пользователя (registered)
            telegram_user_id: Telegram ID (для анонимных)

        Returns:
            Обновленный Question

        Raises:
            QuestionNotFoundError: Если вопрос не найден
        """
        if not user_id and not telegram_user_id:
            raise QAServiceError("Either user_id or telegram_user_id must be provided")

        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            # Находим голос пользователя
            stmt = select(QuestionUpvote).where(
                and_(
                    QuestionUpvote.question_id == question_id,
                    or_(
                        QuestionUpvote.user_id == user_id,
                        QuestionUpvote.telegram_user_id == telegram_user_id
                    )
                )
            )
            result = await session.execute(stmt)
            upvote = result.scalar_one_or_none()

            if not upvote:
                raise QAServiceError("User has not voted for this question")

            # Удаляем голос
            await session.delete(upvote)

            # Уменьшаем счетчик
            if question.upvote_count > 0:
                question.upvote_count -= 1
            await session.flush()
            await session.refresh(question)

            logger.info(
                f"Upvote удален: question={question_id}, "
                f"user={user_id or telegram_user_id}"
            )

            return question
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to downvote question {question_id}: {e}") from e

    async def has_user_voted(
        self,
        question_id: str,
        user_id: Optional[str] = None,
        telegram_user_id: Optional[int] = None
    ) -> bool:
        """
        Проверить, голосовал ли пользователь за вопрос.

        Args:
            question_id: UUID вопроса
            user_id: ID пользователя (registered)
            telegram_user_id: Telegram ID (для анонимных)

        Returns:
            True если пользователь уже голосовал
        """
        if not user_id and not telegram_user_id:
            return False

        session = await self._get_session()

        try:
            stmt = select(QuestionUpvote).where(
                and_(
                    QuestionUpvote.question_id == question_id,
                    or_(
                        QuestionUpvote.user_id == user_id,
                        QuestionUpvote.telegram_user_id == telegram_user_id
                    )
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            raise QAServiceError(f"Failed to check vote for question {question_id}: {e}") from e

    # ========== Statistics ==========

    async def get_question_stats(self, stream_id: str) -> dict:
        """
        Получить статистику вопросов для потока.

        Args:
            stream_id: ID потока

        Returns:
            Словарь со статистикой:
            - total_questions: общее количество вопросов
            - pending_questions: ожидающие вопросы
            - answered_questions: отвеченные вопросы
            - rejected_questions: отклоненные вопросы
            - filtered_questions: отфильтрованные вопросы
            - total_votes: общее количество голосов
        """
        session = await self._get_session()

        try:
            # Общее количество вопросов
            total_stmt = select(func.count(Question.id)).where(
                Question.stream_id == stream_id
            )
            total = await session.execute(total_stmt)
            total_questions = total.scalar() or 0

            # По статусам
            pending_stmt = select(func.count(Question.id)).where(
                and_(
                    Question.stream_id == stream_id,
                    Question.status == QuestionStatus.PENDING,
                    Question.is_filtered == False
                )
            )
            pending = await session.execute(pending_stmt)
            pending_questions = pending.scalar() or 0

            answered_stmt = select(func.count(Question.id)).where(
                and_(
                    Question.stream_id == stream_id,
                    Question.status == QuestionStatus.ANSWERED
                )
            )
            answered = await session.execute(answered_stmt)
            answered_questions = answered.scalar() or 0

            rejected_stmt = select(func.count(Question.id)).where(
                and_(
                    Question.stream_id == stream_id,
                    Question.status == QuestionStatus.REJECTED
                )
            )
            rejected = await session.execute(rejected_stmt)
            rejected_questions = rejected.scalar() or 0

            filtered_stmt = select(func.count(Question.id)).where(
                and_(
                    Question.stream_id == stream_id,
                    Question.is_filtered == True
                )
            )
            filtered = await session.execute(filtered_stmt)
            filtered_questions = filtered.scalar() or 0

            # Общее количество голосов
            votes_stmt = select(func.sum(Question.upvote_count)).where(
                Question.stream_id == stream_id
            )
            votes = await session.execute(votes_stmt)
            total_votes = votes.scalar() or 0

            return {
                "total_questions": total_questions,
                "pending_questions": pending_questions,
                "answered_questions": answered_questions,
                "rejected_questions": rejected_questions,
                "filtered_questions": filtered_questions,
                "total_votes": total_votes
            }
        except SQLAlchemyError as e:
            raise QAServiceError(f"Failed to get stats for stream {stream_id}: {e}") from e

    async def delete_question(self, question_id: str) -> bool:
        """
        Удалить вопрос.

        Args:
            question_id: UUID вопроса

        Returns:
            True если вопрос удален

        Raises:
            QuestionNotFoundError: Если вопрос не найден
        """
        session = await self._get_session()

        try:
            question = await self.get_question(question_id)
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            await session.delete(question)
            await session.flush()

            logger.info(f"Вопрос удален: id={question_id}")

            return True
        except SQLAlchemyError as e:
            await session.rollback()
            raise QAServiceError(f"Failed to delete question {question_id}: {e}") from e


# Singleton instance
_qa_service: Optional[QAService] = None


def get_qa_service() -> QAService:
    """Получить singleton экземпляр QAService."""
    global _qa_service
    if _qa_service is None:
        _qa_service = QAService()
    return _qa_service


async def shutdown_qa_service() -> None:
    """Закрыть QAService при завершении приложения."""
    global _qa_service
    if _qa_service is not None:
        await _qa_service.close()
        _qa_service = None
