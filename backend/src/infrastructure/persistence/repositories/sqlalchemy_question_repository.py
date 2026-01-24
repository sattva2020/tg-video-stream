"""
SQLAlchemy реализация репозитория вопросов.

Этот модуль реализует IQuestionRepository port используя SQLAlchemy ORM.
Question является Entity, поэтому репозиторий управляет
его жизненным циклом как единым целым.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.domain.entities.question import Question, QuestionStatus
from src.domain.value_objects.user_id import UserId
from src.infrastructure.persistence.mappers.question_mapper import QuestionMapper
from src.models.qa import Question as QuestionORM
from src.domain.errors import RepositoryError


class SqlAlchemyQuestionRepository:
    """
    SQLAlchemy реализация IQuestionRepository.

    Использует QuestionMapper для преобразования между Domain entities и ORM models.
    Репозиторий НЕ выполняет commit - это ответственность use case.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session: Async SQLAlchemy сессия
        """
        self._session = session

    async def get_by_id(self, question_id: str) -> Optional[Question]:
        """
        Получить вопрос по ID.

        Args:
            question_id: Уникальный идентификатор вопроса

        Returns:
            Question entity или None если не найден

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(QuestionORM)
                .where(QuestionORM.id == question_id)
                .options(selectinload(QuestionORM.author))  # Eager load author
                .options(selectinload(QuestionORM.stream))  # Eager load stream
            )
            result = await self._session.execute(stmt)
            orm_question = result.scalar_one_or_none()

            if not orm_question:
                return None

            return QuestionMapper.to_entity(orm_question)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get question by id {question_id}: {e}") from e

    async def get_by_stream_id(self, stream_id: str, status: Optional[QuestionStatus] = None) -> List[Question]:
        """
        Получить все вопросы для указанного потока.

        Args:
            stream_id: ID потока
            status: Опциональный фильтр по статусу вопроса

        Returns:
            Список Question entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            query = select(QuestionORM).where(QuestionORM.stream_id == stream_id)

            if status:
                # Map domain status to ORM status
                from src.models.qa import QuestionStatus as ORMQuestionStatus
                status_mapping = {
                    QuestionStatus.PENDING: ORMQuestionStatus.PENDING,
                    QuestionStatus.APPROVED: ORMQuestionStatus.PINNED,
                    QuestionStatus.ANSWERED: ORMQuestionStatus.ANSWERED,
                    QuestionStatus.REJECTED: ORMQuestionStatus.REJECTED,
                }
                orm_status = status_mapping.get(status)
                if orm_status:
                    query = query.where(QuestionORM.status == orm_status)

            query = query.order_by(QuestionORM.created_at.desc())
            query = query.options(selectinload(QuestionORM.author))
            query = query.options(selectinload(QuestionORM.stream))

            result = await self._session.execute(query)
            orm_questions = result.scalars().all()

            return QuestionMapper.to_entity_list(orm_questions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get questions by stream_id {stream_id}: {e}") from e

    async def get_pending_by_stream(self, stream_id: str) -> List[Question]:
        """
        Получить все ожидающие вопросы для указанного потока.

        Args:
            stream_id: ID потока

        Returns:
            Список вопросов в статусе PENDING, отсортированных по голосам

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            from src.models.qa import QuestionStatus as ORMQuestionStatus

            stmt = (
                select(QuestionORM)
                .where(
                    and_(
                        QuestionORM.stream_id == stream_id,
                        QuestionORM.status == ORMQuestionStatus.PENDING,
                        QuestionORM.is_filtered == False  # Не отфильтрованные
                    )
                )
                .order_by(QuestionORM.upvote_count.desc(), QuestionORM.created_at.asc())
                .options(selectinload(QuestionORM.author))
                .options(selectinload(QuestionORM.stream))
            )
            result = await self._session.execute(stmt)
            orm_questions = result.scalars().all()

            return QuestionMapper.to_entity_list(orm_questions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get pending questions by stream {stream_id}: {e}") from e

    async def get_approved_by_stream(self, stream_id: str) -> List[Question]:
        """
        Получить все одобренные вопросы для указанного потока.

        Args:
            stream_id: ID потока

        Returns:
            Список вопросов в статусе APPROVED/PINNED, отсортированных по голосам

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            from src.models.qa import QuestionStatus as ORMQuestionStatus

            stmt = (
                select(QuestionORM)
                .where(
                    and_(
                        QuestionORM.stream_id == stream_id,
                        QuestionORM.status == ORMQuestionStatus.PINNED
                    )
                )
                .order_by(QuestionORM.upvote_count.desc(), QuestionORM.created_at.asc())
                .options(selectinload(QuestionORM.author))
                .options(selectinload(QuestionORM.stream))
            )
            result = await self._session.execute(stmt)
            orm_questions = result.scalars().all()

            return QuestionMapper.to_entity_list(orm_questions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get approved questions by stream {stream_id}: {e}") from e

    async def get_by_user(self, user_id: UserId) -> List[Question]:
        """
        Получить все вопросы пользователя.

        Args:
            user_id: ID автора вопросов

        Returns:
            Список всех Question entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(QuestionORM)
                .where(QuestionORM.author_id == user_id.value)
                .order_by(QuestionORM.created_at.desc())
                .options(selectinload(QuestionORM.author))
                .options(selectinload(QuestionORM.stream))
            )
            result = await self._session.execute(stmt)
            orm_questions = result.scalars().all()

            return QuestionMapper.to_entity_list(orm_questions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get questions by user {user_id}: {e}") from e

    async def save(self, question: Question) -> None:
        """
        Сохранить вопрос (create или update).

        Args:
            question: Question entity для сохранения

        Raises:
            RepositoryError: При ошибке сохранения
        """
        try:
            # Проверяем, существует ли вопрос
            stmt = select(QuestionORM).where(QuestionORM.id == question.id)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()

            if existing_orm:
                # Update: обновляем существующий ORM объект
                QuestionMapper.update_orm(existing_orm, question)
            else:
                # Create: создаем новый ORM объект
                orm_question = QuestionMapper.to_orm(question)
                self._session.add(orm_question)

            # flush() для раннего обнаружения constraint violations
            # commit() НЕ вызываем - это ответственность use case
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save question {question.id}: {e}") from e

    async def delete(self, question_id: str) -> None:
        """
        Удалить вопрос по ID.

        Args:
            question_id: Уникальный идентификатор вопроса

        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(QuestionORM).where(QuestionORM.id == question_id)
            result = await self._session.execute(stmt)
            orm_question = result.scalar_one_or_none()

            if not orm_question:
                # Не raising error, just return silently (idempotent delete)
                return

            await self._session.delete(orm_question)
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete question {question_id}: {e}") from e


# Alias for consistency with naming convention
QuestionRepository = SqlAlchemyQuestionRepository
