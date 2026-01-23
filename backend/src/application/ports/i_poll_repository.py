"""
IPollRepository Port Interface

Контракт для доступа к опросам в хранилище.
"""

from typing import Protocol, Optional, List
from src.domain.entities.poll import Poll, PollStatus
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId


class IPollRepository(Protocol):
    """
    Интерфейс репозитория опросов.

    Poll является Aggregate Root, поэтому репозиторий управляет
    всеми связанными entities (PollOption, PollVote) как единым целым.

    Examples:
        >>> poll = Poll.create(...)
        >>> await repository.save(poll)
        >>> active_polls = await repository.get_active_by_chat(chat_id)
    """

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
        ...

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
        ...

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
        ...

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
        ...

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
        ...

    async def delete(self, poll_id: str) -> None:
        """
        Удалить опрос по ID.

        Cascade delete удаляет все связанные PollOption и PollVote.

        Args:
            poll_id: Уникальный идентификатор опроса

        Raises:
            RepositoryError: При ошибке удаления
        """
        ...
