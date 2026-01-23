"""
Chat Aggregator Service
Feature: 021-social-media-integration-cross-platform-broadcasting

Сервис для сбора и нормализации сообщений чата со всех платформ:
- Сбор сообщений из Telegram, YouTube, Twitch, других платформ
- Нормализация в единый формат
- Дедупликация сообщений
- Кэширование агрегированных сообщений
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import Session

from src.models.chat_message import ChatMessage
from src.models.streaming_platform import StreamingPlatform
from src.schemas.streaming_platforms import (
    ChatMessageResponse,
    ChatMessageListResponse,
    ChatMessageAggregatedResponse,
    ChatMessageCreate,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "chat_aggregator:"
CACHE_MESSAGES_KEY = f"{CACHE_PREFIX}messages:{{channel_id}}:{{platform_id}}"
CACHE_AGGREGATED_KEY = f"{CACHE_PREFIX}aggregated:{{channel_id}}"
CACHE_TTL = 60  # 1 minute for real-time chat


class ChatAggregator:
    """
    Сервис агрегации чата с Redis кэшированием.

    Методы:
    - add_message: Добавить сообщение из чата платформы
    - get_messages: Получить сообщения для канала/платформы
    - get_aggregated_messages: Получить агрегированные сообщения со всех платформ
    - delete_message: Удалить сообщение (по желанию пользователя или модератора)
    - clear_channel_cache: Очистить кэш сообщений канала
    """

    def __init__(self, db: Session, redis_client: Optional["aioredis.Redis"] = None):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
            redis_client: Опциональный Redis клиент для кэширования
        """
        self.db = db
        self.redis = redis_client

    async def _get_from_cache(self, key: str) -> Optional[dict]:
        """Получение данных из кэша Redis."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    async def _set_to_cache(self, key: str, data: dict, ttl: int = CACHE_TTL) -> None:
        """Сохранение данных в кэш Redis."""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    async def _delete_from_cache(self, key: str) -> None:
        """Удаление данных из кэша Redis."""
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis cache delete error: {e}")

    def _serialize_message(self, message: ChatMessage) -> dict:
        """
        Сериализация сообщения чата в словарь.

        Args:
            message: Объект ChatMessage

        Returns:
            Словарь с данными сообщения
        """
        return {
            "id": str(message.id),
            "platform_id": str(message.platform_id),
            "channel_id": str(message.channel_id),
            "platform_message_id": message.platform_message_id,
            "author_name": message.author_name,
            "author_display_name": message.author_display_name,
            "content": message.content,
            "message_timestamp": message.message_timestamp.isoformat(),
            "author_color": message.author_color,
            "metadata": json.loads(message.metadata) if message.metadata else None,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }

    async def add_message(self, message_data: ChatMessageCreate) -> ChatMessageResponse:
        """
        Добавить сообщение из чата платформы.

        Args:
            message_data: Данные сообщения для создания

        Returns:
            ChatMessageResponse с созданным сообщением

        Raises:
            ValueError: Если сообщение с таким platform_message_id уже существует
        """
        # Проверка на дубликаты
        existing = self.db.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.platform_id == message_data.platform_id,
                    ChatMessage.platform_message_id == message_data.platform_message_id
                )
            ).limit(1)
        ).scalar_one_or_none()

        if existing:
            logger.debug(
                f"Duplicate message ignored: platform_id={message_data.platform_id}, "
                f"platform_message_id={message_data.platform_message_id}"
            )
            # Возвращаем существующее сообщение вместо ошибки
            return ChatMessageResponse.model_validate(existing)

        # Создание нового сообщения
        chat_message = ChatMessage(
            platform_id=message_data.platform_id,
            channel_id=message_data.channel_id,
            platform_message_id=message_data.platform_message_id,
            author_name=message_data.author_name,
            author_display_name=message_data.author_display_name,
            content=message_data.content,
            message_timestamp=message_data.message_timestamp,
            author_color=message_data.author_color,
            metadata=json.dumps(message_data.metadata) if message_data.metadata else None,
        )

        self.db.add(chat_message)
        self.db.commit()
        self.db.refresh(chat_message)

        # Очистка кэша для этого канала
        await self.clear_channel_cache(message_data.channel_id)

        logger.info(
            f"Chat message added: id={chat_message.id}, "
            f"platform={message_data.platform_id}, author={message_data.author_name}"
        )

        return ChatMessageResponse.model_validate(chat_message)

    async def add_message_batch(
        self,
        messages: List[ChatMessageCreate]
    ) -> List[ChatMessageResponse]:
        """
        Добавить пакет сообщений из чата платформы.

        Args:
            messages: Список данных сообщений для создания

        Returns:
            Список ChatMessageResponse с созданными сообщениями
        """
        created_messages = []
        channel_ids = set()

        for message_data in messages:
            try:
                result = await self.add_message(message_data)
                created_messages.append(result)
                channel_ids.add(str(message_data.channel_id))
            except Exception as e:
                logger.error(f"Error adding message batch item: {e}")
                # Продолжаем обработку остальных сообщений
                continue

        # Очищаем кэш для всех затронутых каналов
        for channel_id in channel_ids:
            await self.clear_channel_cache(channel_id)

        return created_messages

    async def get_messages(
        self,
        channel_id: UUID,
        platform_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
        since: Optional[datetime] = None
    ) -> ChatMessageListResponse:
        """
        Получить сообщения для канала/платформы.

        Args:
            channel_id: ID канала
            platform_id: Опциональный ID платформы для фильтрации
            limit: Количество сообщений (1-1000)
            offset: Смещение для пагинации
            since: Опциональная дата для получения сообщений с определенного времени

        Returns:
            ChatMessageListResponse с сообщениями
        """
        # Проверка кэша (только для простых запросов без since)
        cache_key = None
        if since is None and platform_id is not None:
            cache_key = CACHE_MESSAGES_KEY.format(
                channel_id=str(channel_id),
                platform_id=str(platform_id)
            )
            cached = await self._get_from_cache(cache_key)
            if cached:
                return ChatMessageListResponse(**cached)

        # Формирование запроса
        query = select(ChatMessage).where(ChatMessage.channel_id == channel_id)

        if platform_id:
            query = query.where(ChatMessage.platform_id == platform_id)

        if since:
            query = query.where(ChatMessage.message_timestamp >= since)

        # Получение общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Применение пагинации и сортировки
        query = query.order_by(desc(ChatMessage.message_timestamp)).limit(limit).offset(offset)

        messages = self.db.execute(query).scalars().all()

        result = ChatMessageListResponse(
            messages=[ChatMessageResponse.model_validate(msg) for msg in messages],
            total=total
        )

        # Кэшируем только простые запросы
        if cache_key:
            await self._set_to_cache(cache_key, result.model_dump())

        return result

    async def get_aggregated_messages(
        self,
        channel_id: UUID,
        limit: int = 100,
        offset: int = 0,
        since: Optional[datetime] = None
    ) -> ChatMessageAggregatedResponse:
        """
        Получить агрегированные сообщения со всех платформ канала.

        Args:
            channel_id: ID канала
            limit: Количество сообщений (1-1000)
            offset: Смещение для пагинации
            since: Опциональная дата для получения сообщений с определенного времени

        Returns:
            ChatMessageAggregatedResponse с сообщениями и списком платформ
        """
        # Проверка кэша (только для простых запросов без since)
        cache_key = None
        if since is None:
            cache_key = CACHE_AGGREGATED_KEY.format(channel_id=str(channel_id))
            cached = await self._get_from_cache(cache_key)
            if cached:
                return ChatMessageAggregatedResponse(**cached)

        # Формирование запроса
        query = select(ChatMessage).where(ChatMessage.channel_id == channel_id)

        if since:
            query = query.where(ChatMessage.message_timestamp >= since)

        # Получение общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Применение пагинации и сортировки
        query = query.order_by(desc(ChatMessage.message_timestamp)).limit(limit).offset(offset)

        messages = self.db.execute(query).scalars().all()

        # Получение уникальных платформ
        platforms_query = (
            select(ChatMessage.platform_id)
            .where(ChatMessage.channel_id == channel_id)
            .distinct()
        )
        if since:
            platforms_query = platforms_query.where(ChatMessage.message_timestamp >= since)

        platform_ids = [str(row[0]) for row in self.db.execute(platforms_query).fetchall()]

        # Получение информации о платформах
        platforms_info = {}
        if platform_ids:
            platforms = self.db.execute(
                select(StreamingPlatform).where(StreamingPlatform.id.in_(platform_ids))
            ).scalars().all()
            platforms_info = {
                str(p.id): {
                    "platform_type": p.platform_type,
                    "platform_name": p.platform_name,
                }
                for p in platforms
            }

        # Обогащение сообщений информацией о платформах
        messages_with_platform = []
        for msg in messages:
            msg_dict = ChatMessageResponse.model_validate(msg).model_dump()
            if str(msg.platform_id) in platforms_info:
                msg_dict["platform_info"] = platforms_info[str(msg.platform_id)]
            messages_with_platform.append(ChatMessageResponse(**msg_dict))

        result = ChatMessageAggregatedResponse(
            channel_id=str(channel_id),
            messages=messages_with_platform,
            platforms=list(platform_ids),
            total=total
        )

        # Кэшируем только простые запросы
        if cache_key:
            await self._set_to_cache(cache_key, result.model_dump())

        return result

    async def delete_message(self, message_id: UUID) -> bool:
        """
        Удалить сообщение (по желанию пользователя или модератора).

        Args:
            message_id: ID сообщения для удаления

        Returns:
            True если сообщение было удалено, False если не найдено
        """
        message = self.db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        ).scalar_one_or_none()

        if not message:
            return False

        channel_id = message.channel_id

        self.db.delete(message)
        self.db.commit()

        # Очистка кэша
        await self.clear_channel_cache(channel_id)

        logger.info(f"Chat message deleted: id={message_id}")
        return True

    async def clear_channel_cache(self, channel_id: UUID) -> None:
        """
        Очистить кэш сообщений канала.

        Args:
            channel_id: ID канала для очистки кэша
        """
        if not self.redis:
            return

        try:
            # Удаляем все ключи кэша для этого канала
            pattern = f"{CACHE_PREFIX}*:{str(channel_id)}:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.debug(f"Cleared {len(keys)} cache keys for channel {channel_id}")
        except Exception as e:
            logger.warning(f"Error clearing channel cache: {e}")

    async def get_message_stats(
        self,
        channel_id: UUID,
        platform_id: Optional[UUID] = None,
        period: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получить статистику сообщений для канала/платформы.

        Args:
            channel_id: ID канала
            platform_id: Опциональный ID платформы для фильтрации
            period: Опциональный период в часах (по умолчанию 24 часа)

        Returns:
            Словарь со статистикой: total_messages, unique_authors, platforms_count
        """
        period_hours = period or 24
        since = datetime.now(timezone.utc) - timedelta(hours=period_hours)

        # Базовый запрос с фильтром по времени
        query = select(ChatMessage).where(
            and_(
                ChatMessage.channel_id == channel_id,
                ChatMessage.message_timestamp >= since
            )
        )

        if platform_id:
            query = query.where(ChatMessage.platform_id == platform_id)

        # Общее количество сообщений
        count_query = select(func.count()).select_from(query.subquery())
        total_messages = self.db.execute(count_query).scalar() or 0

        # Уникальные авторы
        authors_query = select(func.count(func.distinct(ChatMessage.author_name))).select_from(query.subquery())
        unique_authors = self.db.execute(authors_query).scalar() or 0

        # Количество платформ (если не указана конкретная платформа)
        platforms_count = 0
        if platform_id is None:
            platforms_query = select(func.count(func.distinct(ChatMessage.platform_id))).select_from(query.subquery())
            platforms_count = self.db.execute(platforms_query).scalar() or 0
        else:
            platforms_count = 1

        return {
            "total_messages": total_messages,
            "unique_authors": unique_authors,
            "platforms_count": platforms_count,
            "period_hours": period_hours,
            "since": since.isoformat(),
        }


def get_chat_aggregator(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> ChatAggregator:
    """
    Фабрика для создания сервиса агрегации чата.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент

    Returns:
        ChatAggregator instance
    """
    return ChatAggregator(db=db, redis_client=redis_client)
