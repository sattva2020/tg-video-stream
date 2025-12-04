# -*- coding: utf-8 -*-
"""
Базовый класс для сервисов, использующих Redis.
Устраняет дублирование кода инициализации Redis во всех audio сервисах.

Пример использования:
    class MyService(AsyncRedisService):
        async def my_method(self):
            redis = await self._get_redis()
            await redis.set("key", "value")
"""

import os
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

# Попытка импорта Redis
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = Any  # type: ignore


class AsyncRedisService:
    """
    Базовый класс для асинхронных сервисов, использующих Redis.
    
    Предоставляет:
    - Ленивую инициализацию Redis соединения
    - Методы-хелперы для типичных операций
    - Корректное закрытие соединений
    
    Attributes:
        redis_url: URL для подключения к Redis
        key_prefix: Префикс для всех ключей сервиса
    """
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        key_prefix: str = "",
    ):
        """
        Инициализирует сервис.
        
        Args:
            redis_url: URL Redis (по умолчанию из REDIS_URL env)
            key_prefix: Префикс для ключей этого сервиса
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.key_prefix = key_prefix
        self._redis: Optional[Redis] = None
    
    async def _get_redis(self) -> Redis:
        """
        Получает или создаёт Redis соединение.
        
        Returns:
            Экземпляр Redis клиента
            
        Raises:
            RuntimeError: Если Redis SDK не установлен
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis SDK не установлен (pip install redis)")
        
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
            )
            logger.debug(f"Redis соединение установлено: {self.redis_url}")
        
        return self._redis
    
    async def close(self) -> None:
        """Закрывает Redis соединение."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.debug("Redis соединение закрыто")
    
    def _make_key(self, *parts: str) -> str:
        """
        Создаёт полный ключ с учётом префикса сервиса.
        
        Args:
            *parts: Части ключа для объединения
            
        Returns:
            Полный ключ вида "prefix:part1:part2:..."
        """
        all_parts = [self.key_prefix] if self.key_prefix else []
        all_parts.extend(parts)
        return ":".join(all_parts)
    
    # =========================================================================
    # Хелперы для типичных операций
    # =========================================================================
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получает и парсит JSON из Redis.
        
        Args:
            key: Ключ (без префикса)
            
        Returns:
            Распарсенный словарь или None
        """
        import json
        
        redis = await self._get_redis()
        full_key = self._make_key(key)
        data = await redis.get(full_key)
        
        if data is None:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Некорректный JSON в ключе {full_key}")
            return None
    
    async def set_json(
        self, 
        key: str, 
        value: Dict[str, Any],
        ttl: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Сохраняет словарь как JSON в Redis.
        
        Args:
            key: Ключ (без префикса)
            value: Словарь для сохранения
            ttl: Время жизни (секунды или timedelta)
            
        Returns:
            True если успешно
        """
        import json
        
        redis = await self._get_redis()
        full_key = self._make_key(key)
        json_data = json.dumps(value, ensure_ascii=False, default=str)
        
        if ttl is not None:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            await redis.setex(full_key, ttl, json_data)
        else:
            await redis.set(full_key, json_data)
        
        return True
    
    async def delete_key(self, key: str) -> bool:
        """
        Удаляет ключ из Redis.
        
        Args:
            key: Ключ (без префикса)
            
        Returns:
            True если ключ существовал и был удалён
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        result = await redis.delete(full_key)
        return result > 0
    
    async def exists_key(self, key: str) -> bool:
        """
        Проверяет существование ключа.
        
        Args:
            key: Ключ (без префикса)
            
        Returns:
            True если ключ существует
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        return await redis.exists(full_key) > 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Инкрементирует значение ключа.
        
        Args:
            key: Ключ (без префикса)
            amount: Величина инкремента
            
        Returns:
            Новое значение
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        return await redis.incrby(full_key, amount)
    
    async def set_with_expiry(
        self, 
        key: str, 
        value: str, 
        ttl_seconds: int,
    ) -> bool:
        """
        Устанавливает значение с TTL.
        
        Args:
            key: Ключ (без префикса)
            value: Значение
            ttl_seconds: Время жизни в секундах
            
        Returns:
            True если успешно
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        await redis.setex(full_key, ttl_seconds, value)
        return True
    
    # =========================================================================
    # Rate Limiting хелперы
    # =========================================================================
    
    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Проверяет rate limit для идентификатора.
        
        Args:
            identifier: Уникальный идентификатор (user_id, ip, etc.)
            max_requests: Максимум запросов в окне
            window_seconds: Размер окна в секундах
            
        Returns:
            Tuple (разрешено: bool, оставшиеся запросы: int)
        """
        redis = await self._get_redis()
        key = self._make_key("ratelimit", identifier)
        
        current = await redis.get(key)
        
        if current is None:
            await redis.setex(key, window_seconds, "1")
            return True, max_requests - 1
        
        count = int(current)
        
        if count >= max_requests:
            return False, 0
        
        await redis.incr(key)
        return True, max_requests - count - 1
    
    # =========================================================================
    # List операции
    # =========================================================================
    
    async def list_push(self, key: str, *values: str) -> int:
        """
        Добавляет значения в конец списка.
        
        Args:
            key: Ключ списка
            *values: Значения для добавления
            
        Returns:
            Новая длина списка
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        return await redis.rpush(full_key, *values)
    
    async def list_range(
        self, 
        key: str, 
        start: int = 0, 
        end: int = -1,
    ) -> List[str]:
        """
        Получает диапазон элементов списка.
        
        Args:
            key: Ключ списка
            start: Начальный индекс
            end: Конечный индекс (-1 = до конца)
            
        Returns:
            Список элементов
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        return await redis.lrange(full_key, start, end)
    
    async def list_length(self, key: str) -> int:
        """
        Получает длину списка.
        
        Args:
            key: Ключ списка
            
        Returns:
            Длина списка
        """
        redis = await self._get_redis()
        full_key = self._make_key(key)
        return await redis.llen(full_key)


class SyncRedisService:
    """
    Синхронная версия Redis сервиса для использования в не-async контексте.
    """
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        key_prefix: str = "",
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.key_prefix = key_prefix
        self._redis = None
    
    def _get_redis(self):
        """Получает синхронный Redis клиент."""
        if self._redis is None:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def close(self) -> None:
        """Закрывает соединение."""
        if self._redis:
            self._redis.close()
            self._redis = None
    
    def _make_key(self, *parts: str) -> str:
        """Создаёт ключ с префиксом."""
        all_parts = [self.key_prefix] if self.key_prefix else []
        all_parts.extend(parts)
        return ":".join(all_parts)


def is_redis_available() -> bool:
    """Проверяет доступность Redis SDK."""
    return REDIS_AVAILABLE
