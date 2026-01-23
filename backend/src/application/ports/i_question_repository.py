"""
IQuestionRepository Port Interface

Контракт для доступа к вопросам в хранилище.
"""

from typing import Protocol, Optional, List
from src.domain.entities.question import Question, QuestionStatus
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId


class IQuestionRepository(Protocol):
    """
    Интерфейс репозитория вопросов.

    Question является Entity, поэтому репозиторий управляет
    его жизненным циклом как единым целым.

    Examples:
        >>> question = Question.create(...)
        >>> await repository.save(question)
        >>> pending_questions = await repository.get_pending_by_stream(stream_id)
    """

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
        ...

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
        ...

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
        ...

    async def get_approved_by_stream(self, stream_id: str) -> List[Question]:
        """
        Получить все одобренные вопросы для указанного потока.

        Args:
            stream_id: ID потока

        Returns:
            Список вопросов в статусе APPROVED, отсортированных по голосам

        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        ...

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
        ...

    async def save(self, question: Question) -> None:
        """
        Сохранить вопрос (create или update).

        Args:
            question: Question entity для сохранения

        Raises:
            RepositoryError: При ошибке сохранения
        """
        ...

    async def delete(self, question_id: str) -> None:
        """
        Удалить вопрос по ID.

        Args:
            question_id: Уникальный идентификатор вопроса

        Raises:
            RepositoryError: При ошибке удаления
        """
        ...
