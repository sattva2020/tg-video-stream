"""
Упрощенные pytest fixtures без сложных зависимостей.
Использует моки для минимизации импортов.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid


# Mock user для тестирования
class MockUser:
    def __init__(self, user_id=None, email="test@example.com"):
        self.id = user_id or uuid.uuid4()
        self.email = email
        self.role = "user"
        self.status = "approved"


@pytest.fixture
def test_user():
    """Create a mock test user."""
    return MockUser()


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers with mock JWT token."""
    # Простой mock токен (реальный JWT не нужен для тестов с моками)
    token = "mock_jwt_token_for_tests"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_get_current_user(test_user):
    """Mock get_current_user dependency."""
    async def _get_current_user():
        return test_user
    return _get_current_user


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    
    # Mock query responses
    query_mock = MagicMock()
    filter_mock = MagicMock()
    
    filter_mock.first.return_value = None
    query_mock.filter.return_value = filter_mock
    session.query.return_value = query_mock
    
    return session


@pytest.fixture
def mock_playback_settings(test_user):
    """Mock PlaybackSettings model."""
    settings = MagicMock()
    settings.user_id = test_user.id
    settings.speed = 1.0
    settings.pitch_correction = False
    settings.equalizer_preset = "flat"
    settings.equalizer_custom = None
    settings.language = "en"
    settings.theme = "system"
    return settings


@pytest.fixture
def mock_httpx_response_success():
    """Mock successful httpx response."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = {
        "session_id": "test-session-123",
        "message": "Transcoding started",
        "status": "processing"
    }
    mock_response.headers = {"content-type": "application/json"}
    return mock_response


@pytest.fixture
def mock_httpx_client(mock_httpx_response_success):
    """Mock httpx AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_httpx_response_success
    mock_client.get.return_value = mock_httpx_response_success
    return mock_client


@pytest.fixture
def client_with_mocks(mock_get_current_user, mock_db_session, mock_httpx_client):
    """
    FastAPI TestClient с полными моками.
    Избегает импорта настоящего приложения.
    """
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    
    # Создать простое приложение для тестов
    app = FastAPI()
    
    # Mock зависимости
    def override_get_db():
        yield mock_db_session
    
    def override_get_current_user():
        return mock_get_current_user()
    
    # Зарегистрировать audio router с моками
    with patch("src.api.audio.get_db", override_get_db), \
         patch("src.api.audio.get_current_user", override_get_current_user), \
         patch("httpx.AsyncClient", return_value=mock_httpx_client):
        
        from src.api.audio import router as audio_router
        app.include_router(audio_router, prefix="/api/v1")
        
        return TestClient(app)
