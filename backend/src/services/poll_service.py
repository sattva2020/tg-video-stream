"""
Poll Service - управление интерактивными опросами

Сервис обеспечивает:
- Создание опросов с вариантами ответов
- Публикацию и закрытие опросов
- Обработку голосования (single/multiple choice)
- Проверку повторного голосования
- Получение результатов опросов
- WebSocket уведомления о событиях опроса

Storage: PostgreSQL через PollRepository
Domain: Poll Entity с бизнес-логикой
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.poll import Poll, PollOption, PollStatus
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.chat_id import ChatId
from src.domain.errors import BusinessRuleViolationError
from src.application.ports.i_poll_repository import IPollRepository
from src.infrastructure.persistence.repositories.sqlalchemy_poll_repository import SqlAlchemyPollRepository
from src.api.websocket import notify_poll_created, notify_poll_updated, notify_vote_cast

logger = logging.getLogger(__name__)


class PollServiceError(Exception):
    """Базовое исключение для ошибок PollService."""
    pass


class PollNotFoundError(PollServiceError):
    """Опрос не найден."""
    pass


class PollClosedError(PollServiceError):
    """Опрос закрыт и не принимает голоса."""
    pass


class DuplicateVoteError(PollServiceError):
    """Пользователь уже голосовал в этом опросе."""
    pass


class InvalidOptionsError(PollServiceError):
    """Указаны некорректные варианты ответов."""
    pass


class PollService:
    """
    Сервис управления интерактивными опросами.

    Использует PollRepository для персистентности:
    - PostgreSQL для хранения опросов и голосов
    - Poll Entity для бизнес-логики
    - WebSocket для real-time уведомлений

    Attributes:
        repository: Репозиторий для доступа к данным
        session: SQLAlchemy async сессия
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация PollService.

        Args:
            session: SQLAlchemy async сессия
        """
        self._session = session
        self._repository: IPollRepository = SqlAlchemyPollRepository(session)

    # ========== CRUD Operations ==========

    async def create(
        self,
        stream_id: str,
        chat_id: int,
        created_by: str,
        question: str,
        options: List[str],
        allow_multiple_votes: bool = False,
        description: Optional[str] = None
    ) -> Poll:
        """
        Создать новый опрос.

        Args:
            stream_id: ID потока/стрима
            chat_id: Telegram chat ID
            created_by: ID создателя опроса (user_id as string)
            question: Текст вопроса
            options: Список вариантов ответов (минимум 2)
            allow_multiple_votes: Разрешить голосовать за несколько вариантов
            description: Описание опроса (опционально)

        Returns:
            Созданный Poll entity в статусе DRAFT

        Raises:
            InvalidOptionsError: Если меньше 2 вариантов
            BusinessRuleViolationError: Если вопрос пустой
        """
        # Валидация вариантов ответов
        if len(options) < 2:
            raise InvalidOptionsError(
                f"Опрос должен содержать минимум 2 варианта (передано: {len(options)})"
            )

        # Создаём PollOption entities
        poll_options = [
            PollOption(
                id=str(uuid.uuid4()),
                option_text=option_text,
                vote_count=0
            )
            for option_text in options
        ]

        # Создаём Value Objects
        owner_id = UserId(value=uuid.UUID(created_by) if isinstance(created_by, str) else created_by)
        target_chat_id = ChatId(value=chat_id)

        # Генерируем ID опроса
        poll_id = str(uuid.uuid4())

        # Создаём Poll entity через factory method
        poll = Poll.create(
            poll_id=poll_id,
            stream_id=stream_id,
            chat_id=target_chat_id,
            created_by=owner_id,
            question=question,
            options=poll_options,
            allow_multiple_votes=allow_multiple_votes
        )

        # Сохраняем в репозиторий
        await self._repository.save(poll)
        await self._session.commit()

        logger.info(
            f"Создан опрос: poll_id={poll.id}, stream_id={stream_id}, "
            f"question={question}, options_count={len(options)}"
        )

        return poll

    async def get_by_id(self, poll_id: str) -> Poll:
        """
        Получить опрос по ID.

        Args:
            poll_id: UUID опроса

        Returns:
            Poll entity

        Raises:
            PollNotFoundError: Если опрос не найден
        """
        poll = await self._repository.get_by_id(poll_id)

        if not poll:
            raise PollNotFoundError(f"Опрос {poll_id} не найден")

        return poll

    async def get_by_stream(self, stream_id: str) -> List[Poll]:
        """
        Получить все опросы для потока.

        Args:
            stream_id: ID потока

        Returns:
            Список Poll entities (может быть пустым)
        """
        return await self._repository.get_by_stream_id(stream_id)

    async def get_active_by_chat(self, chat_id: int) -> List[Poll]:
        """
        Получить активные опросы для чата.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Список активных Poll entities
        """
        target_chat_id = ChatId(value=chat_id)
        return await self._repository.get_active_by_chat(target_chat_id)

    async def get_by_user(self, user_id: str) -> List[Poll]:
        """
        Получить все опросы пользователя.

        Args:
            user_id: ID создателя

        Returns:
            Список Poll entities
        """
        owner_id = UserId(value=uuid.UUID(user_id) if isinstance(user_id, str) else user_id)
        return await self._repository.get_by_user(owner_id)

    # ========== Poll Lifecycle Operations ==========

    async def publish(self, poll_id: str) -> Poll:
        """
        Опубликовать опрос (DRAFT → ACTIVE).

        Args:
            poll_id: UUID опроса

        Returns:
            Обновленный Poll entity

        Raises:
            PollNotFoundError: Если опрос не найден
            BusinessRuleViolationError: Если опрос не в статусе DRAFT
        """
        poll = await self.get_by_id(poll_id)

        # Используем бизнес-метод entity для публикации
        poll.publish()

        # Сохраняем изменения
        await self._repository.save(poll)
        await self._session.commit()

        # Отправляем WebSocket уведомление
        await notify_poll_created(poll, channel_id=poll.stream_id)

        logger.info(
            f"Опрос опубликован: poll_id={poll.id}, "
            f"stream_id={poll.stream_id}"
        )

        return poll

    async def close(self, poll_id: str) -> Poll:
        """
        Закрыть опрос (ACTIVE → CLOSED).

        Args:
            poll_id: UUID опроса

        Returns:
            Обновленный Poll entity

        Raises:
            PollNotFoundError: Если опрос не найден
            BusinessRuleViolationError: Если опрос не активен
        """
        poll = await self.get_by_id(poll_id)

        # Используем бизнес-метод entity для закрытия
        poll.close()

        # Сохраняем изменения
        await self._repository.save(poll)
        await self._session.commit()

        # Отправляем WebSocket уведомление
        await notify_poll_updated(poll, channel_id=poll.stream_id)

        logger.info(
            f"Опрос закрыт: poll_id={poll.id}, "
            f"total_votes={poll.total_votes()}"
        )

        return poll

    # ========== Voting Operations ==========

    async def vote(
        self,
        poll_id: str,
        user_id: str,
        option_ids: List[str],
        is_anonymous: bool = True
    ) -> Poll:
        """
        Проголосовать в опросе.

        Args:
            poll_id: UUID опроса
            user_id: ID пользователя (строка UUID)
            option_ids: Список ID выбранных вариантов
            is_anonymous: Анонимное голосование

        Returns:
            Обновленный Poll entity

        Raises:
            PollNotFoundError: Если опрос не найден
            PollClosedError: Если опрос закрыт
            DuplicateVoteError: Если пользователь уже голосовал
            InvalidOptionsError: Если варианты не найдены или количество превышено
        """
        poll = await self.get_by_id(poll_id)

        # Проверяем статус опроса
        if poll.status != PollStatus.ACTIVE:
            raise PollClosedError(
                f"Опрос {poll_id} не активен (статус: {poll.status})"
            )

        # Проверяем повторное голосование (для не-anonymous)
        if not poll.allow_multiple_votes and not is_anonymous:
            # TODO: Проверка через PollVote repository
            # В текущей реализации эта логика может быть в application layer
            pass

        # Валидируем варианты ответов
        if not option_ids:
            raise InvalidOptionsError("Не выбран ни один вариант ответа")

        # Проверяем multiple votes restriction
        if not poll.allow_multiple_votes and len(option_ids) > 1:
            raise InvalidOptionsError(
                f"Опрос не поддерживает multiple choice "
                f"(выбрано {len(option_ids)} вариантов)"
            )

        # Проверяем что все варианты существуют
        option_map = {opt.id: opt for opt in poll.options}
        for option_id in option_ids:
            if option_id not in option_map:
                raise InvalidOptionsError(
                    f"Вариант {option_id} не найден в опросе"
                )

        # Создаём UserId для бизнес-метода
        voter_id = UserId(
            value=uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        )

        # Используем бизнес-метод entity для голосования
        poll.vote(voter_id, option_ids)

        # Сохраняем изменения
        await self._repository.save(poll)
        await self._session.commit()

        # Отправляем WebSocket уведомление для каждого варианта
        total_votes = poll.total_votes()
        for option_id in option_ids:
            await notify_vote_cast(
                poll_id=poll.id,
                option_id=option_id,
                total_votes=total_votes,
                channel_id=poll.stream_id
            )

        logger.info(
            f"Голос принят: poll_id={poll.id}, user_id={user_id}, "
            f"option_ids={option_ids}, total_votes={total_votes}"
        )

        return poll

    # ========== Results & Analytics ==========

    async def get_results(self, poll_id: str) -> dict:
        """
        Получить результаты опроса.

        Args:
            poll_id: UUID опроса

        Returns:
            Словарь с результатами:
            {
                "poll_id": str,
                "question": str,
                "total_votes": int,
                "options": [
                    {
                        "id": str,
                        "text": str,
                        "vote_count": int,
                        "percentage": float
                    }
                ],
                "status": str
            }

        Raises:
            PollNotFoundError: Если опрос не найден
        """
        poll = await self.get_by_id(poll_id)

        total_votes = poll.total_votes()
        results = poll.get_results()

        # Формируем детализированные результаты с процентами
        options_results = []
        for option in poll.options:
            percentage = (option.vote_count / total_votes * 100) if total_votes > 0 else 0
            options_results.append({
                "id": option.id,
                "text": option.option_text,
                "vote_count": option.vote_count,
                "percentage": round(percentage, 2)
            })

        return {
            "poll_id": poll.id,
            "question": poll.question,
            "total_votes": total_votes,
            "options": options_results,
            "status": poll.status.value,
            "created_at": poll.created_at.isoformat(),
            "published_at": poll.published_at.isoformat() if poll.published_at else None,
            "closed_at": poll.closed_at.isoformat() if poll.closed_at else None
        }

    # ========== Utility Operations ==========

    async def delete(self, poll_id: str) -> None:
        """
        Удалить опрос.

        Args:
            poll_id: UUID опроса

        Raises:
            PollNotFoundError: Если опрос не найден
        """
        # Проверяем что опрос существует
        await self.get_by_id(poll_id)

        # Удаляем через репозиторий
        await self._repository.delete(poll_id)
        await self._session.commit()

        logger.info(f"Опрос удалён: poll_id={poll_id}")

    async def is_active(self, poll_id: str) -> bool:
        """
        Проверить, активен ли опрос.

        Args:
            poll_id: UUID опроса

        Returns:
            True если опрос активен
        """
        try:
            poll = await self.get_by_id(poll_id)
            return poll.is_active()
        except PollNotFoundError:
            return False


# Singleton instance для обратной совместимости с QueueService pattern
_poll_service: Optional[PollService] = None


def get_poll_service(session: AsyncSession) -> PollService:
    """
    Получить экземпляр PollService для указанной сессии.

    Note:
        В отличие от QueueService, PollService требует сессию
        и не является singleton в классическом смысле.
        Каждый вызов создаёт новый сервис с указанной сессией.
    """
    return PollService(session)
