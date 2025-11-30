"""
Утилиты структурированного логирования.

Предоставляет типизированные функции для логирования событий безопасности
с консистентной структурой данных.
"""
import logging
from typing import Optional, Dict, Any
from enum import Enum


class TelegramAuthEvent(str, Enum):
    """Типы событий Telegram аутентификации."""
    
    # Успешные события
    LOGIN_SUCCESS = "telegram_login_success"
    REGISTRATION_SUCCESS = "telegram_registration_success"
    LINK_SUCCESS = "telegram_link_success"
    UNLINK_SUCCESS = "telegram_unlink_success"
    SIGNATURE_VALID = "telegram_signature_valid"
    TURNSTILE_PASSED = "telegram_turnstile_passed"
    
    # Неуспешные события
    LOGIN_FAILED = "telegram_login_failed"
    SIGNATURE_INVALID = "telegram_signature_invalid"
    AUTH_DATE_EXPIRED = "telegram_auth_date_expired"
    AUTH_DATE_FUTURE = "telegram_auth_date_future"
    TURNSTILE_FAILED = "telegram_turnstile_failed"
    LINK_CONFLICT = "telegram_link_conflict"
    UNLINK_BLOCKED = "telegram_unlink_blocked"
    
    # Подозрительные события (для security мониторинга)
    SUSPICIOUS_REGISTRATION = "telegram_suspicious_registration"
    RATE_LIMIT_HIT = "telegram_rate_limit_hit"


class SecurityLogger:
    """
    Структурированный логгер для событий безопасности.
    
    Использует JSON-подобный формат для легкой интеграции с системами
    мониторинга (ELK, Loki, CloudWatch).
    """
    
    def __init__(self, name: str = "security"):
        self.logger = logging.getLogger(f"security.{name}")
    
    def _log(
        self,
        level: int,
        event: TelegramAuthEvent,
        message: str,
        telegram_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        username: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Внутренний метод для структурированного логирования.
        
        Args:
            level: Уровень логирования (logging.INFO, logging.WARNING и т.д.)
            event: Тип события
            message: Читаемое сообщение
            telegram_id: ID пользователя в Telegram
            user_id: ID пользователя в системе
            ip_address: IP адрес клиента
            username: Telegram username
            extra: Дополнительные поля
        """
        log_data = {
            "event": event.value,
            "message": message,
        }
        
        if telegram_id is not None:
            log_data["telegram_id"] = telegram_id
        if user_id is not None:
            log_data["user_id"] = user_id
        if ip_address:
            log_data["ip_address"] = ip_address
        if username:
            log_data["telegram_username"] = username
        if extra:
            log_data.update(extra)
        
        # Форматируем как структурированную строку
        structured_msg = " | ".join(f"{k}={v}" for k, v in log_data.items())
        self.logger.log(level, structured_msg)
    
    def info(
        self,
        event: TelegramAuthEvent,
        message: str,
        **kwargs,
    ):
        """Логирование информационного события."""
        self._log(logging.INFO, event, message, **kwargs)
    
    def warning(
        self,
        event: TelegramAuthEvent,
        message: str,
        **kwargs,
    ):
        """Логирование предупреждения."""
        self._log(logging.WARNING, event, message, **kwargs)
    
    def error(
        self,
        event: TelegramAuthEvent,
        message: str,
        **kwargs,
    ):
        """Логирование ошибки."""
        self._log(logging.ERROR, event, message, **kwargs)


# Singleton для Telegram auth логгера
telegram_auth_logger = SecurityLogger("telegram_auth")
