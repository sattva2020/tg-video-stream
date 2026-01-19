"""
IStreamRepository Port Interface

Контракт для доступа к потокам вещания в хранилище.
"""

from typing import Protocol, Optional, List
from src.domain.entities.stream import Stream
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId


class IStreamRepository(Protocol):
    """
    Интерфейс репозитория потоков вещания.
    
    Stream является Aggregate Root, поэтому репозиторий управляет
    всеми связанными entities (Playlist, Track) как единым целым.
    
    Examples:
        >>> stream = Stream.create(...)
        >>> await repository.save(stream)
        >>> active_streams = await repository.get_active_by_user(user.id)
    """
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
