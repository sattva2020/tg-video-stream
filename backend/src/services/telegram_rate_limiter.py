"""
Telegram Rate Limiter Service

Система обнаружения и обработки лимитов Telegram API.
Отслеживает ошибки, управляет cooldown периодами и предупреждает пользователей.

Типы лимитов Telegram:
1. FloodWait - общий лимит на запросы (содержит время ожидания в секундах)
2. PhoneNumberFlood - слишком много попыток авторизации с номера
3. PhoneCodeExpired - код истёк (120 секунд)
4. SendCodeUnavailable - отправка кода временно недоступна
5. PeerFlood - слишком много действий с пользователями/каналами
6. PhonePasswordFlood - слишком много попыток ввода пароля 2FA

Интеграция с RateLimitQueueService:
- Все API запросы проходят через очередь с приоритетами
- Автоматическое управление скоростью запросов
- Пакетная обработка для эффективности
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
from src.core.config import settings

logger = logging.getLogger(__name__)


class LimitType(Enum):
    """Типы лимитов Telegram"""
    FLOOD_WAIT = "flood_wait"                    # Общий FloodWait
    PHONE_NUMBER_FLOOD = "phone_number_flood"    # Лимит на номер телефона
    PHONE_CODE_EXPIRED = "phone_code_expired"    # Код истёк
    SEND_CODE_UNAVAILABLE = "send_code_unavailable"  # Отправка кода недоступна
    PEER_FLOOD = "peer_flood"                    # Лимит на действия с пользователями
    PASSWORD_FLOOD = "password_flood"            # Лимит на попытки пароля
    PHONE_BANNED = "phone_banned"                # Номер заблокирован
    API_ID_FLOOD = "api_id_flood"                # Лимит на API_ID
    UNKNOWN = "unknown"                          # Неизвестный лимит


@dataclass
class LimitInfo:
    """Информация о лимите"""
    type: LimitType
    wait_seconds: int = 0
    message: str = ""
    retry_after: Optional[datetime] = None
    phone: Optional[str] = None
    raw_error: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Проверка, активен ли ещё лимит"""
        if not self.retry_after:
            return False
        return datetime.now() < self.retry_after
    
    @property
    def remaining_seconds(self) -> int:
        """Оставшееся время ожидания"""
        if not self.retry_after:
            return 0
        remaining = (self.retry_after - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "wait_seconds": self.wait_seconds,
            "remaining_seconds": self.remaining_seconds,
            "message": self.message,
            "retry_after": self.retry_after.isoformat() if self.retry_after else None,
            "is_active": self.is_active,
        }


class TelegramRateLimiter:
    """Сервис управления лимитами Telegram API"""
    
    # Ключи для Redis
    REDIS_PREFIX = "tg_limit"
    
    # Маппинг ошибок Pyrogram на типы лимитов
    ERROR_MAPPING = {
        "FloodWait": LimitType.FLOOD_WAIT,
        "Flood": LimitType.FLOOD_WAIT,
        "PhoneNumberFlood": LimitType.PHONE_NUMBER_FLOOD,
        "PhoneCodeExpired": LimitType.PHONE_CODE_EXPIRED,
        "SEND_CODE_UNAVAILABLE": LimitType.SEND_CODE_UNAVAILABLE,
        "SendCodeUnavailable": LimitType.SEND_CODE_UNAVAILABLE,
        "PeerFlood": LimitType.PEER_FLOOD,
        "PhonePasswordFlood": LimitType.PASSWORD_FLOOD,
        "PhoneNumberBanned": LimitType.PHONE_BANNED,
        "ApiIdPublishedFlood": LimitType.API_ID_FLOOD,
        "FloodTestPhoneWait": LimitType.FLOOD_WAIT,
    }
    
    # Рекомендуемые cooldown периоды (если не указано в ошибке)
    DEFAULT_COOLDOWNS = {
        LimitType.FLOOD_WAIT: 60,
        LimitType.PHONE_NUMBER_FLOOD: 3600,       # 1 час
        LimitType.PHONE_CODE_EXPIRED: 0,          # Можно сразу запросить новый
        LimitType.SEND_CODE_UNAVAILABLE: 1800,    # 30 минут
        LimitType.PEER_FLOOD: 86400,              # 24 часа
        LimitType.PASSWORD_FLOOD: 600,            # 10 минут
        LimitType.PHONE_BANNED: 0,                # Бессрочно
        LimitType.API_ID_FLOOD: 86400,            # 24 часа
        LimitType.UNKNOWN: 60,
    }
    
    # Человекочитаемые сообщения
    USER_MESSAGES = {
        LimitType.FLOOD_WAIT: "⏳ Слишком много запросов. Подождите {time}.",
        LimitType.PHONE_NUMBER_FLOOD: "📵 Слишком много попыток авторизации с этого номера. Попробуйте через {time}.",
        LimitType.PHONE_CODE_EXPIRED: "⌛ Код подтверждения истёк. Запросите новый код.",
        LimitType.SEND_CODE_UNAVAILABLE: "🚫 Отправка кода временно недоступна для этого номера. Попробуйте через {time}.",
        LimitType.PEER_FLOOD: "🔒 Временные ограничения на действия с пользователями. Подождите {time}.",
        LimitType.PASSWORD_FLOOD: "🔐 Слишком много попыток ввода пароля. Подождите {time}.",
        LimitType.PHONE_BANNED: "⛔ Этот номер телефона заблокирован в Telegram.",
        LimitType.API_ID_FLOOD: "🛑 Превышен лимит API. Обратитесь к администратору.",
        LimitType.UNKNOWN: "⚠️ Telegram временно ограничил запросы. Подождите {time}.",
    }
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        
    async def _get_redis(self) -> redis.Redis:
        return await redis.from_url(self.redis_url, decode_responses=True)
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """Форматирование времени для пользователя"""
        if seconds < 60:
            return f"{seconds} сек."
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} мин."
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} ч."
        else:
            days = seconds // 86400
            return f"{days} дн."
    
    def parse_error(self, error: Exception) -> LimitInfo:
        """
        Парсинг ошибки Pyrogram и извлечение информации о лимите.
        
        Args:
            error: Исключение от Pyrogram
            
        Returns:
            LimitInfo с информацией о лимите
        """
        error_name = type(error).__name__
        error_str = str(error)
        
        logger.warning(f"[RateLimiter] Parsing error: {error_name}: {error_str}")
        
        # Определяем тип лимита
        limit_type = LimitType.UNKNOWN
        for error_key, ltype in self.ERROR_MAPPING.items():
            if error_key.lower() in error_name.lower() or error_key.lower() in error_str.lower():
                limit_type = ltype
                break
        
        # Извлекаем время ожидания из ошибки
        wait_seconds = self.DEFAULT_COOLDOWNS.get(limit_type, 60)
        
        # FloodWait содержит время в атрибуте value
        if hasattr(error, 'value') and isinstance(error.value, int):
            wait_seconds = error.value
        elif hasattr(error, 'x') and isinstance(error.x, int):
            wait_seconds = error.x
        
        # Пробуем извлечь время из строки ошибки
        import re
        time_match = re.search(r'(\d+)\s*(?:seconds?|sec|s)', error_str, re.IGNORECASE)
        if time_match:
            wait_seconds = int(time_match.group(1))
        
        # Формируем сообщение для пользователя
        message_template = self.USER_MESSAGES.get(limit_type, self.USER_MESSAGES[LimitType.UNKNOWN])
        message = message_template.format(time=self._format_time(wait_seconds))
        
        # Вычисляем время, когда можно повторить
        retry_after = datetime.now() + timedelta(seconds=wait_seconds) if wait_seconds > 0 else None
        
        return LimitInfo(
            type=limit_type,
            wait_seconds=wait_seconds,
            message=message,
            retry_after=retry_after,
            raw_error=error_str,
        )
    
    async def record_limit(self, phone: str, limit_info: LimitInfo) -> None:
        """
        Записать лимит в Redis для отслеживания.
        
        Args:
            phone: Номер телефона
            limit_info: Информация о лимите
        """
        r = await self._get_redis()
        try:
            key = f"{self.REDIS_PREFIX}:{phone}"
            
            # Сохраняем информацию о лимите
            await r.hset(key, mapping={
                "type": limit_info.type.value,
                "wait_seconds": str(limit_info.wait_seconds),
                "retry_after": limit_info.retry_after.isoformat() if limit_info.retry_after else "",
                "message": limit_info.message,
                "recorded_at": datetime.now().isoformat(),
            })
            
            # Устанавливаем TTL на время лимита + буфер
            if limit_info.wait_seconds > 0:
                await r.expire(key, limit_info.wait_seconds + 60)
            
            # Инкрементируем счётчик ошибок для аналитики
            counter_key = f"{self.REDIS_PREFIX}:stats:{limit_info.type.value}"
            await r.incr(counter_key)
            await r.expire(counter_key, 86400)  # Статистика за 24 часа
            
            logger.info(f"[RateLimiter] Recorded limit for {phone}: {limit_info.type.value}, wait={limit_info.wait_seconds}s")
            
        finally:
            await r.close()
    
    async def check_limit(self, phone: str) -> Optional[LimitInfo]:
        """
        Проверить, есть ли активный лимит для номера телефона.
        
        Args:
            phone: Номер телефона
            
        Returns:
            LimitInfo если лимит активен, иначе None
        """
        r = await self._get_redis()
        try:
            key = f"{self.REDIS_PREFIX}:{phone}"
            data = await r.hgetall(key)
            
            if not data:
                return None
            
            # Проверяем, истёк ли лимит
            retry_after_str = data.get("retry_after", "")
            if retry_after_str:
                retry_after = datetime.fromisoformat(retry_after_str)
                if datetime.now() >= retry_after:
                    # Лимит истёк, удаляем
                    await r.delete(key)
                    return None
                
                # Лимит ещё активен
                return LimitInfo(
                    type=LimitType(data.get("type", "unknown")),
                    wait_seconds=int(data.get("wait_seconds", 0)),
                    message=data.get("message", ""),
                    retry_after=retry_after,
                    phone=phone,
                )
            
            return None
            
        finally:
            await r.close()
    
    async def clear_limit(self, phone: str) -> None:
        """Очистить лимит для номера телефона"""
        r = await self._get_redis()
        try:
            key = f"{self.REDIS_PREFIX}:{phone}"
            await r.delete(key)
            logger.info(f"[RateLimiter] Cleared limit for {phone}")
        finally:
            await r.close()
    
    async def get_stats(self) -> Dict[str, int]:
        """Получить статистику лимитов за последние 24 часа"""
        r = await self._get_redis()
        try:
            stats = {}
            for limit_type in LimitType:
                key = f"{self.REDIS_PREFIX}:stats:{limit_type.value}"
                count = await r.get(key)
                if count:
                    stats[limit_type.value] = int(count)
            return stats
        finally:
            await r.close()
    
    async def get_global_status(self) -> Dict[str, Any]:
        """
        Получить глобальный статус лимитов API.
        
        Returns:
            Словарь с информацией о текущем состоянии лимитов
        """
        r = await self._get_redis()
        try:
            # Проверяем глобальный лимит API_ID
            api_limit_key = f"{self.REDIS_PREFIX}:global:api_id"
            api_limit = await r.get(api_limit_key)
            
            # Получаем статистику
            stats = await self.get_stats()
            
            # Считаем активные лимиты
            active_limits = 0
            pattern = f"{self.REDIS_PREFIX}:+*"
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor, match=pattern, count=100)
                for key in keys:
                    if "stats" not in key and "global" not in key:
                        active_limits += 1
                if cursor == 0:
                    break
            
            return {
                "api_id_limited": bool(api_limit),
                "active_phone_limits": active_limits,
                "stats_24h": stats,
                "status": "limited" if api_limit or active_limits > 10 else "ok",
            }
            
        finally:
            await r.close()
    
    def should_retry(self, limit_info: LimitInfo) -> bool:
        """
        Определить, стоит ли повторять запрос.

        Args:
            limit_info: Информация о лимите

        Returns:
            True если запрос можно/нужно повторить после ожидания
        """
        # Не повторять при бане
        if limit_info.type == LimitType.PHONE_BANNED:
            return False

        # Код истёк - нужно запросить новый
        if limit_info.type == LimitType.PHONE_CODE_EXPIRED:
            return False  # Не повторять, а запросить новый код

        # Остальные - можно повторить после ожидания
        return limit_info.wait_seconds < 3600  # Ждём только если меньше часа


# Глобальный экземпляр
rate_limiter = TelegramRateLimiter()


# Integration with RateLimitQueueService
class TelegramAPIQueue:
    """
    Интеграционный слой для выполнения Telegram API вызовов через очередь.

    Использует RateLimitQueueService для управления запросами с приоритетами
    и автоматической обработкой rate limits.

    Usage:
        queue = TelegramAPIQueue()

        # Прямое выполнение с автоматическим queueing
        result = await queue.execute_api_call(
            client=client,
            method="get_chat",
            params={"chat_id": "@channel"},
            request_type=RequestType.CHANNEL_INFO,
            account_id="account123"
        )

        # Добавление в очередь без немедленного выполнения
        request = await queue.enqueue(
            method="send_message",
            params={"chat_id": "@channel", "text": "Hello"},
            request_type=RequestType.STREAM_CONTROL,
            account_id="account123",
            priority=RequestPriority.HIGH
        )
    """

    def __init__(self):
        """Инициализация TelegramAPIQueue."""
        self._queue_service = None
        self._limiter = rate_limiter

    async def _get_queue_service(self):
        """Lazy load RateLimitQueueService."""
        if self._queue_service is None:
            from src.services.rate_limit_queue_service import get_rate_limit_queue_service
            self._queue_service = get_rate_limit_queue_service()
        return self._queue_service

    async def execute_api_call(
        self,
        client: Any,
        method: str,
        params: Dict[str, Any],
        request_type: Any = None,
        account_id: Optional[str] = None,
        priority: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Выполнить API вызов с автоматическим управлением очередью и rate limits.

        Args:
            client: Pyrogram Client instance
            method: Имя метода API (например, "get_chat", "send_message")
            params: Параметры для API вызова
            request_type: Тип запроса (RequestType enum)
            account_id: ID аккаунта Telegram
            priority: Приоритет запроса (RequestPriority enum)
            metadata: Дополнительные метаданные

        Returns:
            Результат API вызова

        Raises:
            Exception: При ошибке API или превышении лимита повторных попыток
        """
        from src.services.rate_limit_queue_service import (
            RequestType as QueueRequestType,
            RequestPriority as QueueRequestPriority,
            QueuedRequest,
        )

        # Определяем тип запроса и приоритет
        if request_type is None:
            request_type = QueueRequestType.BACKGROUND_SYNC
        if priority is None:
            priority = QueueRequestPriority.LOW

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Проверяем rate limits перед выполнением
                if account_id:
                    limit_info = await self._limiter.check_limit(account_id)
                    if limit_info and limit_info.is_active:
                        # Ждём окончания лимита
                        wait_seconds = limit_info.remaining_seconds
                        if wait_seconds > 0:
                            logger.warning(
                                f"[TelegramQueue] Rate limit active for {account_id}, "
                                f"waiting {wait_seconds}s"
                            )
                            await asyncio.sleep(min(wait_seconds, 60))

                # Выполняем API вызов
                api_method = getattr(client, method, None)
                if not api_method:
                    raise ValueError(f"Method {method} not found on client")

                if asyncio.iscoroutinefunction(api_method):
                    result = await api_method(**params)
                else:
                    result = api_method(**params)

                # Записываем успех (если есть account_id)
                if account_id:
                    # Можно добавить запись об успешном запросе в статистику
                    pass

                return result

            except Exception as e:
                # Проверяем, является ли ошибка rate limit
                limit_info = self._limiter.parse_error(e)

                if limit_info.type in (
                    LimitType.FLOOD_WAIT,
                    LimitType.PEER_FLOOD,
                    LimitType.API_ID_FLOOD,
                ):
                    # Записываем лимит
                    if account_id:
                        await self._limiter.record_limit(account_id, limit_info)

                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(
                            f"[TelegramQueue] Max retries exceeded for {method}: {e}"
                        )
                        raise

                    # Ждём перед повторной попыткой
                    wait_time = min(limit_info.remaining_seconds, 60)
                    logger.warning(
                        f"[TelegramQueue] Rate limit hit, retry {retry_count}/{max_retries}, "
                        f"waiting {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)

                elif limit_info.type == LimitType.PHONE_BANNED:
                    # Не повторять при бане
                    logger.error(f"[TelegramQueue] Account {account_id} is banned")
                    raise

                else:
                    # Другие ошибки не повторяем
                    logger.error(f"[TelegramQueue] API call failed: {e}")
                    raise

        raise Exception(f"Max retries exceeded for {method}")

    async def enqueue(
        self,
        method: str,
        params: Dict[str, Any],
        request_type: Any,
        account_id: Optional[str] = None,
        priority: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Добавить запрос в очередь без немедленного выполнения.

        Args:
            method: Имя метода API
            params: Параметры запроса
            request_type: Тип запроса (RequestType enum)
            account_id: ID аккаунта
            priority: Приоритет (RequestPriority enum)
            metadata: Дополнительные метаданные

        Returns:
            QueuedRequest объект
        """
        from src.services.rate_limit_queue_service import (
            RequestType as QueueRequestType,
            RequestPriority as QueueRequestPriority,
        )

        queue_service = await self._get_queue_service()

        # Добавляем в очередь
        request = await queue_service.add(
            method=method,
            params=params,
            request_type=request_type,
            account_id=account_id,
            priority=priority,
            metadata=metadata or {},
        )

        logger.info(
            f"[TelegramQueue] Enqueued request: {method}, "
            f"type={request_type.value}, priority={priority.value if priority else 'auto'}"
        )

        return request

    async def process_queue(
        self,
        client: Any,
        account_id: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_iterations: Optional[int] = None,
    ) -> int:
        """
        Обработать очередь запросов для указанного аккаунта.

        Args:
            client: Pyrogram Client instance
            account_id: ID аккаунта (None для global очереди)
            batch_size: Размер пакета для обработки
            max_iterations: Максимальное число итераций (None = бесконечно)

        Returns:
            Количество обработанных запросов
        """
        from src.services.rate_limit_queue_service import QueuedRequest

        queue_service = await self._get_queue_service()
        iterations = 0
        total_processed = 0

        while max_iterations is None or iterations < max_iterations:
            # Проверяем, пуста ли очередь
            if await queue_service.is_empty(account_id):
                logger.debug(f"[TelegramQueue] Queue empty for {account_id}")
                break

            # Получаем пакет запросов
            requests = await queue_service.pop_batch(
                batch_size=batch_size,
                account_id=account_id,
            )

            if not requests:
                break

            # Обрабатываем каждый запрос
            for request in requests:
                try:
                    result = await self.execute_api_call(
                        client=client,
                        method=request.method,
                        params=request.params,
                        request_type=request.request_type,
                        account_id=request.account_id,
                    )

                    # Отслеживаем успешное выполнение
                    await queue_service._track_request_processed(
                        account_id=request.account_id,
                        request=request,
                        success=True,
                    )

                    total_processed += 1

                except Exception as e:
                    logger.error(
                        f"[TelegramQueue] Error processing queued request: "
                        f"{request.method}, error={e}"
                    )

                    # Отслеживаем неудачное выполнение
                    await queue_service._track_request_processed(
                        account_id=request.account_id,
                        request=request,
                        success=False,
                    )

                    # Возвращаем в очередь при необходимости
                    if request.retry_count < request.max_retries:
                        await queue_service._requeue_failed_requests([request])

            iterations += 1

            # Небольшая пауза между итерациями
            await asyncio.sleep(0.1)

        logger.info(
            f"[TelegramQueue] Processed {total_processed} requests "
            f"for {account_id} in {iterations} iterations"
        )

        return total_processed


# Глобальный экземпляр интеграционного слоя
telegram_api_queue = TelegramAPIQueue()


"""
Integration Guide: Using RateLimitQueueService with Telegram Handlers
=====================================================================

The TelegramAPIQueue provides two main usage patterns:

PATTERN 1: Direct Execution with Rate Limit Protection
------------------------------------------------------
Use this for user-facing API calls that need immediate response but still
benefit from rate limit protection and automatic retry logic.

Example:
    from src.services.telegram_rate_limiter import telegram_api_queue
    from src.services.rate_limit_queue_service import RequestType

    # Execute API call with automatic rate limit handling
    chat = await telegram_api_queue.execute_api_call(
        client=client,
        method="get_chat",
        params={"chat_id": "@channel"},
        request_type=RequestType.CHANNEL_INFO,
        account_id="account123"
    )

Benefits:
- Automatic retry on FloodWait errors
- Rate limit detection and waiting
- Request tracking per account
- Priority-based execution

PATTERN 2: Queue for Background Processing
-------------------------------------------
Use this for bulk operations, background tasks, or non-urgent API calls.

Example (Enqueue + Manual Processing):
    # Add request to queue
    await telegram_api_queue.enqueue(
        method="send_message",
        params={"chat_id": chat_id, "text": "Hello"},
        request_type=RequestType.BACKGROUND_SYNC,
        account_id="account123",
        priority=RequestPriority.LOW
    )

    # Process queue later (in background task)
    await telegram_api_queue.process_queue(
        client=client,
        account_id="account123",
        batch_size=10
    )

Example (Automatic Processing):
    # Just enqueue, let background worker process
    await telegram_api_queue.enqueue(...)

Request Types and Priorities:
------------------------------
- STREAM_CONTROL (HIGH priority): play/pause/skip commands
- METADATA_FETCH (MEDIUM priority): track metadata, channel info
- CHANNEL_INFO (MEDIUM priority): get_chat, get_full_chat
- USER_INFO (MEDIUM priority): get_users, get_me
- FILE_UPLOAD (LOW priority): upload files
- BACKGROUND_SYNC (LOW priority): periodic sync, cleanup

Integration in Handlers:
------------------------
1. For immediate user responses: Use direct client calls
   await message.reply_text("Response")

2. For API calls with rate limits: Use execute_api_call()
   result = await telegram_api_queue.execute_api_call(...)

3. For background tasks: Use enqueue()
   await telegram_api_queue.enqueue(...)

Rate Limit Handling:
-------------------
The queue service automatically:
- Detects FloodWait and other Telegram rate limits
- Waits appropriate time before retry
- Tracks rate limits per account in Redis
- Respects request priorities (HIGH > MEDIUM > LOW)
- Batches compatible requests for efficiency

Multi-Account Support:
---------------------
When using multiple Telegram accounts:
1. Each account has its own queue: rate_limit_queue:{account_id}
2. Distribute load across accounts using account_id parameter
3. Queue service tracks usage per account
4. Automatic fallback when accounts hit rate limits

Example with MultiAccountRateLimiter:
    from src.services.multi_account_rate_limiter import multi_account_limiter

    # Select best account
    account = await multi_account_limiter.select_account()

    # Execute API call on selected account
    result = await telegram_api_queue.execute_api_call(
        client=account.client,
        method="send_message",
        params={"chat_id": chat_id, "text": "Hello"},
        request_type=RequestType.STREAM_CONTROL,
        account_id=account.account_id,
        priority=RequestPriority.HIGH
    )
"""
