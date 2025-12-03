"""
Unified Queue Service

Объединенный сервис очереди, делегирующий операции между обычной и приоритетной очередями
на основе конфигурации канала.

Features:
- Автоматический выбор типа очереди (FIFO или Priority)
- Unified API для обоих типов очередей
- Плавная миграция между режимами
- Статистика использования VIP-очереди
"""

from typing import Optional, List
from enum import Enum
import logging

from src.models.queue import (
    QueueItem,
    QueueItemCreate,
    QueueInfo,
)
from src.models.user import User
from src.services.queue_service import (
    QueueService,
    get_queue_service,
    QueueFullError,
    QueueEmptyError,
    ItemNotFoundError,
    InvalidPositionError,
)
from src.services.priority_queue_service import (
    PriorityQueueService,
    get_priority_queue_service,
)

logger = logging.getLogger(__name__)


class QueueMode(str, Enum):
    """Режим работы очереди."""
    FIFO = "fifo"  # Обычная FIFO очередь (Redis LIST)
    PRIORITY = "priority"  # Приоритетная очередь (Redis SORTED SET)


# Глобальная конфигурация режима очереди для каждого канала
# В production должна браться из БД или Redis
CHANNEL_QUEUE_MODE: dict[int, QueueMode] = {}
DEFAULT_QUEUE_MODE = QueueMode.FIFO


class UnifiedQueueService:
    """
    Unified Queue Service - делегирует операции между обычной и приоритетной очередями.
    
    Позволяет плавно переключаться между режимами очереди без изменения API.
    """
    
    def __init__(self):
        self._fifo_service: QueueService = get_queue_service()
        self._priority_service: PriorityQueueService = get_priority_queue_service()
        logger.info("UnifiedQueueService initialized")
    
    def _get_mode(self, channel_id: int) -> QueueMode:
        """Получить режим очереди для канала."""
        return CHANNEL_QUEUE_MODE.get(channel_id, DEFAULT_QUEUE_MODE)
    
    async def set_mode(self, channel_id: int, mode: QueueMode) -> None:
        """
        Установить режим очереди для канала.
        
        ВАЖНО: При смене режима существующая очередь НЕ мигрируется автоматически.
        Рекомендуется очистить очередь перед сменой режима.
        """
        old_mode = self._get_mode(channel_id)
        if old_mode != mode:
            logger.warning(
                f"Changing queue mode for channel {channel_id}: {old_mode} -> {mode}. "
                "Existing queue items will NOT be migrated automatically!"
            )
        
        CHANNEL_QUEUE_MODE[channel_id] = mode
        logger.info(f"Queue mode set to {mode} for channel {channel_id}")
    
    async def migrate_queue(self, channel_id: int, from_mode: QueueMode, to_mode: QueueMode) -> int:
        """
        Мигрировать очередь из одного режима в другой.
        
        Returns:
            Количество перенесенных элементов
        """
        if from_mode == to_mode:
            logger.warning(f"Source and target modes are the same: {from_mode}")
            return 0
        
        # Получить все элементы из исходной очереди
        if from_mode == QueueMode.FIFO:
            queue_info = await self._fifo_service.get_all(channel_id, limit=1000)
        else:
            queue_info = await self._priority_service.get_all(channel_id, limit=1000)
        
        migrated_count = 0
        
        # Добавить элементы в целевую очередь
        # ВАЖНО: При миграции в priority режим requested_by ДОЛЖЕН быть заполнен
        # для корректного расчета приоритета
        for item in queue_info.items:
            try:
                item_create = QueueItemCreate(
                    title=item.title,
                    url=item.url,
                    duration=item.duration,
                    source=item.source,
                    metadata=item.metadata,
                )
                
                if to_mode == QueueMode.FIFO:
                    await self._fifo_service.add(
                        channel_id=channel_id,
                        item_create=item_create,
                        requested_by=item.requested_by,
                    )
                else:
                    # Для priority режима нужен User объект
                    # TODO: Получать User из БД по requested_by
                    logger.warning(
                        f"Migration to PRIORITY mode requires User objects. "
                        f"Item {item.id} will be added with default priority."
                    )
                    # Временно создаем заглушку
                    # В production нужно получать реальный User из БД
                    user = None  # TODO: fetch User from DB by requested_by
                    
                    await self._priority_service.add(
                        channel_id=channel_id,
                        item_create=item_create,
                        user=user,  # Если None, будет NORMAL priority
                    )
                
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate item {item.id}: {e}")
        
        # Очистить исходную очередь
        if from_mode == QueueMode.FIFO:
            await self._fifo_service.clear(channel_id)
        else:
            await self._priority_service.clear(channel_id)
        
        logger.info(
            f"Migrated {migrated_count}/{len(queue_info.items)} items "
            f"from {from_mode} to {to_mode} for channel {channel_id}"
        )
        
        return migrated_count
    
    # ==========================================================================
    # Unified API - делегирует к нужному сервису
    # ==========================================================================
    
    async def add(
        self,
        channel_id: int,
        item_create: QueueItemCreate,
        requested_by: Optional[int] = None,
        user: Optional[User] = None,
    ) -> QueueItem:
        """
        Добавить элемент в очередь (в конец для FIFO, с приоритетом для PRIORITY).
        
        Args:
            channel_id: ID канала
            item_create: Данные элемента
            requested_by: Telegram ID пользователя (для FIFO)
            user: User объект (для PRIORITY - обязателен для корректного приоритета)
        """
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.add(
                channel_id=channel_id,
                item_create=item_create,
                requested_by=requested_by,
            )
        else:
            return await self._priority_service.add(
                channel_id=channel_id,
                item_create=item_create,
                user=user,
            )
    
    async def add_priority(
        self,
        channel_id: int,
        item_create: QueueItemCreate,
        requested_by: Optional[int] = None,
    ) -> QueueItem:
        """
        Добавить элемент в начало очереди (только для FIFO).
        
        В PRIORITY режиме этот метод делегирует к обычному add(),
        так как приоритет определяется ролью пользователя автоматически.
        """
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.add_priority(
                channel_id=channel_id,
                item_create=item_create,
                requested_by=requested_by,
            )
        else:
            # В priority режиме add_priority не имеет смысла
            # так как позиция определяется ролью пользователя
            logger.warning(
                f"add_priority called in PRIORITY mode for channel {channel_id}. "
                "Delegating to regular add(). Position will be determined by user role."
            )
            return await self._priority_service.add(
                channel_id=channel_id,
                item_create=item_create,
                user=None,  # TODO: get User from requested_by
            )
    
    async def get_all(
        self,
        channel_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> QueueInfo:
        """Получить все элементы очереди."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.get_all(
                channel_id=channel_id,
                limit=limit,
                offset=offset,
            )
        else:
            return await self._priority_service.get_all(
                channel_id=channel_id,
                limit=limit,
                offset=offset,
            )
    
    async def get_next(self, channel_id: int) -> Optional[QueueItem]:
        """Получить следующий элемент без удаления."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.get_next(channel_id)
        else:
            return await self._priority_service.get_next(channel_id)
    
    async def pop_next(self, channel_id: int) -> Optional[QueueItem]:
        """Получить и удалить следующий элемент."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.pop_next(channel_id)
        else:
            return await self._priority_service.pop_next(channel_id)
    
    async def remove(self, channel_id: int, item_id: str) -> None:
        """Удалить элемент по ID."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            await self._fifo_service.remove(channel_id, item_id)
        else:
            await self._priority_service.remove(channel_id, item_id)
    
    async def move(
        self,
        channel_id: int,
        item_id: str,
        new_position: int,
    ) -> List[QueueItem]:
        """
        Переместить элемент на новую позицию.
        
        ВАЖНО: В PRIORITY режиме этот метод НЕ поддерживается,
        так как позиция определяется приоритетом (ролью пользователя).
        """
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.move(
                channel_id=channel_id,
                item_id=item_id,
                new_position=new_position,
            )
        else:
            raise InvalidPositionError(
                "Move operation is not supported in PRIORITY queue mode. "
                "Item position is determined by user role."
            )
    
    async def skip(self, channel_id: int) -> Optional[QueueItem]:
        """Пропустить текущий трек (удалить первый элемент и вернуть следующий)."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.skip(channel_id)
        else:
            # В priority режиме skip работает аналогично
            # pop_next удаляет первый (с наименьшим score), get_next возвращает следующий
            await self._priority_service.pop_next(channel_id)
            return await self._priority_service.get_next(channel_id)
    
    async def clear(self, channel_id: int) -> int:
        """Очистить очередь."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.clear(channel_id)
        else:
            return await self._priority_service.clear(channel_id)
    
    async def get_size(self, channel_id: int) -> int:
        """Получить размер очереди."""
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.FIFO:
            return await self._fifo_service.get_size(channel_id)
        else:
            # У PriorityQueueService нет get_size, используем get_all
            queue_info = await self._priority_service.get_all(channel_id, limit=1)
            return queue_info.total_items
    
    # ==========================================================================
    # Priority Queue Specific Methods
    # ==========================================================================
    
    async def get_vip_count(self, channel_id: int) -> int:
        """
        Получить количество VIP треков в очереди.
        
        Доступно только в PRIORITY режиме.
        """
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.PRIORITY:
            return await self._priority_service.get_vip_count(channel_id)
        else:
            logger.warning(
                f"get_vip_count called in FIFO mode for channel {channel_id}. "
                "Returning 0."
            )
            return 0
    
    async def get_queue_stats(self, channel_id: int) -> dict:
        """
        Получить статистику очереди (распределение по ролям).
        
        Доступно только в PRIORITY режиме.
        """
        mode = self._get_mode(channel_id)
        
        if mode == QueueMode.PRIORITY:
            return await self._priority_service.get_queue_stats(channel_id)
        else:
            # Для FIFO возвращаем простую статистику
            size = await self._fifo_service.get_size(channel_id)
            return {
                "mode": QueueMode.FIFO.value,
                "total": size,
                "vip": 0,
                "admin": 0,
                "normal": size,
            }


# Singleton
_unified_queue_service: Optional[UnifiedQueueService] = None


def get_unified_queue_service() -> UnifiedQueueService:
    """Получить singleton instance UnifiedQueueService."""
    global _unified_queue_service
    if _unified_queue_service is None:
        _unified_queue_service = UnifiedQueueService()
    return _unified_queue_service
