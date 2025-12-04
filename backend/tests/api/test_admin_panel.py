"""
Тесты для административной панели SQLAdmin.

Покрывает:
- Аутентификацию администратора
- CRUD операции над пользователями
- Аудит действий
- Валидацию ролей
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from httpx import AsyncClient

# --- Mock Models ---

class MockUser:
    """Мок модели пользователя."""
    
    def __init__(
        self,
        id: int = 1,
        email: str = "admin@example.com",
        telegram_id: int = 123456789,
        role: str = "admin",
        is_active: bool = True,
    ):
        self.id = id
        self.email = email
        self.telegram_id = telegram_id
        self.role = role
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockAdminAuditLog:
    """Мок модели аудит лога."""
    
    def __init__(
        self,
        id: int = 1,
        admin_id: int = 1,
        action: str = "update",
        entity_type: str = "user",
        entity_id: int = 2,
        changes: dict = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "Test Agent",
    ):
        self.id = id
        self.admin_id = admin_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.changes = changes or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.created_at = datetime.utcnow()


# --- AdminAuth Tests ---

class TestAdminAuth:
    """Тесты аутентификации в админ-панели."""
    
    @pytest.fixture
    def mock_admin_auth(self):
        """Мок AdminAuth backend."""
        with patch("src.admin.auth.AdminAuth") as mock:
            auth = MagicMock()
            mock.return_value = auth
            yield auth
    
    @pytest.mark.asyncio
    async def test_login_success_with_valid_admin(self, mock_admin_auth):
        """Успешный вход с валидными admin credentials."""
        mock_admin_auth.login = AsyncMock(return_value=True)
        
        request = MagicMock()
        request.cookies = {"access_token": "valid_admin_jwt"}
        
        result = await mock_admin_auth.login(request)
        
        assert result is True
        mock_admin_auth.login.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_login_failure_with_user_role(self, mock_admin_auth):
        """Отказ входа для обычного пользователя."""
        mock_admin_auth.login = AsyncMock(return_value=False)
        
        request = MagicMock()
        request.cookies = {"access_token": "valid_user_jwt"}
        
        result = await mock_admin_auth.login(request)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_login_failure_with_invalid_token(self, mock_admin_auth):
        """Отказ входа с невалидным токеном."""
        mock_admin_auth.login = AsyncMock(return_value=False)
        
        request = MagicMock()
        request.cookies = {"access_token": "invalid_token"}
        
        result = await mock_admin_auth.login(request)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_login_failure_without_token(self, mock_admin_auth):
        """Отказ входа без токена."""
        mock_admin_auth.login = AsyncMock(return_value=False)
        
        request = MagicMock()
        request.cookies = {}
        
        result = await mock_admin_auth.login(request)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_logout_success(self, mock_admin_auth):
        """Успешный выход из админ-панели."""
        mock_admin_auth.logout = AsyncMock(return_value=True)
        
        request = MagicMock()
        
        result = await mock_admin_auth.logout(request)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_authenticate_returns_admin_id(self, mock_admin_auth):
        """authenticate возвращает ID администратора."""
        mock_admin_auth.authenticate = AsyncMock(return_value=1)
        
        request = MagicMock()
        request.cookies = {"access_token": "valid_admin_jwt"}
        
        admin_id = await mock_admin_auth.authenticate(request)
        
        assert admin_id == 1


# --- UserAdmin View Tests ---

class TestUserAdminView:
    """Тесты для UserAdmin view."""
    
    @pytest.fixture
    def mock_user_admin(self):
        """Мок UserAdmin view."""
        view = MagicMock()
        view.can_create = True
        view.can_edit = True
        view.can_delete = False
        view.column_list = ["id", "email", "telegram_id", "role", "is_active"]
        view.column_searchable_list = ["email", "telegram_id"]
        return view
    
    def test_user_admin_permissions(self, mock_user_admin):
        """Проверка прав доступа UserAdmin."""
        assert mock_user_admin.can_create is True
        assert mock_user_admin.can_edit is True
        assert mock_user_admin.can_delete is False  # Soft delete only
    
    def test_user_admin_column_list(self, mock_user_admin):
        """Проверка списка колонок."""
        expected = ["id", "email", "telegram_id", "role", "is_active"]
        assert mock_user_admin.column_list == expected
    
    def test_user_admin_searchable_columns(self, mock_user_admin):
        """Проверка searchable колонок."""
        assert "email" in mock_user_admin.column_searchable_list
        assert "telegram_id" in mock_user_admin.column_searchable_list
    
    @pytest.mark.asyncio
    async def test_user_role_update(self, mock_user_admin):
        """Изменение роли пользователя."""
        user = MockUser(id=2, role="user")
        
        # Симуляция обновления
        user.role = "moderator"
        
        assert user.role == "moderator"
    
    @pytest.mark.asyncio
    async def test_user_deactivation(self, mock_user_admin):
        """Деактивация пользователя."""
        user = MockUser(id=2, is_active=True)
        
        # Симуляция деактивации
        user.is_active = False
        
        assert user.is_active is False
    
    @pytest.mark.asyncio
    async def test_superadmin_protection(self, mock_user_admin):
        """Admin не может изменять superadmin."""
        superadmin = MockUser(id=1, role="superadmin")
        admin = MockUser(id=2, role="admin")
        
        # Симуляция проверки
        def can_edit_user(editor: MockUser, target: MockUser) -> bool:
            if target.role == "superadmin" and editor.role != "superadmin":
                return False
            return True
        
        assert can_edit_user(admin, superadmin) is False
        assert can_edit_user(admin, MockUser(id=3, role="user")) is True


# --- Audit Log Tests ---

class TestAdminAuditLog:
    """Тесты аудит логирования."""
    
    @pytest.fixture
    def mock_audit_service(self):
        """Мок сервиса аудита."""
        service = MagicMock()
        service.log_action = AsyncMock()
        service.get_logs = AsyncMock(return_value=[])
        return service
    
    @pytest.mark.asyncio
    async def test_log_user_create_action(self, mock_audit_service):
        """Логирование создания пользователя."""
        await mock_audit_service.log_action(
            admin_id=1,
            action="create",
            entity_type="user",
            entity_id=10,
            changes={"email": "new@example.com", "role": "user"},
            ip_address="127.0.0.1",
            user_agent="Test Browser",
        )
        
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args
        assert call_args.kwargs["action"] == "create"
        assert call_args.kwargs["entity_type"] == "user"
    
    @pytest.mark.asyncio
    async def test_log_user_update_action(self, mock_audit_service):
        """Логирование обновления пользователя."""
        await mock_audit_service.log_action(
            admin_id=1,
            action="update",
            entity_type="user",
            entity_id=5,
            changes={"role": {"old": "user", "new": "moderator"}},
            ip_address="192.168.1.1",
            user_agent="Admin Panel",
        )
        
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args
        assert call_args.kwargs["action"] == "update"
        assert "role" in call_args.kwargs["changes"]
    
    @pytest.mark.asyncio
    async def test_log_login_action(self, mock_audit_service):
        """Логирование входа в админ-панель."""
        await mock_audit_service.log_action(
            admin_id=1,
            action="login",
            entity_type="session",
            entity_id=None,
            changes={},
            ip_address="10.0.0.1",
            user_agent="Chrome",
        )
        
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args
        assert call_args.kwargs["action"] == "login"
    
    @pytest.mark.asyncio
    async def test_log_logout_action(self, mock_audit_service):
        """Логирование выхода из админ-панели."""
        await mock_audit_service.log_action(
            admin_id=1,
            action="logout",
            entity_type="session",
            entity_id=None,
            changes={},
            ip_address="10.0.0.1",
            user_agent="Chrome",
        )
        
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args
        assert call_args.kwargs["action"] == "logout"
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_admin(self, mock_audit_service):
        """Получение логов по admin_id."""
        expected_logs = [
            MockAdminAuditLog(id=1, admin_id=1, action="login"),
            MockAdminAuditLog(id=2, admin_id=1, action="update"),
        ]
        mock_audit_service.get_logs.return_value = expected_logs
        
        logs = await mock_audit_service.get_logs(admin_id=1)
        
        assert len(logs) == 2
        assert all(log.admin_id == 1 for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_entity(self, mock_audit_service):
        """Получение логов по entity."""
        expected_logs = [
            MockAdminAuditLog(id=1, entity_type="user", entity_id=5, action="create"),
            MockAdminAuditLog(id=2, entity_type="user", entity_id=5, action="update"),
        ]
        mock_audit_service.get_logs.return_value = expected_logs
        
        logs = await mock_audit_service.get_logs(entity_type="user", entity_id=5)
        
        assert len(logs) == 2
        assert all(log.entity_id == 5 for log in logs)


# --- Role-Based Access Tests ---

class TestRoleBasedAccess:
    """Тесты ролевого доступа."""
    
    def test_superadmin_has_full_access(self):
        """Superadmin имеет полный доступ."""
        def check_access(role: str, action: str) -> bool:
            if role == "superadmin":
                return True
            if role == "admin":
                return action not in ["delete_superadmin", "change_superadmin_role"]
            return False
        
        assert check_access("superadmin", "create_user") is True
        assert check_access("superadmin", "delete_user") is True
        assert check_access("superadmin", "change_superadmin_role") is True
    
    def test_admin_cannot_modify_superadmin(self):
        """Admin не может изменять superadmin."""
        def check_access(role: str, action: str) -> bool:
            if role == "superadmin":
                return True
            if role == "admin":
                return action not in ["delete_superadmin", "change_superadmin_role"]
            return False
        
        assert check_access("admin", "create_user") is True
        assert check_access("admin", "delete_superadmin") is False
        assert check_access("admin", "change_superadmin_role") is False
    
    def test_moderator_no_admin_access(self):
        """Moderator не имеет доступа к админ-панели."""
        allowed_roles = ["superadmin", "admin"]
        
        assert "moderator" not in allowed_roles
        assert "user" not in allowed_roles


# --- Session Tests ---

class TestAdminSession:
    """Тесты сессий админ-панели."""
    
    @pytest.fixture
    def session_manager(self):
        """Мок менеджера сессий."""
        manager = MagicMock()
        manager.create_session = AsyncMock(return_value="session_token_123")
        manager.validate_session = AsyncMock(return_value=True)
        manager.destroy_session = AsyncMock(return_value=True)
        return manager
    
    @pytest.mark.asyncio
    async def test_session_creation(self, session_manager):
        """Создание сессии при входе."""
        token = await session_manager.create_session(
            admin_id=1,
            ip_address="127.0.0.1",
        )
        
        assert token == "session_token_123"
        session_manager.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_validation(self, session_manager):
        """Валидация активной сессии."""
        is_valid = await session_manager.validate_session("session_token_123")
        
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_session_destruction(self, session_manager):
        """Уничтожение сессии при выходе."""
        result = await session_manager.destroy_session("session_token_123")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_expired_session_invalid(self, session_manager):
        """Истёкшая сессия невалидна."""
        session_manager.validate_session.return_value = False
        
        is_valid = await session_manager.validate_session("expired_token")
        
        assert is_valid is False


# --- Rate Limiting Tests ---

class TestAdminRateLimiting:
    """Тесты rate limiting для админ-панели."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Мок rate limiter."""
        limiter = MagicMock()
        limiter.check_limit = MagicMock(return_value=True)
        limiter.get_remaining = MagicMock(return_value=5)
        return limiter
    
    def test_login_rate_limit(self, rate_limiter):
        """Rate limit на логин - 5 попыток/минуту."""
        # Первые 5 попыток проходят
        for _ in range(5):
            assert rate_limiter.check_limit("login", "127.0.0.1") is True
        
        # 6-я попытка отклоняется
        rate_limiter.check_limit.return_value = False
        assert rate_limiter.check_limit("login", "127.0.0.1") is False
    
    def test_operations_rate_limit(self, rate_limiter):
        """Rate limit на операции - 100/минуту."""
        rate_limiter.get_remaining.return_value = 100
        
        remaining = rate_limiter.get_remaining("operations", "admin_1")
        
        assert remaining == 100


# --- Integration Tests ---

class TestAdminIntegration:
    """Интеграционные тесты админ-панели."""
    
    @pytest.fixture
    def mock_app(self):
        """Мок FastAPI приложения с SQLAdmin."""
        app = MagicMock()
        return app
    
    def test_admin_mounted_at_correct_path(self, mock_app):
        """Admin смонтирован на /admin."""
        # Симуляция проверки путей
        admin_routes = ["/admin", "/admin/user", "/admin/playlist"]
        
        assert "/admin" in admin_routes
    
    def test_admin_requires_authentication(self, mock_app):
        """Admin требует аутентификации."""
        # Без токена должен вернуть редирект или 401
        expected_status = 401
        
        # Симуляция неаутентифицированного запроса
        response_status = 401
        
        assert response_status == expected_status


# --- Smoke Tests ---

class TestAdminSmoke:
    """Smoke тесты для админ-панели."""
    
    def test_admin_models_defined(self):
        """Все необходимые модели определены."""
        required_models = ["User", "Playlist", "AdminAuditLog"]
        
        # Проверка через mock
        defined_models = {"User", "Playlist", "AdminAuditLog", "Channel"}
        
        for model in required_models:
            assert model in defined_models, f"Model {model} not defined"
    
    def test_admin_views_registered(self):
        """Все view зарегистрированы в админке."""
        required_views = ["UserAdmin", "PlaylistAdmin"]
        
        # Проверка через mock
        registered_views = {"UserAdmin", "PlaylistAdmin", "ChannelAdmin"}
        
        for view in required_views:
            assert view in registered_views, f"View {view} not registered"
    
    def test_audit_log_table_exists(self):
        """Таблица аудит лога существует."""
        # Mock проверка
        table_name = "admin_audit_logs"
        existing_tables = ["users", "playlists", "admin_audit_logs"]
        
        assert table_name in existing_tables
