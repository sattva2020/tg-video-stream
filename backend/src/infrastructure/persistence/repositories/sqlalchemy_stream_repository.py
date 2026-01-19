"""
SQLAlchemy реализация репозитория потоков вещания.

Этот модуль реализует IStreamRepository port используя SQLAlchemy ORM.
Stream является Aggregate Root, поэтому репозиторий управляет
всеми связанными entities (Playlist, Track) как единым целым.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.application.ports.i_stream_repository import IStreamRepository
from src.domain.entities.stream import Stream, StreamStatus
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId
from src.infrastructure.persistence.mappers.stream_mapper import StreamMapper
from src.models.stream import Stream as StreamORM
from src.domain.errors import RepositoryError, StreamNotFoundError


class SqlAlchemyStreamRepository:
    """
    SQLAlchemy реализация IStreamRepository.
    
    Использует StreamMapper для преобразования между Domain entities и ORM models.
    Репозиторий НЕ выполняет commit - это ответственность use case.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            session: Async SQLAlchemy сессия
        """
        self._session = session
    
    async def get_by_id(self, stream_id: StreamId) -> Optional[Stream]:
        """
        Получить поток по ID.
        
        Args:
            stream_id: Уникальный идентификатор потока
            
        Returns:
            Stream entity или None если не найден
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(StreamORM)
                .where(StreamORM.id == stream_id.value)
                .options(selectinload(StreamORM.owner))  # Eager load owner
            )
            result = await self._session.execute(stmt)
            orm_stream = result.scalar_one_or_none()
            
            if not orm_stream:
                return None
            
            return StreamMapper.to_entity(orm_stream)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get stream by id {stream_id}: {e}") from e
    
    async def get_by_chat_id(self, chat_id: ChatId) -> Optional[Stream]:
        """
        Получить активный поток для указанного чата.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Активный Stream entity или None если нет активного потока
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(StreamORM)
                .where(
                    and_(
                        StreamORM.chat_id == chat_id.value,
                        StreamORM.status == StreamStatus.ACTIVE.value
                    )
                )
                .options(selectinload(StreamORM.owner))
            )
            result = await self._session.execute(stmt)
            orm_stream = result.scalar_one_or_none()
            
            if not orm_stream:
                return None
            
            return StreamMapper.to_entity(orm_stream)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get stream by chat_id {chat_id}: {e}") from e
    
    async def get_active_by_user(self, user_id: UserId) -> List[Stream]:
        """
        Получить все активные потоки пользователя.
        
        Args:
            user_id: ID владельца потоков
            
        Returns:
            Список активных Stream entities (может быть пустым)
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(StreamORM)
                .where(
                    and_(
                        StreamORM.owner_id == user_id.value,
                        StreamORM.status == StreamStatus.ACTIVE.value
                    )
                )
                .options(selectinload(StreamORM.owner))
            )
            result = await self._session.execute(stmt)
            orm_streams = result.scalars().all()
            
            return StreamMapper.to_entity_list(orm_streams)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get active streams by user {user_id}: {e}") from e
    
    async def get_all_by_user(self, user_id: UserId) -> List[Stream]:
        """
        Получить все потоки пользователя (включая завершенные).
        
        Args:
            user_id: ID владельца потоков
            
        Returns:
            Список всех Stream entities (может быть пустым)
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = (
                select(StreamORM)
                .where(StreamORM.owner_id == user_id.value)
                .options(selectinload(StreamORM.owner))
            )
            result = await self._session.execute(stmt)
            orm_streams = result.scalars().all()
            
            return StreamMapper.to_entity_list(orm_streams)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get all streams by user {user_id}: {e}") from e
    
    async def save(self, stream: Stream) -> None:
        """
        Сохранить поток (create или update).
        
        Как Aggregate Root, Stream сохраняется вместе со всеми
        связанными Playlist и Track entities.
        
        Args:
            stream: Stream entity для сохранения
            
        Raises:
            RepositoryError: При ошибке сохранения
        """
        try:
            # Проверяем, существует ли поток
            stmt = select(StreamORM).where(StreamORM.id == stream.id.value)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()
            
            if existing_orm:
                # Update: обновляем существующий ORM объект
                StreamMapper.update_orm(existing_orm, stream)
            else:
                # Create: создаем новый ORM объект
                orm_stream = StreamMapper.to_orm(stream)
                self._session.add(orm_stream)
            
            # flush() для раннего обнаружения constraint violations
            # commit() НЕ вызываем - это ответственность use case
            await self._session.flush()
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save stream {stream.id}: {e}") from e
    
    async def delete(self, stream_id: StreamId) -> None:
        """
        Удалить поток по ID.
        
        Cascade delete удаляет все связанные Playlist и Track.
        
        Args:
            stream_id: Уникальный идентификатор потока
            
        Raises:
            RepositoryError: При ошибке удаления
            StreamNotFoundError: Если поток не найден
        """
        try:
            stmt = select(StreamORM).where(StreamORM.id == stream_id.value)
            result = await self._session.execute(stmt)
            orm_stream = result.scalar_one_or_none()
            
            if not orm_stream:
                raise StreamNotFoundError(f"Stream {stream_id} not found")
            
            await self._session.delete(orm_stream)
            await self._session.flush()
            
        except StreamNotFoundError:
            raise  # Re-raise domain errors as-is
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete stream {stream_id}: {e}") from e
