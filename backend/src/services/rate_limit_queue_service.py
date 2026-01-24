"""
Rate Limit Queue Service - управление очередью запросов к API с приоритетами

Сервис для управления очередью API запросов с приоритетами:
- HIGH priority (0-999): Потоковое управление (play/pause/skip)
- MEDIUM priority (1000-1999): Получение метаданных
- LOW priority (2000+): Фоновые задачи

Storage: Redis Sorted Set (ZADD/ZRANGE/ZREM/ZSCORE)
Key pattern: rate_limit_queue:{account_id}

Приоритет вычисляется как:
  score = priority_base + (timestamp / 1e10)

Это обеспечивает:
1. Высокоприоритетные запросы выполняются первыми
2. FIFO порядок внутри одного уровня приоритета
3. Автоматическое пакетирование запросов для эффективности
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

import redis.asyncio as redis

from src.config import settings

logger = logging.getLogger(__name__)


class PriorityLevel:
    """Константы приоритетов для API запросов."""
    HIGH = 0        # 0-999: Потоковое управление (play/pause/skip)
    MEDIUM = 1000   # 1000-1999: Получение метаданных
    LOW = 2000      # 2000+: Фоновые задачи


class RequestPriority(Enum):
    """Уровни приоритетов для API запросов."""
    HIGH = 0        # 0-999: Потоковое управление (play/pause/skip)
    MEDIUM = 1000   # 1000-1999: Получение метаданных
    LOW = 2000      # 2000+: Фоновые задачи


class RequestType(Enum):
    """Типы API запросов."""
    STREAM_CONTROL = "stream_control"       # Play/pause/skip
    METADATA_FETCH = "metadata_fetch"       # Получение метаданных трека
    CHANNEL_INFO = "channel_info"           # Информация о канале
    USER_INFO = "user_info"                 # Информация о пользователе
    FILE_UPLOAD = "file_upload"             # Загрузка файлов
    BACKGROUND_SYNC = "background_sync"     # Фоновая синхронизация
    BATCH_PROCESSING = "batch_processing"   # Пакетная обработка


@dataclass
class QueuedRequest:
    """Очередный запрос к API."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_type: RequestType = RequestType.BACKGROUND_SYNC
    priority: RequestPriority = RequestPriority.LOW
    account_id: Optional[str] = None
    method: str = ""  # Имя метода API
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3

    def to_redis_json(self) -> str:
        """Сериализация для хранения в Redis."""
        return json.dumps({
            "id": self.id,
            "request_type": self.request_type.value,
            "priority": self.priority.value,
            "account_id": self.account_id,
            "method": self.method,
            "params": self.params,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        })

    @classmethod
    def from_redis_json(cls, json_str: str) -> "QueuedRequest":
        """Десериализация из Redis."""
        data = json.loads(json_str)
        return cls(
            id=data["id"],
            request_type=RequestType(data["request_type"]),
            priority=RequestPriority(data["priority"]),
            account_id=data.get("account_id"),
            method=data.get("method", ""),
            params=data.get("params", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


@dataclass
class QueueStats:
    """Статистика очереди."""
    total_requests: int = 0
    high_priority: int = 0
    medium_priority: int = 0
    low_priority: int = 0
    oldest_request_age: float = 0  # В секундах


class RateLimitQueueService:
    """
    Сервис управления очередью запросов к API с приоритетами.

    Использует Redis Sorted Set:
    - rate_limit_queue:{account_id} → ZSET {request_json: score}
    - score = priority_base + (timestamp / 1e10) для FIFO внутри приоритета

    Attributes:
        redis_url: URL подключения к Redis
        max_queue_size: Максимальный размер очереди
        batch_size: Размер пакета для групповой обработки
        batch_timeout: Таймаут ожидания накопления пакета (сек)
    """

    REDIS_KEY_PREFIX = "rate_limit_queue"
    DEFAULT_MAX_QUEUE_SIZE = 1000
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_BATCH_TIMEOUT = 0.1  # 100ms

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_timeout: float = DEFAULT_BATCH_TIMEOUT,
    ):
        """
        Инициализация RateLimitQueueService.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            max_queue_size: Максимальный размер очереди
            batch_size: Размер пакета для групповой обработки
            batch_timeout: Таймаут ожидания накопления пакета
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
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
    def _get_queue_key(account_id: Optional[str]) -> str:
        """Генерация Redis ключа для очереди запросов."""
        if account_id:
            return f"{RateLimitQueueService.REDIS_KEY_PREFIX}:{account_id}"
        return f"{RateLimitQueueService.REDIS_KEY_PREFIX}:global"

    @staticmethod
    def _generate_score(priority: RequestPriority) -> float:
        """
        Генерация итогового score для sorted set.

        Score = priority_base + (timestamp / 1e10)

        Timestamp деление на 1e10 обеспечивает:
        - FIFO внутри одного уровня приоритета
        - Не влияет на разницу между уровнями (>1000)

        Args:
            priority: Приоритет запроса

        Returns:
            Score для ZADD
        """
        timestamp_component = time.time() / 1e10
        return priority.value + timestamp_component

    @staticmethod
    def _get_priority_for_request_type(request_type: RequestType) -> RequestPriority:
        """
        Определить приоритет по типу запроса.

        Args:
            request_type: Тип запроса

        Returns:
            Соответствующий приоритет
        """
        if request_type == RequestType.STREAM_CONTROL:
            return RequestPriority.HIGH
        elif request_type in (RequestType.METADATA_FETCH, RequestType.CHANNEL_INFO, RequestType.USER_INFO):
            return RequestPriority.MEDIUM
        else:
            return RequestPriority.LOW

    async def add(
        self,
        method: str,
        params: Dict[str, Any],
        request_type: RequestType = RequestType.BACKGROUND_SYNC,
        account_id: Optional[str] = None,
        priority: Optional[RequestPriority] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QueuedRequest:
        """
        Добавить запрос в очередь.

        Args:
            method: Имя метода API
            params: Параметры запроса
            request_type: Тип запроса
            account_id: ID аккаунта для выполнения запроса
            priority: Приоритет (автоопределение если None)
            metadata: Дополнительные метаданные

        Returns:
            Созданный QueuedRequest

        Raises:
            Exception: Если очередь достигла максимального размера
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # Проверка лимита очереди
        current_size = await r.zcard(key)
        if current_size >= self.max_queue_size:
            raise Exception(
                f"Очередь для аккаунта {account_id} достигла максимального размера "
                f"({self.max_queue_size} запросов)"
            )

        # Определение приоритета
        if priority is None:
            priority = self._get_priority_for_request_type(request_type)

        # Создание запроса
        request = QueuedRequest(
            request_type=request_type,
            priority=priority,
            account_id=account_id,
            method=method,
            params=params,
            metadata=metadata or {},
        )

        # Вычисление score
        score = self._generate_score(priority)

        # Добавление в sorted set
        await r.zadd(key, {request.to_redis_json(): score})

        logger.debug(
            f"Добавлен запрос в очередь: method={method}, "
            f"type={request_type.value}, priority={priority.value}, score={score:.10f}"
        )

        return request

    async def get_next(
        self,
        account_id: Optional[str] = None,
    ) -> Optional[QueuedRequest]:
        """
        Получить следующий запрос (с наивысшим приоритетом) без удаления.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            QueuedRequest с наивысшим приоритетом или None
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # ZRANGE 0 0 - элемент с минимальным score (наивысший приоритет)
        result = await r.zrange(key, 0, 0, withscores=True)

        if not result:
            return None

        item_json, score = result[0]

        try:
            request = QueuedRequest.from_redis_json(item_json)
            request.metadata["priority_score"] = score
            return request
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга следующего запроса: {e}")
            return None

    async def pop_next(
        self,
        account_id: Optional[str] = None,
    ) -> Optional[QueuedRequest]:
        """
        Извлечь следующий запрос (с наивысшим приоритетом) и удалить его.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            QueuedRequest или None если очередь пуста
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # ZPOPMIN - атомарное извлечение элемента с минимальным score
        result = await r.zpopmin(key, count=1)

        if not result:
            return None

        item_json, score = result[0]

        try:
            request = QueuedRequest.from_redis_json(item_json)
            request.metadata["priority_score"] = score
            logger.debug(
                f"Извлечен запрос: method={request.method}, score={score:.10f}"
            )
            return request
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга запроса: {e}")
            return None

    async def pop_batch(
        self,
        batch_size: Optional[int] = None,
        account_id: Optional[str] = None,
    ) -> List[QueuedRequest]:
        """
        Извлечь пакет запросов с наивысшими приоритетами.

        Args:
            batch_size: Размер пакета (по умолчанию из настроек)
            account_id: ID аккаунта (global очередь если None)

        Returns:
            Список QueuedRequest
        """
        size = batch_size or self.batch_size
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # ZPOPMIN - атомарное извлечение нескольких элементов
        results = await r.zpopmin(key, count=size)

        requests = []
        for item_json, score in results:
            try:
                request = QueuedRequest.from_redis_json(item_json)
                request.metadata["priority_score"] = score
                requests.append(request)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга запроса в пакете: {e}")
                continue

        if requests:
            logger.debug(f"Извлечен пакет из {len(requests)} запросов")

        return requests

    async def get_all(
        self,
        account_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[QueuedRequest]:
        """
        Получить все запросы из очереди с учетом приоритетов.

        Args:
            account_id: ID аккаунта (global очередь если None)
            limit: Максимальное количество элементов
            offset: Смещение

        Returns:
            Список QueuedRequest отсортированных по приоритету
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # Получение с пагинацией (ZRANGE с WITHSCORES)
        start = offset
        end = offset + limit - 1
        items_with_scores = await r.zrange(
            key,
            start,
            end,
            withscores=True
        )

        requests = []
        for item_json, score in items_with_scores:
            try:
                request = QueuedRequest.from_redis_json(item_json)
                request.metadata["priority_score"] = score
                requests.append(request)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга запроса: {e}")
                continue

        return requests

    async def remove(self, request_id: str, account_id: Optional[str] = None) -> bool:
        """
        Удалить запрос по ID.

        Args:
            request_id: UUID запроса
            account_id: ID аккаунта (global очередь если None)

        Returns:
            True если запрос удален
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # Получаем все элементы
        items_with_scores = await r.zrange(key, 0, -1, withscores=True)

        for item_json, score in items_with_scores:
            try:
                request = QueuedRequest.from_redis_json(item_json)
                if request.id == request_id:
                    # Удаляем по значению (member)
                    removed = await r.zrem(key, item_json)
                    if removed > 0:
                        logger.debug(f"Удален запрос: {request_id}")
                        return True
            except (json.JSONDecodeError, ValueError):
                continue

        return False

    async def clear(self, account_id: Optional[str] = None) -> int:
        """
        Очистить очередь.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            Количество удаленных элементов
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        size = await r.zcard(key)
        await r.delete(key)

        logger.info(f"Очищена очередь: account={account_id}, items={size}")

        return size

    async def get_size(self, account_id: Optional[str] = None) -> int:
        """
        Получить размер очереди.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            Количество запросов в очереди
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)
        return await r.zcard(key)

    async def is_empty(self, account_id: Optional[str] = None) -> bool:
        """
        Проверить, пуста ли очередь.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            True если очередь пуста
        """
        return await self.get_size(account_id) == 0

    async def get_queue_stats(self, account_id: Optional[str] = None) -> QueueStats:
        """
        Получить статистику очереди.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            QueueStats с распределением по приоритетам
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        total = await r.zcard(key)

        # Подсчет по приоритетам
        high_count = await r.zcount(key, RequestPriority.HIGH.value, RequestPriority.MEDIUM.value - 1)
        medium_count = await r.zcount(key, RequestPriority.MEDIUM.value, RequestPriority.LOW.value - 1)
        low_count = total - high_count - medium_count

        # Возраст самого старого запроса
        oldest_request_age = 0.0
        if total > 0:
            oldest = await r.zrange(key, 0, 0, withscores=True)
            if oldest:
                try:
                    request = QueuedRequest.from_redis_json(oldest[0][0])
                    oldest_request_age = time.time() - request.created_at
                except (json.JSONDecodeError, ValueError):
                    pass

        return QueueStats(
            total_requests=total,
            high_priority=high_count,
            medium_priority=medium_count,
            low_priority=low_count,
            oldest_request_age=oldest_request_age,
        )

    async def get_priority_distribution(self, account_id: Optional[str] = None) -> Dict[str, int]:
        """
        Получить распределение запросов по приоритетам.

        Args:
            account_id: ID аккаунта (global очередь если None)

        Returns:
            Словарь с количеством запросов по приоритетам
        """
        stats = await self.get_queue_stats(account_id)
        return {
            "high": stats.high_priority,
            "medium": stats.medium_priority,
            "low": stats.low_priority,
            "total": stats.total_requests,
        }

    async def update_retry_count(
        self,
        request_id: str,
        retry_count: int,
        account_id: Optional[str] = None,
    ) -> bool:
        """
        Обновить счетчик повторных попыток для запроса.

        Args:
            request_id: UUID запроса
            retry_count: Новое значение счетчика
            account_id: ID аккаунта (global очередь если None)

        Returns:
            True если запрос обновлен
        """
        r = await self._get_redis()
        key = self._get_queue_key(account_id)

        # Получаем все элементы
        items_with_scores = await r.zrange(key, 0, -1, withscores=True)

        for item_json, score in items_with_scores:
            try:
                request = QueuedRequest.from_redis_json(item_json)
                if request.id == request_id:
                    # Обновляем счетчик
                    request.retry_count = retry_count
                    # Удаляем старый элемент
                    await r.zrem(key, item_json)
                    # Добавляем обновленный с тем же score
                    await r.zadd(key, {request.to_redis_json(): score})
                    logger.debug(f"Обновлен retry_count для {request_id}: {retry_count}")
                    return True
            except (json.JSONDecodeError, ValueError):
                continue

        return False


# Singleton instance
_rate_limit_queue_service: Optional[RateLimitQueueService] = None


def get_rate_limit_queue_service() -> RateLimitQueueService:
    """Получить singleton экземпляр RateLimitQueueService."""
    global _rate_limit_queue_service
    if _rate_limit_queue_service is None:
        _rate_limit_queue_service = RateLimitQueueService()
    return _rate_limit_queue_service


async def shutdown_rate_limit_queue_service() -> None:
    """Закрыть RateLimitQueueService при завершении приложения."""
    global _rate_limit_queue_service
    if _rate_limit_queue_service is not None:
        await _rate_limit_queue_service.close()
        _rate_limit_queue_service = None
