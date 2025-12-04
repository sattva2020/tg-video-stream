"""
Queue Service - управление очередью воспроизведения

Сервис обеспечивает:
- Добавление/удаление элементов очереди
- Перемещение элементов (изменение порядка)
- Приоритетное добавление (в начало)
- Пропуск текущего трека
- Получение следующего элемента
- Redis persistence с ключами stream_queue:{channel_id}

Storage: Redis List (LPUSH/RPUSH/LRANGE/LREM/LINDEX)
"""

from datetime import datetime, timezone
from typing import Optional
import logging
import json

import redis.asyncio as redis

from src.config import settings
from src.models.queue import (
    QueueItem,
    QueueItemCreate,
    QueueInfo,
    QueueOperation,
    QueueSource,
)

logger = logging.getLogger(__name__)


class QueueServiceError(Exception):
    """Базовое исключение для ошибок QueueService."""
    pass


class QueueFullError(QueueServiceError):
    """Очередь достигла максимального размера."""
    pass


class QueueEmptyError(QueueServiceError):
    """Очередь пуста."""
    pass


class ItemNotFoundError(QueueServiceError):
    """Элемент не найден в очереди."""
    pass


class InvalidPositionError(QueueServiceError):
    """Некорректная позиция для перемещения."""
    pass


class QueueService:
    """
    Сервис управления очередью воспроизведения.
    
    Использует Redis List для хранения очереди:
    - stream_queue:{channel_id} → LIST of JSON QueueItem
    
    Attributes:
        max_queue_size: Максимальный размер очереди (по умолчанию 100)
        redis_url: URL подключения к Redis
    """
    
    # Redis key pattern
    REDIS_KEY_PREFIX = "stream_queue"
    
    # Максимальный размер очереди (из спецификации)
    DEFAULT_MAX_QUEUE_SIZE = 100
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
    ):
        """
        Инициализация QueueService.
        
        Args:
            redis_url: URL Redis (по умолчанию из settings)
            max_queue_size: Максимальный размер очереди
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_queue_size = max_queue_size
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента с lazy initialization."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis
    
    async def close(self) -> None:
        """Закрытие Redis соединения."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
    
    @staticmethod
    def _get_queue_key(channel_id: int) -> str:
        """Генерация Redis ключа для очереди канала."""
        return QueueItem.get_queue_key(channel_id)
    
    # ========== CRUD Operations ==========
    
    async def add(
        self,
        channel_id: int,
        item_create: QueueItemCreate,
        requested_by: Optional[int] = None
    ) -> QueueItem:
        """
        Добавить элемент в конец очереди (RPUSH).
        
        Args:
            channel_id: ID Telegram канала
            item_create: Данные для создания элемента
            requested_by: ID пользователя, запросившего добавление
            
        Returns:
            Созданный QueueItem
            
        Raises:
            QueueFullError: Если очередь достигла максимального размера
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Проверка лимита очереди
        current_size = await r.llen(key)
        if current_size >= self.max_queue_size:
            raise QueueFullError(
                f"Очередь канала {channel_id} достигла максимального размера "
                f"({self.max_queue_size} элементов)"
            )
        
        # Создание QueueItem
        item = QueueItem(
            channel_id=channel_id,
            title=item_create.title,
            url=item_create.url,
            duration=item_create.duration,
            source=item_create.source,
            requested_by=requested_by,
            metadata=item_create.metadata or {}
        )
        
        # Сохранение в Redis (в конец списка)
        await r.rpush(key, item.to_redis_json())
        
        logger.info(
            f"Добавлен элемент в очередь: channel={channel_id}, "
            f"item_id={item.id}, title={item.title}"
        )
        
        return item
    
    async def add_priority(
        self,
        channel_id: int,
        item_create: QueueItemCreate,
        requested_by: Optional[int] = None
    ) -> QueueItem:
        """
        Добавить элемент в начало очереди (приоритетное добавление, LPUSH).
        
        Args:
            channel_id: ID Telegram канала
            item_create: Данные для создания элемента
            requested_by: ID пользователя
            
        Returns:
            Созданный QueueItem
            
        Raises:
            QueueFullError: Если очередь полна
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Проверка лимита
        current_size = await r.llen(key)
        if current_size >= self.max_queue_size:
            raise QueueFullError(
                f"Очередь канала {channel_id} достигла максимального размера"
            )
        
        # Создание QueueItem
        item = QueueItem(
            channel_id=channel_id,
            title=item_create.title,
            url=item_create.url,
            duration=item_create.duration,
            source=item_create.source,
            requested_by=requested_by,
            metadata=item_create.metadata or {}
        )
        
        # Сохранение в начало списка
        await r.lpush(key, item.to_redis_json())
        
        logger.info(
            f"Приоритетно добавлен элемент: channel={channel_id}, "
            f"item_id={item.id}, title={item.title}"
        )
        
        return item
    
    async def remove(self, channel_id: int, item_id: str) -> bool:
        """
        Удалить элемент из очереди по ID.
        
        Args:
            channel_id: ID Telegram канала
            item_id: UUID элемента
            
        Returns:
            True если элемент удален
            
        Raises:
            ItemNotFoundError: Если элемент не найден
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Получаем все элементы
        items_json = await r.lrange(key, 0, -1)
        
        # Ищем элемент
        for item_json in items_json:
            try:
                item = QueueItem.from_redis_json(item_json)
                if item.id == item_id:
                    # Удаляем (LREM удаляет по значению)
                    removed = await r.lrem(key, 1, item_json)
                    if removed > 0:
                        logger.info(
                            f"Удален элемент из очереди: channel={channel_id}, "
                            f"item_id={item_id}"
                        )
                        return True
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга элемента очереди: {e}")
                continue
        
        raise ItemNotFoundError(
            f"Элемент {item_id} не найден в очереди канала {channel_id}"
        )
    
    async def move(
        self,
        channel_id: int,
        item_id: str,
        new_position: int
    ) -> list[QueueItem]:
        """
        Переместить элемент на новую позицию.
        
        Args:
            channel_id: ID Telegram канала
            item_id: UUID элемента
            new_position: Новая позиция (0 = первый)
            
        Returns:
            Обновленный список очереди
            
        Raises:
            ItemNotFoundError: Если элемент не найден
            InvalidPositionError: Если позиция некорректна
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Получаем все элементы
        items_json = await r.lrange(key, 0, -1)
        items = []
        target_index = -1
        target_item = None
        
        for i, item_json in enumerate(items_json):
            try:
                item = QueueItem.from_redis_json(item_json)
                items.append(item)
                if item.id == item_id:
                    target_index = i
                    target_item = item
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга: {e}")
                continue
        
        if target_index == -1 or target_item is None:
            raise ItemNotFoundError(
                f"Элемент {item_id} не найден в очереди канала {channel_id}"
            )
        
        # Валидация позиции
        if new_position < 0 or new_position >= len(items):
            raise InvalidPositionError(
                f"Некорректная позиция {new_position}. "
                f"Допустимый диапазон: 0-{len(items) - 1}"
            )
        
        # Если позиция не изменилась
        if target_index == new_position:
            return items
        
        # Перемещение элемента
        items.pop(target_index)
        items.insert(new_position, target_item)
        
        # Атомарное обновление в Redis (через pipeline)
        async with r.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            for item in items:
                await pipe.rpush(key, item.to_redis_json())
            await pipe.execute()
        
        logger.info(
            f"Перемещен элемент: channel={channel_id}, item_id={item_id}, "
            f"from={target_index}, to={new_position}"
        )
        
        return items
    
    # ========== Query Operations ==========
    
    async def get_all(
        self,
        channel_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> QueueInfo:
        """
        Получить очередь канала с пагинацией.
        
        Args:
            channel_id: ID Telegram канала
            limit: Максимальное количество элементов
            offset: Смещение
            
        Returns:
            QueueInfo с элементами и метаданными
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Общее количество
        total = await r.llen(key)
        
        # Получение с пагинацией
        start = offset
        end = offset + limit - 1
        items_json = await r.lrange(key, start, end)
        
        items = []
        total_duration = 0
        
        for item_json in items_json:
            try:
                item = QueueItem.from_redis_json(item_json)
                items.append(item)
                if item.duration:
                    total_duration += item.duration
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга элемента: {e}")
                continue
        
        return QueueInfo(
            channel_id=channel_id,
            items=items,
            total_items=total,
            total_duration=total_duration
        )
    
    async def get_next(self, channel_id: int) -> Optional[QueueItem]:
        """
        Получить следующий элемент очереди (без удаления).
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            QueueItem или None если очередь пуста
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # LINDEX 0 - первый элемент
        item_json = await r.lindex(key, 0)
        
        if item_json is None:
            return None
        
        try:
            return QueueItem.from_redis_json(item_json)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга следующего элемента: {e}")
            return None
    
    async def get_by_id(
        self,
        channel_id: int,
        item_id: str
    ) -> Optional[QueueItem]:
        """
        Получить элемент по ID.
        
        Args:
            channel_id: ID Telegram канала
            item_id: UUID элемента
            
        Returns:
            QueueItem или None
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        items_json = await r.lrange(key, 0, -1)
        
        for item_json in items_json:
            try:
                item = QueueItem.from_redis_json(item_json)
                if item.id == item_id:
                    return item
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None
    
    async def get_size(self, channel_id: int) -> int:
        """Получить размер очереди."""
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        return await r.llen(key)
    
    async def is_empty(self, channel_id: int) -> bool:
        """Проверить, пуста ли очередь."""
        return await self.get_size(channel_id) == 0
    
    # ========== Playback Operations ==========
    
    async def skip(self, channel_id: int) -> Optional[QueueItem]:
        """
        Пропустить текущий трек (удалить первый элемент).
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            Следующий QueueItem или None если очередь станет пустой
            
        Raises:
            QueueEmptyError: Если очередь уже пуста
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Проверка на пустую очередь
        if await r.llen(key) == 0:
            raise QueueEmptyError(f"Очередь канала {channel_id} пуста")
        
        # Удаляем первый элемент (LPOP)
        skipped_json = await r.lpop(key)
        
        if skipped_json:
            try:
                skipped = QueueItem.from_redis_json(skipped_json)
                logger.info(
                    f"Пропущен трек: channel={channel_id}, "
                    f"item_id={skipped.id}, title={skipped.title}"
                )
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Возвращаем следующий элемент
        return await self.get_next(channel_id)
    
    async def clear(self, channel_id: int) -> int:
        """
        Очистить очередь канала.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            Количество удаленных элементов
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Получаем размер перед удалением
        size = await r.llen(key)
        
        # Удаляем ключ
        await r.delete(key)
        
        logger.info(f"Очищена очередь: channel={channel_id}, items={size}")
        
        return size
    
    async def pop_next(self, channel_id: int) -> Optional[QueueItem]:
        """
        Извлечь следующий элемент (удаляет из очереди).
        
        Используется при переходе к следующему треку.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            QueueItem или None если очередь пуста
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        item_json = await r.lpop(key)
        
        if item_json is None:
            return None
        
        try:
            item = QueueItem.from_redis_json(item_json)
            logger.debug(
                f"Извлечен элемент: channel={channel_id}, item_id={item.id}"
            )
            return item
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга элемента: {e}")
            return None
    
    # ========== Utility Operations ==========
    
    async def get_position(
        self,
        channel_id: int,
        item_id: str
    ) -> Optional[int]:
        """
        Получить позицию элемента в очереди.
        
        Args:
            channel_id: ID Telegram канала
            item_id: UUID элемента
            
        Returns:
            Позиция (0-based) или None если не найден
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        items_json = await r.lrange(key, 0, -1)
        
        for i, item_json in enumerate(items_json):
            try:
                item = QueueItem.from_redis_json(item_json)
                if item.id == item_id:
                    return i
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None
    
    async def get_all_channel_ids(self) -> list[int]:
        """
        Получить список всех каналов с активными очередями.
        
        Returns:
            Список channel_id
        """
        r = await self._get_redis()
        pattern = f"{self.REDIS_KEY_PREFIX}:*"
        
        channel_ids = []
        async for key in r.scan_iter(match=pattern):
            try:
                # Извлекаем channel_id из ключа
                channel_id_str = key.split(":")[-1]
                channel_ids.append(int(channel_id_str))
            except (ValueError, IndexError):
                continue
        
        return channel_ids
    
    async def create_operation(
        self,
        operation_type: str,
        channel_id: int,
        item_id: Optional[str] = None,
        position: Optional[int] = None
    ) -> QueueOperation:
        """
        Создать объект операции для WebSocket уведомлений.
        
        Args:
            operation_type: Тип операции (add, remove, move, clear, skip)
            channel_id: ID канала
            item_id: ID элемента (опционально)
            position: Позиция (для move)
            
        Returns:
            QueueOperation для отправки через WebSocket
        """
        return QueueOperation(
            operation=operation_type,
            channel_id=channel_id,
            item_id=item_id,
            position=position
        )


# Singleton instance
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Получить singleton экземпляр QueueService."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service


async def shutdown_queue_service() -> None:
    """Закрыть QueueService при завершении приложения."""
    global _queue_service
    if _queue_service is not None:
        await _queue_service.close()
        _queue_service = None
