"""
Integration тесты для API авторизации через Telegram Widget.

Покрывает:
- T010: Integration тест endpoint /api/auth/telegram-widget
- T020: Тест присвоения роли pending
- T026-T028: Тесты link/unlink
"""
import pytest
import time
import hashlib
import hmac
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from src.main import app
from src.models.user import User, UserStatus, UserRole
from src.database import get_db


# Тестовый bot token
TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def generate_telegram_auth_data(
    telegram_id: int = 123456789,
    first_name: str = "John",
    last_name: str = "Doe",
    username: str = "johndoe",
    photo_url: str = "https://t.me/i/userpic/320/abc.jpg",
    auth_date: int = None,
    bot_token: str = TEST_BOT_TOKEN,
) -> dict:
    """Генерирует валидные тестовые данные с правильной подписью."""
    if auth_date is None:
        auth_date = int(time.time())
    
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
    
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    data["hash"] = hash_value
    return data


@pytest.fixture
def client():
    """Создаёт тестовый клиент."""
    return TestClient(app)


@pytest.fixture
def clean_test_users():
    """Очищает тестовых пользователей до и после теста."""
    from src.database import SessionLocal
    
    # Очистка ДО теста
    db = SessionLocal()
    test_telegram_ids = [999999999, 123456789, 111111111, 888888888]
    db.query(User).filter(User.telegram_id.in_(test_telegram_ids)).delete(synchronize_session=False)
    db.commit()
    db.close()
    
    yield
    
    # Очистка ПОСЛЕ теста
    db = SessionLocal()
    db.query(User).filter(User.telegram_id.in_(test_telegram_ids)).delete(synchronize_session=False)
    db.commit()
    db.close()


@pytest.fixture
def mock_telegram_settings():
    """Мокает настройки Telegram."""
    with patch('src.services.telegram_widget_auth_service.settings') as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = TEST_BOT_TOKEN
        mock_settings.TELEGRAM_AUTH_MAX_AGE = 300
        mock_settings.TURNSTILE_SECRET_KEY = ""
        yield mock_settings


class TestTelegramWidgetAuthEndpoint:
    """Тесты для POST /api/auth/telegram-widget."""
    
    def test_auth_new_user_creates_pending_account(self, client, mock_telegram_settings, clean_test_users):
        """Тест: новый пользователь создаётся со статусом pending."""
        data = generate_telegram_auth_data(telegram_id=999999999)
        
        with patch('src.api.auth.telegram_widget.telegram_widget_auth_service') as mock_service:
            mock_service.verify.return_value = (True, None)
            mock_service.verify_turnstile.return_value = True
            
            response = client.post("/api/auth/telegram-widget", json=data)
        
        # Проверяем успешный ответ
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert json_data["is_new_user"] is True
        assert json_data["user"]["status"] == "pending"
    
    def test_auth_invalid_signature_returns_400(self, client, mock_telegram_settings):
        """Тест: невалидная подпись возвращает 400."""
        data = generate_telegram_auth_data()
        data["hash"] = "invalid_hash"
        
        with patch('src.api.auth.telegram_widget.telegram_widget_auth_service') as mock_service:
            mock_service.verify.return_value = (False, "Невалидная подпись")
            
            response = client.post("/api/auth/telegram-widget", json=data)
        
        assert response.status_code == 400
        assert "подпись" in response.json()["detail"].lower() or "невалидн" in response.json()["detail"].lower()
    
    def test_auth_expired_auth_date_returns_400(self, client, mock_telegram_settings):
        """Тест: устаревший auth_date возвращает 400."""
        data = generate_telegram_auth_data(auth_date=int(time.time()) - 600)
        
        with patch('src.api.auth.telegram_widget.telegram_widget_auth_service') as mock_service:
            mock_service.verify.return_value = (False, "Данные авторизации устарели")
            
            response = client.post("/api/auth/telegram-widget", json=data)
        
        assert response.status_code == 400
        assert "устарел" in response.json()["detail"].lower()
    
    def test_auth_existing_user_updates_profile(self, client, mock_telegram_settings, clean_test_users):
        """Тест: существующий пользователь обновляет профиль."""
        # Используем уникальный telegram_id для этого теста
        data = generate_telegram_auth_data(
            telegram_id=888888888,
            first_name="Updated",
            last_name="Name",
        )
        
        with patch('src.api.auth.telegram_widget.telegram_widget_auth_service') as mock_service:
            mock_service.verify.return_value = (True, None)
            mock_service.verify_turnstile.return_value = True
            
            # Первый запрос создаёт пользователя
            response1 = client.post("/api/auth/telegram-widget", json=data)
            assert response1.status_code == 200, f"First request failed: {response1.json()}"
            
        # Генерируем НОВЫЕ данные с обновлённым именем
        data2 = generate_telegram_auth_data(
            telegram_id=888888888,
            first_name="NewName",
            last_name="Name",
        )
        
        with patch('src.api.auth.telegram_widget.telegram_widget_auth_service') as mock_service:
            mock_service.verify.return_value = (True, None)
            mock_service.verify_turnstile.return_value = True
            
            # Второй запрос обновляет
            response2 = client.post("/api/auth/telegram-widget", json=data2)
        
        assert response2.status_code == 200
        assert response2.json()["is_new_user"] is False


class TestTelegramWidgetLinkEndpoint:
    """Тесты для POST /api/auth/telegram-widget/link."""
    
    def test_link_requires_auth(self, client):
        """Тест: привязка требует авторизации."""
        data = generate_telegram_auth_data()
        
        response = client.post("/api/auth/telegram-widget/link", json=data)
        
        assert response.status_code == 401
    
    def test_link_conflict_when_telegram_already_linked(self, client):
        """Тест: конфликт если Telegram уже привязан к другому."""
        # Этот тест требует мока авторизации и БД
        pass  # TODO: Реализовать с fixtures


class TestTelegramWidgetUnlinkEndpoint:
    """Тесты для DELETE /api/auth/telegram-widget/unlink."""
    
    def test_unlink_requires_auth(self, client):
        """Тест: отвязка требует авторизации."""
        response = client.delete("/api/auth/telegram-widget/unlink")
        
        assert response.status_code == 401
    
    def test_unlink_fails_without_alternative_auth(self, client):
        """Тест: нельзя отвязать единственный способ входа."""
        # Этот тест требует мока авторизации и БД
        pass  # TODO: Реализовать с fixtures
