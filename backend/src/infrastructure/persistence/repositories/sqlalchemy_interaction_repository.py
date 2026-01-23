"""
SQLAlchemy реализация репозитория взаимодействий (реакции и чат).

Этот модуль реализует репозиторий для управления Reaction и ChatMessage entities
используя SQLAlchemy ORM. Управляет эмодзи-реакциями зрителей и сообщениями чата
для отображения на stream overlay.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.domain.entities.reaction import Reaction, ReactionType
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.stream_id import StreamId
from src.infrastructure.persistence.mappers.interaction_mapper import InteractionMapper
from src.models.interaction import EmojiReaction as EmojiReactionORM, ReactionDisplayStatus, ChatMessage as ChatMessageORM, ChatMessageStatus
from src.domain.errors import RepositoryError


class InteractionRepository:
    """
    SQLAlchemy реализация репозитория взаимодействий.

    Управляет Reaction entities (эмодзи-реакции) и ChatMessage ORM models (чат-сообщения).
    Использует InteractionMapper для преобразования между Domain entities и ORM models.
    Репозиторий НЕ выполняет commit - это ответственность use case.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session: Async SQLAlchemy сессия
        """
        self._session = session

    # ========== Reaction Methods ==========

    async def get_reaction_by_id(self, reaction_id: str) -> Optional[Reaction]:
        """
        Получить реакцию по ID.

        Args:
            reaction_id: Уникальный идентификатор реакции

        Returns:
            Reaction entity или None если не найдена

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(EmojiReactionORM)
                .where(EmojiReactionORM.id == reaction_id)
            )
            result = await self._session.execute(stmt)
            orm_reaction = result.scalar_one_or_none()

            if not orm_reaction:
                return None

            return InteractionMapper.reaction_to_entity(orm_reaction)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get reaction by id {reaction_id}: {e}") from e

    async def get_reactions_by_stream(self, stream_id: str, limit: int = 100) -> List[Reaction]:
        """
        Получить реакции для указанного потока.

        Args:
            stream_id: ID потока
            limit: Максимальное количество реакций (по умолчанию 100)

        Returns:
            Список Reaction entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(EmojiReactionORM)
                .where(EmojiReactionORM.stream_id == stream_id)
                .where(EmojiReactionORM.display_status != ReactionDisplayStatus.HIDDEN)
                .order_by(desc(EmojiReactionORM.created_at))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            orm_reactions = result.scalars().all()

            return InteractionMapper.reaction_to_entity_list(orm_reactions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get reactions for stream {stream_id}: {e}") from e

    async def get_active_reactions_by_stream(self, stream_id: str, limit: int = 50) -> List[Reaction]:
        """
        Получить активные (не истекшие и видимые) реакции для потока.

        Args:
            stream_id: ID потока
            limit: Максимальное количество реакций (по умолчанию 50)

        Returns:
            Список активных Reaction entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            from datetime import datetime
            stmt = (
                select(EmojiReactionORM)
                .where(
                    and_(
                        EmojiReactionORM.stream_id == stream_id,
                        EmojiReactionORM.display_status == ReactionDisplayStatus.VISIBLE,
                        or_(
                            EmojiReactionORM.expires_at.is_(None),
                            EmojiReactionORM.expires_at > datetime.utcnow()
                        )
                    )
                )
                .order_by(desc(EmojiReactionORM.created_at))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            orm_reactions = result.scalars().all()

            return InteractionMapper.reaction_to_entity_list(orm_reactions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get active reactions for stream {stream_id}: {e}") from e

    async def get_reactions_by_user(self, user_id: UserId, stream_id: Optional[str] = None) -> List[Reaction]:
        """
        Получить реакции пользователя.

        Args:
            user_id: ID пользователя
            stream_id: Опциональный фильтр по потоку

        Returns:
            Список Reaction entities (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            conditions = [EmojiReactionORM.user_id == user_id.value]

            if stream_id:
                conditions.append(EmojiReactionORM.stream_id == stream_id)

            stmt = (
                select(EmojiReactionORM)
                .where(and_(*conditions))
                .order_by(desc(EmojiReactionORM.created_at))
            )
            result = await self._session.execute(stmt)
            orm_reactions = result.scalars().all()

            return InteractionMapper.reaction_to_entity_list(orm_reactions)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get reactions for user {user_id}: {e}") from e

    async def save_reaction(self, reaction: Reaction) -> None:
        """
        Сохранить реакцию (create или update).

        Args:
            reaction: Reaction entity для сохранения

        Raises:
            RepositoryError: При ошибке сохранения
        """
        try:
            # Проверяем, существует ли реакция
            stmt = select(EmojiReactionORM).where(EmojiReactionORM.id == reaction.id)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()

            if existing_orm:
                # Update: обновляем существующий ORM объект
                InteractionMapper.update_reaction_orm(existing_orm, reaction)
            else:
                # Create: создаем новый ORM объект
                orm_reaction = InteractionMapper.reaction_to_orm(reaction)
                self._session.add(orm_reaction)

            # flush() для раннего обнаружения constraint violations
            # commit() НЕ вызываем - это ответственность use case
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save reaction {reaction.id}: {e}") from e

    async def delete_reaction(self, reaction_id: str) -> None:
        """
        Удалить реакцию по ID.

        Args:
            reaction_id: Уникальный идентификатор реакции

        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(EmojiReactionORM).where(EmojiReactionORM.id == reaction_id)
            result = await self._session.execute(stmt)
            orm_reaction = result.scalar_one_or_none()

            if not orm_reaction:
                # Idempotent delete - не raising error если не найден
                return

            await self._session.delete(orm_reaction)
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete reaction {reaction_id}: {e}") from e

    async def delete_expired_reactions(self, stream_id: Optional[str] = None) -> int:
        """
        Удалить истекшие реакции.

        Args:
            stream_id: Опциональный фильтр по потоку

        Returns:
            Количество удаленных реакций

        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            from datetime import datetime
            conditions = [EmojiReactionORM.expires_at < datetime.utcnow()]

            if stream_id:
                conditions.append(EmojiReactionORM.stream_id == stream_id)

            stmt = select(EmojiReactionORM).where(and_(*conditions))
            result = await self._session.execute(stmt)
            orm_reactions = result.scalars().all()

            count = len(orm_reactions)
            for orm_reaction in orm_reactions:
                await self._session.delete(orm_reaction)

            await self._session.flush()
            return count

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete expired reactions: {e}") from e

    # ========== Chat Message Methods ==========

    async def get_chat_message_by_id(self, message_id: str) -> Optional[ChatMessageORM]:
        """
        Получить chat-сообщение по ID.

        Args:
            message_id: Уникальный идентификатор сообщения

        Returns:
            ChatMessage ORM model или None если не найдено

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(ChatMessageORM)
                .where(ChatMessageORM.id == message_id)
            )
            result = await self._session.execute(stmt)
            orm_message = result.scalar_one_or_none()

            return orm_message

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get chat message by id {message_id}: {e}") from e

    async def get_chat_messages_by_stream(
        self,
        stream_id: str,
        limit: int = 100,
        status: Optional[ChatMessageStatus] = None
    ) -> List[ChatMessageORM]:
        """
        Получить chat-сообщения для указанного потока.

        Args:
            stream_id: ID потока
            limit: Максимальное количество сообщений (по умолчанию 100)
            status: Опциональный фильтр по статусу

        Returns:
            Список ChatMessage ORM models (может быть пустым)

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            conditions = [
                ChatMessageORM.stream_id == stream_id,
                ChatMessageORM.is_filtered == False  # Исключаем отфильтрованные
            ]

            if status:
                conditions.append(ChatMessageORM.message_status == status)

            stmt = (
                select(ChatMessageORM)
                .where(and_(*conditions))
                .order_by(desc(ChatMessageORM.created_at))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            orm_messages = result.scalars().all()

            return list(orm_messages)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get chat messages for stream {stream_id}: {e}") from e

    async def save_chat_message(self, message: ChatMessageORM) -> None:
        """
        Сохранить chat-сообщение (create или update).

        Args:
            message: ChatMessage ORM model для сохранения

        Raises:
            RepositoryError: При ошибке сохранения
        """
        try:
            # Проверяем, существует ли сообщение
            stmt = select(ChatMessageORM).where(ChatMessageORM.id == message.id)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()

            if existing_orm:
                # Update: обновляем существующий ORM объект
                existing_orm.content = message.content
                existing_orm.message_status = message.message_status
                existing_orm.is_filtered = message.is_filtered
                existing_orm.filter_reason = message.filter_reason
                existing_orm.is_flagged = message.is_flagged
            else:
                # Create: добавляем новый ORM объект
                self._session.add(message)

            # flush() для раннего обнаружения constraint violations
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save chat message {message.id}: {e}") from e

    async def delete_chat_message(self, message_id: str) -> None:
        """
        Удалить chat-сообщение по ID.

        Args:
            message_id: Уникальный идентификатор сообщения

        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(ChatMessageORM).where(ChatMessageORM.id == message_id)
            result = await self._session.execute(stmt)
            orm_message = result.scalar_one_or_none()

            if not orm_message:
                # Idempotent delete - не raising error если не найден
                return

            await self._session.delete(orm_message)
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete chat message {message_id}: {e}") from e

    async def flag_chat_message(self, message_id: str, flagged: bool = True) -> None:
        """
        Пометить chat-сообщение для проверки.

        Args:
            message_id: Уникальный идентификатор сообщения
            flagged: True для пометки, False для снятия пометки

        Raises:
            RepositoryError: При ошибке обновления
        """
        try:
            stmt = select(ChatMessageORM).where(ChatMessageORM.id == message_id)
            result = await self._session.execute(stmt)
            orm_message = result.scalar_one_or_none()

            if not orm_message:
                raise RepositoryError(f"Chat message {message_id} not found")

            orm_message.is_flagged = flagged
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to flag chat message {message_id}: {e}") from e

    async def filter_chat_message(self, message_id: str, filtered: bool = True, reason: Optional[str] = None) -> None:
        """
        Отфильтровать chat-сообщение (скрыть из overlay).

        Args:
            message_id: Уникальный идентификатор сообщения
            filtered: True для фильтрации, False для отмены
            reason: Причина фильтрации

        Raises:
            RepositoryError: При ошибке обновления
        """
        try:
            stmt = select(ChatMessageORM).where(ChatMessageORM.id == message_id)
            result = await self._session.execute(stmt)
            orm_message = result.scalar_one_or_none()

            if not orm_message:
                raise RepositoryError(f"Chat message {message_id} not found")

            orm_message.is_filtered = filtered
            orm_message.filter_reason = reason
            await self._session.flush()

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to filter chat message {message_id}: {e}") from e


# Импорт или_ для использования в запросах
from sqlalchemy import or_
