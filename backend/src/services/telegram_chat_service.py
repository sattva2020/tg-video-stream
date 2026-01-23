"""
Telegram Chat Service
Сервис для интеграции Telegram чата с stream overlay.

Функции:
- Capture сообщений из Telegram чата
- Сохранение в ChatMessage модель
- WebSocket уведомления для real-time отображения
- Модерация контента
- Управление отображением на overlay

Автор: Jarvis
Дата: 2025-12-29
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interaction import ChatMessage, ChatMessageStatus
from src.api.websocket import notify_chat_message
from src.services.moderation_service import ModerationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramChatService:
    """Сервис для управления Telegram чатом на stream overlay."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session: Async SQLAlchemy сессия
        """
        self.session = session
        self.moderation = ModerationService(session)

    async def capture_message(
        self,
        stream_id: str,
        telegram_message_id: int,
        content: str,
        author_name: str,
        telegram_user_id: int,
        author_avatar_url: Optional[str] = None,
        author_id: Optional[str] = None,
        original_timestamp: Optional[datetime] = None
    ) -> Optional[ChatMessage]:
        """
        Захватить сообщение из Telegram для отображения на overlay.

        Args:
            stream_id: ID потока
            telegram_message_id: ID сообщения из Telegram
            content: Текст сообщения
            author_name: Имя автора
            telegram_user_id: Telegram ID автора
            author_avatar_url: URL аватара (опционально)
            author_id: ID авторизованного пользователя (если есть)
            original_timestamp: Оригинальное время отправки в Telegram

        Returns:
            ChatMessage ORM модель или None если сообщение отфильтровано

        Raises:
            ValueError: При неверных аргументах
        """
        try:
            # Проверка модерации
            moderation_result = await self.moderation.check_chat_message(content)
            if moderation_result['is_filtered']:
                logger.info(
                    f"Сообщение отфильтровано: user={author_name}, "
                    f"reason={moderation_result['reason']}"
                )
                # Создаем сообщение как скрытое
                chat_message = ChatMessage(
                    stream_id=stream_id,
                    author_id=author_id,
                    telegram_user_id=telegram_user_id,
                    author_name=author_name,
                    author_avatar_url=author_avatar_url,
                    content=content,
                    telegram_message_id=telegram_message_id,
                    original_timestamp=original_timestamp or datetime.now(),
                    message_status=ChatMessageStatus.HIDDEN,
                    is_filtered=True,
                    filter_reason=moderation_result['reason']
                )
                self.session.add(chat_message)
                await self.session.flush()
                return None

            # Создаем сообщение
            chat_message = ChatMessage(
                stream_id=stream_id,
                author_id=author_id,
                telegram_user_id=telegram_user_id,
                author_name=author_name,
                author_avatar_url=author_avatar_url,
                content=content,
                telegram_message_id=telegram_message_id,
                original_timestamp=original_timestamp or datetime.now(),
                message_status=ChatMessageStatus.PENDING,
                is_filtered=False
            )

            self.session.add(chat_message)
            await self.session.flush()

            logger.info(
                f"Сообщение захвачено: id={chat_message.id}, "
                f"author={author_name}, stream={stream_id}"
            )

            # WebSocket уведомление
            await notify_chat_message(
                stream_id=stream_id,
                message_id=str(chat_message.id),
                author_name=author_name,
                content=content
            )

            return chat_message

        except Exception as e:
            logger.error(f"Ошибка захвата сообщения: {e}")
            raise

    async def update_edited_message(
        self,
        telegram_message_id: int,
        new_content: str
    ) -> Optional[ChatMessage]:
        """
        Обновить отредактированное сообщение.

        Args:
            telegram_message_id: ID сообщения из Telegram
            new_content: Новое содержимое

        Returns:
            Обновленный ChatMessage или None если не найден
        """
        try:
            from sqlalchemy import select

            stmt = select(ChatMessage).where(
                ChatMessage.telegram_message_id == telegram_message_id
            )
            result = await self.session.execute(stmt)
            chat_message = result.scalar_one_or_none()

            if not chat_message:
                logger.warning(
                    f"Сообщение не найдено для обновления: telegram_id={telegram_message_id}"
                )
                return None

            # Проверка модерации нового содержания
            moderation_result = await self.moderation.check_chat_message(new_content)
            if moderation_result['is_filtered']:
                chat_message.content = new_content
                chat_message.message_status = ChatMessageStatus.HIDDEN
                chat_message.is_filtered = True
                chat_message.filter_reason = moderation_result['reason']
            else:
                chat_message.content = new_content

            await self.session.flush()

            logger.info(
                f"Сообщение обновлено: id={chat_message.id}, "
                "filtered={moderation_result['is_filtered']}"
            )

            return chat_message

        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")
            raise

    async def get_visible_messages(
        self,
        stream_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """
        Получить видимые сообщения для потока.

        Args:
            stream_id: ID потока
            limit: Максимальное количество сообщений

        Returns:
            Список ChatMessage ORM моделей
        """
        try:
            from sqlalchemy import select, desc

            stmt = (
                select(ChatMessage)
                .where(ChatMessage.stream_id == stream_id)
                .where(ChatMessage.message_status == ChatMessageStatus.VISIBLE)
                .where(ChatMessage.is_filtered == False)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            messages = result.scalars().all()

            return list(messages)

        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")
            return []

    async def hide_message(self, message_id: str) -> bool:
        """
        Скрыть сообщение (модерация).

        Args:
            message_id: ID сообщения

        Returns:
            True если успешно, False если сообщение не найдено
        """
        try:
            from sqlalchemy import select

            stmt = select(ChatMessage).where(ChatMessage.id == message_id)
            result = await self.session.execute(stmt)
            chat_message = result.scalar_one_or_none()

            if not chat_message:
                return False

            chat_message.message_status = ChatMessageStatus.HIDDEN
            await self.session.flush()

            logger.info(f"Сообщение скрыто: id={message_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка скрытия сообщения: {e}")
            return False

    async def flag_message(self, message_id: str) -> bool:
        """
        Пометить сообщение для проверки.

        Args:
            message_id: ID сообщения

        Returns:
            True если успешно, False если сообщение не найдено
        """
        try:
            from sqlalchemy import select

            stmt = select(ChatMessage).where(ChatMessage.id == message_id)
            result = await self.session.execute(stmt)
            chat_message = result.scalar_one_or_none()

            if not chat_message:
                return False

            chat_message.is_flagged = True
            chat_message.message_status = ChatMessageStatus.FLAGGED
            await self.session.flush()

            logger.info(f"Сообщение помечено: id={message_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка пометки сообщения: {e}")
            return False

    async def get_message_by_telegram_id(
        self,
        telegram_message_id: int
    ) -> Optional[ChatMessage]:
        """
        Получить сообщение по Telegram ID.

        Args:
            telegram_message_id: ID сообщения из Telegram

        Returns:
            ChatMessage ORM модель или None
        """
        try:
            from sqlalchemy import select

            stmt = select(ChatMessage).where(
                ChatMessage.telegram_message_id == telegram_message_id
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Ошибка поиска сообщения: {e}")
            return None

    async def get_chat_statistics(
        self,
        stream_id: str
    ) -> Dict[str, Any]:
        """
        Получить статистику чата для потока.

        Args:
            stream_id: ID потока

        Returns:
            Словарь со статистикой
        """
        try:
            from sqlalchemy import select, func

            # Общее количество сообщений
            total_stmt = select(func.count(ChatMessage.id)).where(
                ChatMessage.stream_id == stream_id
            )
            total_result = await self.session.execute(total_stmt)
            total_messages = total_result.scalar() or 0

            # Количество уникальных авторов
            authors_stmt = select(func.count(func.distinct(ChatMessage.telegram_user_id))).where(
                ChatMessage.stream_id == stream_id
            )
            authors_result = await self.session.execute(authors_stmt)
            unique_authors = authors_result.scalar() or 0

            # Количество отфильтрованных сообщений
            filtered_stmt = select(func.count(ChatMessage.id)).where(
                ChatMessage.stream_id == stream_id,
                ChatMessage.is_filtered == True
            )
            filtered_result = await self.session.execute(filtered_stmt)
            filtered_messages = filtered_result.scalar() or 0

            return {
                'total_messages': total_messages,
                'unique_authors': unique_authors,
                'filtered_messages': filtered_messages,
                'visible_messages': total_messages - filtered_messages
            }

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total_messages': 0,
                'unique_authors': 0,
                'filtered_messages': 0,
                'visible_messages': 0
            }
