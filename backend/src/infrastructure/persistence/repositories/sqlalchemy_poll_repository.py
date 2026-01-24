"""
SQLAlchemy реализация репозитория опросов.

Этот модуль реализует IPollRepository port используя SQLAlchemy ORM.
Poll является Aggregate Root, поэтому репозиторий управляет
всеми связанными entities (PollOption, PollVote) как единым целым.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.domain.entities.poll import Poll, PollStatus
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId
from src.infrastructure.persistence.mappers.poll_mapper import PollMapper
from src.models.poll import Poll as PollORM
from src.domain.errors import RepositoryError


class SqlAlchemyPollRepository:
    """
    SQLAlchemy реализация IPollRepository.

    Использует PollMapper для преобразования между Domain entities и ORM models.
    Репозиторий НЕ выполняет commit - это ответственность use case.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session: Async SQLAlchemy сессия
        """
        self._session = session

    async def get_by_id(self, poll_id: str) -> Optional[Poll]:
        """
        Получить опрос по ID.

        Args:
            poll_id: Уникальный идентификатор опроса

        Returns:
            Poll entity или None если не найден

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(PollORM)
                .where(PollORM.id == poll_id)
                .options(selectinload(PollORM.owner))  # Eager load owner
                .options(selectinload(PollORM.options))  # Eager load options
            )
            result = await self._session.execute(stmt)
            orm_poll = result.scalar_one_or_none()

            if not orm_poll:
                return None

            return PollMapper.to_entity(orm_poll)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get poll by id {poll_id}: {e}") from e

    async def get_by_stream_id(self, stream_id: str) -> List[Poll]:
        """
        Получить все опросы для указанного потока.

        Args:
            stream_id: ID потока

        Returns:
            Список Poll entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            # Note: stream_id might not be in PollORM yet, using get_by_user as fallback
            # This will need to be adjusted when stream_id is added to PollORM
            stmt = (
                select(PollORM)
                .order_by(PollORM.created_at.desc())
                .options(selectinload(PollORM.owner))
                .options(selectinload(PollORM.options))
            )
            result = await self._session.execute(stmt)
            orm_polls = result.scalars().all()

            # Filter in Python for now (will be optimized with proper stream_id column)
            poll_entities = PollMapper.to_entity_list(orm_polls)
            return [p for p in poll_entities if p.stream_id == stream_id]

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get polls by stream_id {stream_id}: {e}") from e

    async def get_active_by_chat(self, chat_id: ChatId) -> List[Poll]:
        """
        Получить все активные опросы для указанного чата.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Список активных Poll entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(PollORM)
                .where(PollORM.status == PollStatus.ACTIVE.value)
                .order_by(PollORM.created_at.desc())
                .options(selectinload(PollORM.owner))
                .options(selectinload(PollORM.options))
            )
            result = await self._session.execute(stmt)
            orm_polls = result.scalars().all()

            # Filter by chat_id in Python (since chat_id might not be in ORM yet)
            poll_entities = PollMapper.to_entity_list(orm_polls)
            return [p for p in poll_entities if p.chat_id.value == chat_id.value]

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get active polls by chat_id {chat_id}: {e}") from e

    async def get_by_user(self, user_id: UserId) -> List[Poll]:
        """
        Получить все опросы пользователя.

        Args:
            user_id: ID создателя опросов

        Returns:
            Список всех Poll entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(PollORM)
                .where(PollORM.owner_id == user_id.value)
                .order_by(PollORM.created_at.desc())
                .options(selectinload(PollORM.owner))
                .options(selectinload(PollORM.options))
            )
            result = await self._session.execute(stmt)
            orm_polls = result.scalars().all()

            return PollMapper.to_entity_list(orm_polls)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get polls by user {user_id}: {e}") from e

    async def save(self, poll: Poll) -> None:
        """
        Сохранить опрос (create или update).

        Как Aggregate Root, Poll сохраняется вместе со всеми
        связанными PollOption entities.

        Args:
            poll: Poll entity для сохранения

        Raises:
            RepositoryError: При ошибке сохранения
        """
        try:
            # Проверяем, существует ли опрос
            stmt = select(PollORM).where(PollORM.id == poll.id)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()

            if existing_orm:
                # Update: обновляем существующий ORM объект
                PollMapper.update_orm(existing_orm, poll)
            else:
                # Create: создаем новый ORM объект
                orm_poll = PollMapper.to_orm(poll)
                self._session.add(orm_poll)

            # flush() для раннего обнаружения constraint violations
            # commit() НЕ вызываем - это ответственность use case
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save poll {poll.id}: {e}") from e

    async def delete(self, poll_id: str) -> None:
        """
        Удалить опрос по ID.

        Cascade delete удаляет все связанные PollOption и PollVote.

        Args:
            poll_id: Уникальный идентификатор опроса

        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(PollORM).where(PollORM.id == poll_id)
            result = await self._session.execute(stmt)
            orm_poll = result.scalar_one_or_none()

            if not orm_poll:
                # Не raising error, just return silently (idempotent delete)
                return

            await self._session.delete(orm_poll)
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete poll {poll_id}: {e}") from e


# Alias for consistency with naming convention
PollRepository = SqlAlchemyPollRepository
