"""
Тесты для сервиса верификации Telegram Login Widget.

Покрывает:
- T009: Unit тест верификации подписи
- T019: Тест создания нового пользователя
"""
import pytest
import time
import hashlib
import hmac
from unittest.mock import patch, MagicMock

from src.services.telegram_widget_auth_service import TelegramWidgetAuthService
from src.schemas.telegram_auth import TelegramAuthRequest


# Тестовый bot token
TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def generate_valid_telegram_data(
    telegram_id: int = 123456789,
    first_name: str = "John",
    last_name: str = "Doe",
    username: str = "johndoe",
    photo_url: str = "https://t.me/i/userpic/320/abc.jpg",
    auth_date: int = None,
    bot_token: str = TEST_BOT_TOKEN,
) -> dict:
    """
    Генерирует валидные тестовые данные с правильной подписью.
    """
    if auth_date is None:
        auth_date = int(time.time())
    
    # Собираем данные для подписи
    data = {
        "id": telegram_id,
        "first_name": first_name,
        "auth_date": auth_date,
    }
    if last_name:
        data["last_name"] = last_name
    if username:
        data["username"] = username
    if photo_url:
        data["photo_url"] = photo_url
    
    # Формируем data-check-string
    check_data = {}
    check_data['id'] = str(data['id'])
    check_data['first_name'] = data['first_name']
    check_data['auth_date'] = str(data['auth_date'])
    if last_name:
        check_data['last_name'] = last_name
    if username:
        check_data['username'] = username
    if photo_url:
        check_data['photo_url'] = photo_url
    
    data_check_string = '\n'.join(
        f'{k}={v}' for k, v in sorted(check_data.items())
    )
    
    # Вычисляем подпись
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    data["hash"] = hash_value
    return data


class TestTelegramWidgetAuthService:
    """Тесты для TelegramWidgetAuthService."""
    
    @pytest.fixture
    def service(self):
        """Создаёт сервис с тестовым bot token."""
        with patch.object(TelegramWidgetAuthService, '__init__', lambda self: None):
            service = TelegramWidgetAuthService()
            service.bot_token = TEST_BOT_TOKEN
            service.max_age = 300
            service.turnstile_secret = ""
            return service
    
    def test_verify_signature_valid(self, service):
        """Тест: валидная подпись проходит проверку."""
        data = generate_valid_telegram_data()
        request = TelegramAuthRequest(**data)
        
        result = service.verify_signature(request)
        
        assert result is True
    
    def test_verify_signature_invalid_hash(self, service):
        """Тест: невалидная подпись отклоняется."""
        data = generate_valid_telegram_data()
        data["hash"] = "invalid_hash_value"
        request = TelegramAuthRequest(**data)
        
        result = service.verify_signature(request)
        
        assert result is False
    
    def test_verify_signature_tampered_data(self, service):
        """Тест: подделанные данные отклоняются."""
        data = generate_valid_telegram_data()
        # Меняем имя после генерации подписи
        data["first_name"] = "Hacker"
        request = TelegramAuthRequest(**data)
        
        result = service.verify_signature(request)
        
        assert result is False
    
    def test_verify_signature_without_optional_fields(self, service):
        """Тест: подпись работает без опциональных полей."""
        data = generate_valid_telegram_data(
            last_name=None,
            username=None,
            photo_url=None,
        )
        request = TelegramAuthRequest(**data)
        
        result = service.verify_signature(request)
        
        assert result is True
    
    def test_verify_signature_no_bot_token(self, service):
        """Тест: без bot token возвращает False."""
        service.bot_token = ""
        data = generate_valid_telegram_data()
        request = TelegramAuthRequest(**data)
        
        result = service.verify_signature(request)
        
        assert result is False
    
    def test_validate_auth_date_valid(self, service):
        """Тест: свежий auth_date проходит проверку."""
        auth_date = int(time.time()) - 60  # 1 минута назад
        
        result = service.validate_auth_date(auth_date)
        
        assert result is True
    
    def test_validate_auth_date_expired(self, service):
        """Тест: устаревший auth_date отклоняется."""
        auth_date = int(time.time()) - 600  # 10 минут назад (> 5 мин)
        
        result = service.validate_auth_date(auth_date)
        
        assert result is False
    
    def test_validate_auth_date_future(self, service):
        """Тест: auth_date в далёком будущем отклоняется."""
        auth_date = int(time.time()) + 120  # 2 минуты в будущем (> 60 сек допуска)
        
        result = service.validate_auth_date(auth_date)
        
        assert result is False
    
    def test_verify_full_valid(self, service):
        """Тест: полная верификация валидных данных."""
        data = generate_valid_telegram_data()
        request = TelegramAuthRequest(**data)
        
        is_valid, error = service.verify(request)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_expired_auth_date(self, service):
        """Тест: полная верификация с устаревшим auth_date."""
        data = generate_valid_telegram_data(auth_date=int(time.time()) - 600)
        request = TelegramAuthRequest(**data)
        
        is_valid, error = service.verify(request)
        
        assert is_valid is False
        assert "устарели" in error.lower()
    
    def test_verify_invalid_signature(self, service):
        """Тест: полная верификация с невалидной подписью."""
        data = generate_valid_telegram_data()
        data["hash"] = "invalid"
        request = TelegramAuthRequest(**data)
        
        is_valid, error = service.verify(request)
        
        assert is_valid is False
        assert "подпись" in error.lower()


class TestTelegramWidgetAuthServiceTurnstile:
    """Тесты для Turnstile CAPTCHA верификации."""
    
    @pytest.fixture
    def service(self):
        """Создаёт сервис с Turnstile secret."""
        with patch.object(TelegramWidgetAuthService, '__init__', lambda self: None):
            service = TelegramWidgetAuthService()
            service.bot_token = TEST_BOT_TOKEN
            service.max_age = 300
            service.turnstile_secret = "test_secret"
            return service
    
    @pytest.mark.asyncio
    async def test_verify_turnstile_success(self, service):
        """Тест: успешная проверка Turnstile."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await service.verify_turnstile("valid_token")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_turnstile_failure(self, service):
        """Тест: неуспешная проверка Turnstile."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "success": False,
                "error-codes": ["invalid-input-response"]
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await service.verify_turnstile("invalid_token")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_turnstile_no_secret(self, service):
        """Тест: без secret пропускаем проверку."""
        service.turnstile_secret = ""
        
        result = await service.verify_turnstile("any_token")
        
        assert result is True
