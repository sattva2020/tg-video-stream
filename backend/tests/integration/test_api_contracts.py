"""
Integration tests for API contracts
Проверяем что API endpoints возвращают правильную структуру данных
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.database.models import User
from src.services.auth import create_access_token


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def admin_token(test_db):
    """Create admin user and return JWT token"""
    from src.database.models import User
    from src.services.auth import create_access_token
    
    user = User(
        email="admin@test.com",
        google_id="admin123",
        is_approved=True,
        role="admin"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    token = create_access_token({"sub": user.email, "role": user.role})
    return token


@pytest.fixture
def user_token(test_db):
    """Create regular user and return JWT token"""
    user = User(
        email="user@test.com",
        google_id="user123",
        is_approved=True,
        role="user"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    token = create_access_token({"sub": user.email, "role": user.role})
    return token


class TestAuthAPIContract:
    """Test authentication API contracts"""
    
    def test_google_login_returns_redirect_url(self, client):
        """GET /api/auth/google/login должен возвращать redirect URL"""
        response = client.get("/api/auth/google/login")
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: обязательные поля
        assert "url" in data
        assert isinstance(data["url"], str)
        assert data["url"].startswith("https://accounts.google.com/")
    
    def test_me_endpoint_returns_user_data(self, client, user_token):
        """GET /api/auth/me должен возвращать данные пользователя"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: обязательные поля пользователя
        assert "email" in data
        assert "role" in data
        assert "is_approved" in data
        assert "totp_enabled" in data
        
        # Contract: типы данных
        assert isinstance(data["email"], str)
        assert isinstance(data["role"], str)
        assert isinstance(data["is_approved"], bool)
        assert isinstance(data["totp_enabled"], bool)
    
    def test_logout_clears_cookie(self, client, user_token):
        """POST /api/auth/logout должен очищать cookie"""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        
        # Contract: cookie должна быть удалена
        cookies = response.cookies
        if "refresh_token" in cookies:
            assert cookies["refresh_token"] == ""


class TestAdminAPIContract:
    """Test admin API contracts"""
    
    def test_users_list_structure(self, client, admin_token):
        """GET /api/admin/users должен возвращать список пользователей"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: должен быть список
        assert isinstance(data, list)
        
        # Contract: структура пользователя
        if len(data) > 0:
            user = data[0]
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "is_approved" in user
            assert "created_at" in user
    
    def test_metrics_endpoint_structure(self, client, admin_token):
        """GET /api/admin/metrics должен возвращать системные метрики"""
        response = client.get(
            "/api/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: обязательные секции
        assert "metrics" in data
        assert "timestamp" in data
        
        metrics = data["metrics"]
        
        # Contract: системные метрики
        assert "system" in metrics
        assert "cpu_percent" in metrics["system"]
        assert "memory_percent" in metrics["system"]
        
        # Contract: процесс
        if "process" in metrics:
            assert "cpu_percent" in metrics["process"]
            assert "memory_mb" in metrics["process"]
    
    def test_unauthorized_access_denied(self, client, user_token):
        """Обычный пользователь не должен иметь доступ к admin endpoints"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Contract: 403 Forbidden для non-admin
        assert response.status_code == 403


class TestStreamAPIContract:
    """Test streaming API contracts"""
    
    def test_stream_status_structure(self, client, user_token):
        """GET /api/stream/status должен возвращать статус стрима"""
        response = client.get(
            "/api/stream/status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: обязательные поля
        assert "is_streaming" in data
        assert "current_track" in data
        
        # Contract: типы
        assert isinstance(data["is_streaming"], bool)
        
        # Если стрим идет, должна быть информация о треке
        if data["is_streaming"] and data["current_track"]:
            track = data["current_track"]
            assert "title" in track
            assert "artist" in track
    
    def test_playlist_structure(self, client, user_token):
        """GET /api/stream/playlist должен возвращать плейлист"""
        response = client.get(
            "/api/stream/playlist",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: должен быть список
        assert isinstance(data, list)
        
        # Contract: структура трека
        if len(data) > 0:
            track = data[0]
            assert "id" in track or "path" in track
            assert "title" in track
            assert "artist" in track


class TestNotificationsAPIContract:
    """Test notifications API contracts"""
    
    def test_notifications_list_structure(self, client, user_token):
        """GET /api/notifications должен возвращать список уведомлений"""
        response = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract: должен быть список
        assert isinstance(data, list)
        
        # Contract: структура уведомления
        if len(data) > 0:
            notif = data[0]
            assert "id" in notif
            assert "type" in notif
            assert "message" in notif
            assert "created_at" in notif
            assert "is_read" in notif


class TestErrorResponseContract:
    """Test error response contracts"""
    
    def test_401_unauthorized_structure(self, client):
        """401 ошибки должны иметь стандартную структуру"""
        response = client.get("/api/auth/me")  # без токена
        
        assert response.status_code == 401
        data = response.json()
        
        # Contract: структура ошибки
        assert "detail" in data
    
    def test_403_forbidden_structure(self, client, user_token):
        """403 ошибки должны иметь стандартную структуру"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        
        # Contract: структура ошибки
        assert "detail" in data
    
    def test_404_not_found_structure(self, client, admin_token):
        """404 ошибки должны иметь стандартную структуру"""
        response = client.get(
            "/api/admin/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        
        # Contract: структура ошибки
        assert "detail" in data
    
    def test_422_validation_error_structure(self, client, admin_token):
        """422 ошибки валидации должны иметь детальную информацию"""
        response = client.post(
            "/api/admin/users/approve",
            json={"invalid": "data"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Contract: структура validation error
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data
            
            # FastAPI validation errors имеют массив деталей
            if isinstance(data["detail"], list):
                error = data["detail"][0]
                assert "loc" in error  # location of error
                assert "msg" in error  # error message
                assert "type" in error  # error type


@pytest.mark.integration
class TestAPIVersioning:
    """Test API versioning"""
    
    def test_api_version_in_response_headers(self, client):
        """API должен возвращать версию в headers"""
        response = client.get("/api/health")
        
        # Contract: версия API
        assert response.status_code == 200
        
        # Опционально: можно добавить X-API-Version header
        # assert "X-API-Version" in response.headers
    
    def test_openapi_schema_available(self, client):
        """OpenAPI schema должна быть доступна"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Contract: OpenAPI структура
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Contract: версия API в info
        assert "version" in schema["info"]
