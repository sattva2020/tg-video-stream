"""
Сервис верификации Telegram Login Widget.

Реализует проверку подписи HMAC-SHA256 согласно официальной документации:
https://core.telegram.org/widgets/login#checking-authorization
"""
import hashlib
import hmac
import time
import logging
from typing import Optional
import httpx

from src.core.config import settings
from src.core.logging_utils import telegram_auth_logger, TelegramAuthEvent
from src.schemas.telegram_auth import TelegramAuthRequest


logger = logging.getLogger(__name__)


class TelegramWidgetAuthService:
    """
    Сервис для верификации данных от Telegram Login Widget.
    
    Включает:
    - Проверку HMAC-SHA256 подписи
    - Валидацию auth_date (защита от replay-атак)
    - Опциональную проверку Cloudflare Turnstile CAPTCHA
    """
    
    @property
    def bot_token(self) -> Optional[str]:
        return settings.TELEGRAM_BOT_TOKEN
    
    @property
    def max_age(self) -> int:
        return settings.TELEGRAM_AUTH_MAX_AGE
    
    @property
    def turnstile_secret(self) -> Optional[str]:
        return settings.TURNSTILE_SECRET_KEY
    
    def verify_signature(self, data: TelegramAuthRequest) -> bool:
        """
        Верифицирует подпись данных от Telegram Login Widget.
        
        Алгоритм:
        1. Собрать все поля (кроме hash, turnstile_token) в формате key=value
        2. Отсортировать по ключу
        3. Соединить через '\\n'
        4. Вычислить SHA256 от bot_token
        5. Вычислить HMAC-SHA256 от data-check-string с ключом SHA256(bot_token)
        6. Сравнить с полученным hash
        
        Args:
            data: Данные от Telegram Login Widget
            
        Returns:
            True если подпись валидна, иначе False
        """
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не настроен")
            return False
        
        # Формируем data-check-string (исключаем hash и turnstile_token)
        check_data = {}
        check_data['id'] = str(data.id)
        check_data['first_name'] = data.first_name
        check_data['auth_date'] = str(data.auth_date)
        
        if data.last_name:
            check_data['last_name'] = data.last_name
        if data.username:
            check_data['username'] = data.username
        if data.photo_url:
            check_data['photo_url'] = data.photo_url
        
        # Сортируем по ключу и соединяем
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(check_data.items())
        )
        
        # Вычисляем секретный ключ = SHA256(bot_token)
        secret_key = hashlib.sha256(self.bot_token.encode()).digest()
        
        # Вычисляем HMAC-SHA256
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Безопасное сравнение (защита от timing attack)
        return hmac.compare_digest(calculated_hash, data.hash)
    
    def validate_auth_date(self, auth_date: int) -> bool:
        """
        Проверяет, что auth_date не старше max_age секунд.
        
        Args:
            auth_date: Unix timestamp авторизации от Telegram
            
        Returns:
            True если timestamp валиден, иначе False
        """
        current_time = time.time()
        age = current_time - auth_date
        
        if age > self.max_age:
            telegram_auth_logger.warning(
                TelegramAuthEvent.AUTH_DATE_EXPIRED,
                f"auth_date устарел: возраст {age:.0f}s > max {self.max_age}s",
                extra={"age_seconds": int(age), "max_age": self.max_age}
            )
            return False
        
        # Проверяем, что auth_date не в будущем (с небольшим допуском в 60 секунд)
        if auth_date > current_time + 60:
            telegram_auth_logger.warning(
                TelegramAuthEvent.AUTH_DATE_FUTURE,
                f"auth_date в будущем: {auth_date} > {current_time}",
                extra={"auth_date": auth_date, "current_time": int(current_time)}
            )
            return False
        
        return True
    
    async def verify_turnstile(self, token: str, remote_ip: Optional[str] = None) -> bool:
        """
        Проверяет Cloudflare Turnstile CAPTCHA token.
        
        Args:
            token: Turnstile token от клиента
            remote_ip: IP адрес клиента (опционально)
            
        Returns:
            True если токен валиден, иначе False
        """
        if not self.turnstile_secret:
            logger.warning("TURNSTILE_SECRET_KEY не настроен, пропускаем проверку")
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "secret": self.turnstile_secret,
                    "response": token,
                }
                if remote_ip:
                    payload["remoteip"] = remote_ip
                
                response = await client.post(
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                    data=payload,
                    timeout=10.0
                )
                result = response.json()
                
                if result.get("success"):
                    telegram_auth_logger.info(
                        TelegramAuthEvent.TURNSTILE_PASSED,
                        "Turnstile проверка пройдена",
                    )
                    return True
                else:
                    telegram_auth_logger.warning(
                        TelegramAuthEvent.TURNSTILE_FAILED,
                        "Turnstile проверка не пройдена",
                        extra={"error_codes": result.get('error-codes', [])}
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка проверки Turnstile: {e}")
            # В случае ошибки API пропускаем проверку (fail open)
            # Можно изменить на fail close при необходимости
            return True
    
    def verify(self, data: TelegramAuthRequest) -> tuple[bool, Optional[str]]:
        """
        Полная верификация данных от Telegram Login Widget.
        
        Args:
            data: Данные от Telegram Login Widget
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # 1. Проверяем auth_date
        if not self.validate_auth_date(data.auth_date):
            return False, "Данные авторизации устарели. Попробуйте снова."
        
        # 2. Проверяем подпись
        if not self.verify_signature(data):
            telegram_auth_logger.warning(
                TelegramAuthEvent.SIGNATURE_INVALID,
                "Невалидная подпись данных от Telegram",
                telegram_id=data.id,
                username=data.username,
            )
            return False, "Невалидная подпись. Возможна попытка подделки данных."
        
        telegram_auth_logger.info(
            TelegramAuthEvent.SIGNATURE_VALID,
            "Успешная верификация данных Telegram",
            telegram_id=data.id,
            username=data.username,
        )
        return True, None


# Singleton instance
telegram_widget_auth_service = TelegramWidgetAuthService()
