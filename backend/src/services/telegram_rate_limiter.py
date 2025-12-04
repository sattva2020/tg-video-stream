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
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
