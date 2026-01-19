"""
In-memory реализация репозитория потоков вещания для тестирования.

Этот модуль реализует IStreamRepository используя простой dict.
Используется в unit тестах для изоляции от базы данных.
"""

from typing import Optional, List, Dict
from uuid import UUID

from src.application.ports.i_stream_repository import IStreamRepository
from src.domain.entities.stream import Stream, StreamStatus
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId
from src.domain.errors import StreamNotFoundError


class InMemoryStreamRepository:
    """
    In-memory реализация IStreamRepository для тестирования.
    
    Хранит Stream entities напрямую в dict без ORM.
    Не требует StreamMapper т.к. работает с entities напрямую.
    """
    
    def __init__(self):
        """Инициализация репозитория с пустым хранилищем."""
        self._streams: Dict[UUID, Stream] = {}  # {stream_id.value: Stream entity}
    
    async def get_by_id(self, stream_id: StreamId) -> Optional[Stream]:
        """
        Получить поток по ID.
        
        Args:
            stream_id: Уникальный идентификатор потока
            
        Returns:
            Stream entity или None если не найден
        """
        return self._streams.get(stream_id.value)
    
    async def get_by_chat_id(self, chat_id: ChatId) -> Optional[Stream]:
        """
        Получить активный поток для указанного чата.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Активный Stream entity или None если нет активного потока
        """
        for stream in self._streams.values():
            if stream.chat_id == chat_id and stream.status == StreamStatus.ACTIVE:
                return stream
        return None
    
    async def get_active_by_user(self, user_id: UserId) -> List[Stream]:
        """
        Получить все активные потоки пользователя.
        
        Args:
            user_id: ID владельца потоков
            
        Returns:
            Список активных Stream entities (может быть пустым)
        """
        return [
            stream for stream in self._streams.values()
            if stream.owner_id == user_id and stream.status == StreamStatus.ACTIVE
        ]
    
    async def get_all_by_user(self, user_id: UserId) -> List[Stream]:
        """
        Получить все потоки пользователя (включая завершенные).
        
        Args:
            user_id: ID владельца потоков
            
        Returns:
            Список всех Stream entities (может быть пустым)
        """
        return [
            stream for stream in self._streams.values()
            if stream.owner_id == user_id
        ]
    
    async def save(self, stream: Stream) -> None:
        """
        Сохранить поток (create или update).
        
        Как Aggregate Root, Stream сохраняется вместе со всеми
        связанными Playlist и Track entities.
        
        Args:
            stream: Stream entity для сохранения
        """
        # Сохраняем копию entity (immutability)
        self._streams[stream.id.value] = stream
    
    async def delete(self, stream_id: StreamId) -> None:
        """
        Удалить поток по ID.
        
        Cascade delete удаляет все связанные Playlist и Track.
        
        Args:
            stream_id: Уникальный идентификатор потока
            
        Raises:
            StreamNotFoundError: Если поток не найден
        """
        if stream_id.value not in self._streams:
            raise StreamNotFoundError(f"Stream {stream_id} not found")
        
        del self._streams[stream_id.value]
    
    def clear(self) -> None:
        """Очистить хранилище (для тестов)."""
        self._streams.clear()
