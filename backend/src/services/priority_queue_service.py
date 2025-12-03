"""
Priority Queue Service - управление очередью с приоритетами

Расширяет QueueService для поддержки приоритетов VIP/Admin пользователей:
- VIP priority: 0-999 (высший приоритет)
- Admin priority: 1000-1999  
- Normal priority: 2000+ (FIFO по timestamp)

Storage: Redis Sorted Set (ZADD/ZRANGE/ZREM/ZSCORE)
Key pattern: priority_queue:{channel_id}

Приоритет вычисляется как:
  score = role_priority_base + (timestamp / 1e10)
  
Это обеспечивает:
1. VIP треки всегда впереди обычных
2. FIFO порядок внутри одного уровня приоритета
"""

import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import json

import redis.asyncio as redis

from src.config import settings
from src.models.queue import (
    QueueItem,
    QueueItemCreate,
    QueueInfo,
)
from src.models.user import User, UserRole

logger = logging.getLogger(__name__)


class PriorityLevel:
    """Константы приоритетов для разных ролей."""
    VIP = 0          # 0-999: VIP пользователи
    ADMIN = 1000     # 1000-1999: Администраторы
    NORMAL = 2000    # 2000+: Обычные пользователи


class PriorityQueueService:
    """
    Сервис управления очередью с приоритетами.
    
    Использует Redis Sorted Set:
    - priority_queue:{channel_id} → ZSET {item_json: score}
    - score = role_priority + (timestamp / 1e10) для FIFO внутри роли
    
    Attributes:
        redis_url: URL подключения к Redis
        max_queue_size: Максимальный размер очереди
    """
    
    REDIS_KEY_PREFIX = "priority_queue"
    DEFAULT_MAX_QUEUE_SIZE = 100
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
    ):
        """
        Инициализация PriorityQueueService.
        
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
        """Генерация Redis ключа для приоритетной очереди."""
        return f"{PriorityQueueService.REDIS_KEY_PREFIX}:{channel_id}"
    
    @staticmethod
    def _calculate_priority_score(user_role: str) -> float:
        """
        Вычислить базовый приоритет по роли пользователя.
        
        Args:
            user_role: Роль пользователя (vip, admin, user)
            
        Returns:
            Базовый приоритет (меньше = выше приоритет)
        """
        role_lower = user_role.lower()
        
        if role_lower in ("vip", "superadmin"):
            return PriorityLevel.VIP
        elif role_lower == "admin":
            return PriorityLevel.ADMIN
        else:
            return PriorityLevel.NORMAL
    
    @staticmethod
    def _generate_score(user_role: str) -> float:
        """
        Генерация итогового score для sorted set.
        
        Score = base_priority + (timestamp / 1e10)
        
        Timestamp деление на 1e10 обеспечивает:
        - FIFO внутри одного уровня приоритета
        - Не влияет на разницу между уровнями (>1000)
        
        Args:
            user_role: Роль пользователя
            
        Returns:
            Score для ZADD
        """
        base_priority = PriorityQueueService._calculate_priority_score(user_role)
        timestamp_component = time.time() / 1e10
        return base_priority + timestamp_component
    
    async def add(
        self,
        channel_id: int,
        item_create: QueueItemCreate,
        user: User
    ) -> QueueItem:
        """
        Добавить элемент в приоритетную очередь.
        
        Приоритет определяется ролью пользователя автоматически.
        
        Args:
            channel_id: ID Telegram канала
            item_create: Данные для создания элемента
            user: Пользователь, запросивший добавление
            
        Returns:
            Созданный QueueItem с метаданными приоритета
            
        Raises:
            Exception: Если очередь достигла максимального размера
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Проверка лимита очереди
        current_size = await r.zcard(key)
        if current_size >= self.max_queue_size:
            raise Exception(
                f"Очередь канала {channel_id} достигла максимального размера "
                f"({self.max_queue_size} элементов)"
            )
        
        # Создание QueueItem с метаданными приоритета
        item = QueueItem(
            channel_id=channel_id,
            title=item_create.title,
            url=item_create.url,
            duration=item_create.duration,
            source=item_create.source,
            requested_by=user.id if hasattr(user, 'id') else None,
            metadata={
                **(item_create.metadata or {}),
                "priority_role": user.role,
                "is_vip": user.role.lower() in ("vip", "superadmin"),
                "is_admin": user.role.lower() in ("admin", "superadmin"),
            }
        )
        
        # Вычисление score
        score = self._generate_score(user.role)
        
        # Добавление в sorted set
        await r.zadd(key, {item.to_redis_json(): score})
        
        logger.info(
            f"Добавлен элемент в приоритетную очередь: channel={channel_id}, "
            f"item_id={item.id}, title={item.title}, role={user.role}, score={score:.4f}"
        )
        
        return item
    
    async def get_all(
        self,
        channel_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> QueueInfo:
        """
        Получить очередь с учетом приоритетов.
        
        Элементы возвращаются отсортированными по score (приоритет + FIFO).
        
        Args:
            channel_id: ID Telegram канала
            limit: Максимальное количество элементов
            offset: Смещение
            
        Returns:
            QueueInfo с отсортированными элементами
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Общее количество
        total = await r.zcard(key)
        
        # Получение с пагинацией (ZRANGE с WITHSCORES)
        start = offset
        end = offset + limit - 1
        items_with_scores = await r.zrange(
            key,
            start,
            end,
            withscores=True
        )
        
        items = []
        total_duration = 0
        
        for item_json, score in items_with_scores:
            try:
                item = QueueItem.from_redis_json(item_json)
                # Добавляем score в metadata для отображения
                item.metadata["priority_score"] = score
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
        Получить следующий элемент (с наивысшим приоритетом) без удаления.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            QueueItem с наивысшим приоритетом или None
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # ZRANGE 0 0 - элемент с минимальным score (наивысший приоритет)
        result = await r.zrange(key, 0, 0, withscores=True)
        
        if not result:
            return None
        
        item_json, score = result[0]
        
        try:
            item = QueueItem.from_redis_json(item_json)
            item.metadata["priority_score"] = score
            return item
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга следующего элемента: {e}")
            return None
    
    async def pop_next(self, channel_id: int) -> Optional[QueueItem]:
        """
        Извлечь следующий элемент (с наивысшим приоритетом) и удалить его.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            QueueItem или None если очередь пуста
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # ZPOPMIN - атомарное извлечение элемента с минимальным score
        result = await r.zpopmin(key, count=1)
        
        if not result:
            return None
        
        item_json, score = result[0]
        
        try:
            item = QueueItem.from_redis_json(item_json)
            item.metadata["priority_score"] = score
            logger.debug(
                f"Извлечен элемент: channel={channel_id}, item_id={item.id}, score={score:.4f}"
            )
            return item
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга элемента: {e}")
            return None
    
    async def remove(self, channel_id: int, item_id: str) -> bool:
        """
        Удалить элемент по ID.
        
        Args:
            channel_id: ID Telegram канала
            item_id: UUID элемента
            
        Returns:
            True если элемент удален
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Получаем все элементы
        items_with_scores = await r.zrange(key, 0, -1, withscores=True)
        
        for item_json, score in items_with_scores:
            try:
                item = QueueItem.from_redis_json(item_json)
                if item.id == item_id:
                    # Удаляем по значению (member)
                    removed = await r.zrem(key, item_json)
                    if removed > 0:
                        logger.info(
                            f"Удален элемент из приоритетной очереди: "
                            f"channel={channel_id}, item_id={item_id}"
                        )
                        return True
            except (json.JSONDecodeError, ValueError):
                continue
        
        return False
    
    async def clear(self, channel_id: int) -> int:
        """
        Очистить приоритетную очередь.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            Количество удаленных элементов
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        size = await r.zcard(key)
        await r.delete(key)
        
        logger.info(f"Очищена приоритетная очередь: channel={channel_id}, items={size}")
        
        return size
    
    async def get_size(self, channel_id: int) -> int:
        """Получить размер очереди."""
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        return await r.zcard(key)
    
    async def is_empty(self, channel_id: int) -> bool:
        """Проверить, пуста ли очередь."""
        return await self.get_size(channel_id) == 0
    
    async def get_vip_count(self, channel_id: int) -> int:
        """
        Получить количество VIP треков в очереди.
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            Количество VIP элементов
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        # Подсчитываем элементы с score < 1000 (VIP priority)
        count = await r.zcount(key, PriorityLevel.VIP, PriorityLevel.ADMIN - 1)
        return count
    
    async def get_queue_stats(self, channel_id: int) -> Dict[str, Any]:
        """
        Получить статистику очереди (распределение по приоритетам).
        
        Args:
            channel_id: ID Telegram канала
            
        Returns:
            Словарь со статистикой
        """
        r = await self._get_redis()
        key = self._get_queue_key(channel_id)
        
        total = await r.zcard(key)
        vip_count = await r.zcount(key, PriorityLevel.VIP, PriorityLevel.ADMIN - 1)
        admin_count = await r.zcount(key, PriorityLevel.ADMIN, PriorityLevel.NORMAL - 1)
        normal_count = total - vip_count - admin_count
        
        return {
            "total": total,
            "vip": vip_count,
            "admin": admin_count,
            "normal": normal_count,
        }


# Singleton instance
_priority_queue_service: Optional[PriorityQueueService] = None


def get_priority_queue_service() -> PriorityQueueService:
    """Получить singleton экземпляр PriorityQueueService."""
    global _priority_queue_service
    if _priority_queue_service is None:
        _priority_queue_service = PriorityQueueService()
    return _priority_queue_service


async def shutdown_priority_queue_service() -> None:
    """Закрыть PriorityQueueService при завершении приложения."""
    global _priority_queue_service
    if _priority_queue_service is not None:
        await _priority_queue_service.close()
        _priority_queue_service = None
