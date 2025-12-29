"""
Comprehensive tests for TelegramAuthService (telegram_auth.py)

Coverage targets:
- Initialization
- send_code: success, rate limits, errors, client cleanup
- sign_in: code validation, 2FA required, 2FA password, session export, DB save
- sign_in_public: similar flow without DB save
- resend_code: alternative delivery methods
- Rate limiting integration
- Client lifecycle management
- Error handling (LIMIT_ERRORS, PhoneCodeExpired, invalid password)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PasswordHashInvalid,
    PhoneCodeExpired,
    FloodWait,
    PhoneNumberFlood,
)
from src.services.telegram_auth import (
    TelegramAuthService,
    RateLimitError,
    _pending_clients,
)
from src.models.telegram import TelegramAccount


# ==================== Fixtures ====================

@pytest.fixture
def telegram_auth_service():
    """TelegramAuthService instance"""
    service = TelegramAuthService()
    service.api_id = 12345
    service.api_hash = "test_api_hash"
    service.redis_url = "redis://localhost:6379/0"
    return service


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_pyrogram_client():
    """Mock Pyrogram Client"""
    client = Mock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_code = AsyncMock()
    client.sign_in = AsyncMock()
    client.check_password = AsyncMock()
    client.export_session_string = AsyncMock(return_value="session_string_12345")
    client.resend_code = AsyncMock()
    client.is_connected = True
    client.workdir = None
    return client


@pytest.fixture
def mock_sent_code():
    """Mock Pyrogram SentCode object"""
    sent_code = Mock()
    sent_code.phone_code_hash = "hash_12345"
    sent_code.type = Mock()
    sent_code.type.__class__.__name__ = "SentCodeTypeApp"
    sent_code.next_type = None
    sent_code.timeout = None
    return sent_code


@pytest.fixture
def mock_user():
    """Mock Pyrogram User object"""
    user = Mock()
    user.id = 123456789
    user.first_name = "Test"
    user.username = "testuser"
    user.phone = "+1234567890"
    return user


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session"""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_rate_limiter():
    """Mock rate_limiter with all methods"""
    limiter = Mock()
    limiter.check_limit = AsyncMock(return_value=None)
    limiter.clear_limit = AsyncMock()
    limiter.record_limit = AsyncMock()
    limiter.parse_error = Mock()
    return limiter


@pytest.fixture(autouse=True)
def clear_pending_clients():
    """Clear _pending_clients before each test"""
    _pending_clients.clear()
    yield
    _pending_clients.clear()


# ==================== TelegramAuthService Initialization ====================

class TestTelegramAuthServiceInit:
    """Test service initialization"""

    def test_init_with_defaults(self):
        """Test initialization uses config settings"""
        service = TelegramAuthService()
        assert service.api_id is not None
        assert service.api_hash is not None
        assert service.redis_url is not None

    @pytest.mark.asyncio
    async def test_get_redis_connection(self, telegram_auth_service, mock_redis):
        """Test Redis connection creation"""
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            redis_client = await telegram_auth_service._get_redis()
            assert redis_client == mock_redis


# ==================== send_code Tests ====================

class TestSendCode:
    """Test send_code method"""

    @pytest.mark.asyncio
    async def test_send_code_success(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_sent_code,
        mock_rate_limiter
    ):
        """Test successful code sending"""
        phone = "+1234567890"
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.send_code.return_value = mock_sent_code
            
            result = await telegram_auth_service.send_code(phone)
            
            # Assertions
            assert result["status"] == "code_sent"
            assert result["phone_code_hash"] == "hash_12345"
            
            # Verify client connected
            mock_pyrogram_client.connect.assert_called_once()
            mock_pyrogram_client.send_code.assert_called_once_with(phone)
            
            # Verify Redis operations
            mock_redis.setex.assert_called_once()
            mock_redis.close.assert_called()
            
            # Verify rate limiter cleared
            mock_rate_limiter.clear_limit.assert_called_once_with(phone)
            
            # Verify client stored in memory
            assert phone in _pending_clients
            stored_client, stored_hash = _pending_clients[phone]
            assert stored_hash == "hash_12345"

    @pytest.mark.asyncio
    async def test_send_code_with_active_rate_limit(
        self, 
        telegram_auth_service, 
        mock_rate_limiter
    ):
        """Test send_code blocked by active rate limit"""
        phone = "+1234567890"
        
        # Create mock limit_info
        limit_info = Mock()
        limit_info.is_active = True
        limit_info.remaining_seconds = 120
        limit_info.message = "Rate limit active, wait 120s"
        
        mock_rate_limiter.check_limit.return_value = limit_info
        
        with patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            with pytest.raises(RateLimitError) as exc_info:
                await telegram_auth_service.send_code(phone)
            
            assert exc_info.value.limit_info == limit_info
            mock_rate_limiter.check_limit.assert_called_once_with(phone)

    @pytest.mark.asyncio
    async def test_send_code_cleanup_old_client(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_sent_code,
        mock_rate_limiter
    ):
        """Test cleanup of old pending client"""
        phone = "+1234567890"
        
        # Add old client to _pending_clients
        old_client = Mock()
        old_client.disconnect = AsyncMock()
        _pending_clients[phone] = (old_client, "old_hash")
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.send_code.return_value = mock_sent_code
            
            await telegram_auth_service.send_code(phone)
            
            # Verify old client disconnected
            old_client.disconnect.assert_called_once()
            
            # Verify new client stored
            assert phone in _pending_clients
            stored_client, stored_hash = _pending_clients[phone]
            assert stored_hash == "hash_12345"

    @pytest.mark.asyncio
    async def test_send_code_flood_wait_error(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client,
        mock_rate_limiter
    ):
        """Test FloodWait error handling"""
        phone = "+1234567890"
        
        flood_error = FloodWait(value=300)  # 300 seconds wait
        mock_pyrogram_client.send_code.side_effect = flood_error
        
        limit_info = Mock()
        limit_info.type = Mock(value="flood_wait")
        limit_info.wait_seconds = 300
        limit_info.phone = phone
        mock_rate_limiter.parse_error.return_value = limit_info
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.connect = AsyncMock()
            
            with pytest.raises(RateLimitError):
                await telegram_auth_service.send_code(phone)
            
            # Verify rate limiter recorded error
            mock_rate_limiter.record_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_code_phone_number_flood(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client,
        mock_rate_limiter
    ):
        """Test PhoneNumberFlood error handling"""
        phone = "+1234567890"
        
        flood_error = PhoneNumberFlood()
        mock_pyrogram_client.send_code.side_effect = flood_error
        
        limit_info = Mock()
        limit_info.type = Mock(value="phone_number_flood")
        limit_info.wait_seconds = 86400  # 24 hours
        limit_info.phone = phone
        mock_rate_limiter.parse_error.return_value = limit_info
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.connect = AsyncMock()
            
            with pytest.raises(RateLimitError):
                await telegram_auth_service.send_code(phone)

    @pytest.mark.asyncio
    async def test_send_code_generic_error_with_flood_keyword(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client,
        mock_rate_limiter
    ):
        """Test generic error containing flood keywords"""
        phone = "+1234567890"
        
        # Generic error with flood keyword
        error = Exception("Service temporarily unavailable due to FLOOD")
        mock_pyrogram_client.send_code.side_effect = error
        
        limit_info = Mock()
        limit_info.type = Mock(value="generic_flood")
        limit_info.wait_seconds = 600
        limit_info.phone = phone
        mock_rate_limiter.parse_error.return_value = limit_info
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.connect = AsyncMock()
            
            with pytest.raises(RateLimitError):
                await telegram_auth_service.send_code(phone)
            
            mock_rate_limiter.record_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_code_non_flood_error(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client,
        mock_rate_limiter
    ):
        """Test non-flood error handling (generic exception)"""
        phone = "+1234567890"
        
        error = Exception("Network error")
        mock_pyrogram_client.send_code.side_effect = error
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.connect = AsyncMock()
            
            with pytest.raises(Exception) as exc_info:
                await telegram_auth_service.send_code(phone)
            
            assert str(exc_info.value) == "Network error"
            # Verify client disconnected on error
            mock_pyrogram_client.disconnect.assert_called()


# ==================== sign_in Tests ====================

class TestSignIn:
    """Test sign_in method"""

    @pytest.mark.asyncio
    async def test_sign_in_success_without_2fa(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user,
        mock_db_session
    ):
        """Test successful sign_in without 2FA"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        # Setup pending client
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.return_value = mock_user
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.SessionLocal", return_value=mock_db_session), \
             patch("src.services.telegram_auth.encryption_service") as mock_encryption:
            
            mock_encryption.encrypt.return_value = "encrypted_session"
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            result = await telegram_auth_service.sign_in(user_id, phone, code)
            
            # Assertions
            assert result["status"] == "success"
            assert result["user"]["id"] == 123456789
            assert result["user"]["username"] == "testuser"
            
            # Verify sign_in called
            mock_pyrogram_client.sign_in.assert_called_once_with(phone, "hash_12345", code)
            
            # Verify session exported and encrypted
            mock_pyrogram_client.export_session_string.assert_called_once()
            mock_encryption.encrypt.assert_called_once_with("session_string_12345")
            
            # Verify DB operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            
            # Verify cleanup
            assert phone not in _pending_clients
            mock_redis.delete.assert_called_once_with(f"auth:{phone}:hash")
            mock_pyrogram_client.disconnect.assert_called()

    @pytest.mark.asyncio
    async def test_sign_in_2fa_required(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client
    ):
        """Test sign_in returns 2fa_required"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = SessionPasswordNeeded()
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            result = await telegram_auth_service.sign_in(user_id, phone, code)
            
            # Assertions
            assert result["status"] == "2fa_required"
            
            # Verify client NOT disconnected (needed for next call)
            mock_pyrogram_client.disconnect.assert_not_called()
            
            # Verify TTL extended in Redis
            mock_redis.set.assert_called_once()
            
            # Verify client still in memory
            assert phone in _pending_clients

    @pytest.mark.asyncio
    async def test_sign_in_with_2fa_password(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user,
        mock_db_session
    ):
        """Test sign_in with 2FA password"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        password = "my_password"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.check_password.return_value = mock_user
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.SessionLocal", return_value=mock_db_session), \
             patch("src.services.telegram_auth.encryption_service") as mock_encryption:
            
            mock_encryption.encrypt.return_value = "encrypted_session"
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            result = await telegram_auth_service.sign_in(user_id, phone, code, password)
            
            # Assertions
            assert result["status"] == "success"
            
            # Verify check_password called, NOT sign_in
            mock_pyrogram_client.check_password.assert_called_once_with(password)
            mock_pyrogram_client.sign_in.assert_not_called()

    @pytest.mark.asyncio
    async def test_sign_in_invalid_2fa_password(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test sign_in with invalid 2FA password"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        password = "wrong_password"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.check_password.side_effect = PasswordHashInvalid()
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in(user_id, phone, code, password)
        
        assert "Неверный пароль 2FA" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_no_pending_client(self, telegram_auth_service):
        """Test sign_in fails when no pending client"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in(user_id, phone, code)
        
        assert "Сессия истекла" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_client_disconnected(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test sign_in fails when client disconnected"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        mock_pyrogram_client.is_connected = False
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in(user_id, phone, code)
        
        assert "Клиент отключился" in str(exc_info.value)
        # Verify client removed from memory
        assert phone not in _pending_clients

    @pytest.mark.asyncio
    async def test_sign_in_phone_code_expired(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test sign_in with expired code"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = PhoneCodeExpired()
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in(user_id, phone, code)
        
        assert "Код истёк" in str(exc_info.value)
        # Verify client removed and disconnected
        assert phone not in _pending_clients
        mock_pyrogram_client.disconnect.assert_called()

    @pytest.mark.asyncio
    async def test_sign_in_invalid_code(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test sign_in with invalid code"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "99999"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = PhoneCodeInvalid()
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in(user_id, phone, code)
        
        assert "Invalid code or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_updates_existing_account(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user,
        mock_db_session
    ):
        """Test sign_in updates existing TelegramAccount"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.return_value = mock_user
        
        # Existing account
        existing_account = Mock(spec=TelegramAccount)
        existing_account.encrypted_session = "old_session"
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.SessionLocal", return_value=mock_db_session), \
             patch("src.services.telegram_auth.encryption_service") as mock_encryption:
            
            mock_encryption.encrypt.return_value = "new_encrypted_session"
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_account
            
            await telegram_auth_service.sign_in(user_id, phone, code)
            
            # Verify existing account updated
            assert existing_account.encrypted_session == "new_encrypted_session"
            assert existing_account.tg_user_id == 123456789
            mock_db_session.add.assert_not_called()  # Not adding new
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_workdir_cleanup(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user,
        mock_db_session
    ):
        """Test workdir cleanup after successful sign_in"""
        phone = "+1234567890"
        user_id = "user_123"
        code = "12345"
        
        # Create temp workdir
        temp_workdir = tempfile.mkdtemp(prefix="test_pyrogram_")
        mock_pyrogram_client.workdir = temp_workdir
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.return_value = mock_user
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.SessionLocal", return_value=mock_db_session), \
             patch("src.services.telegram_auth.encryption_service") as mock_encryption:
            
            mock_encryption.encrypt.return_value = "encrypted_session"
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            await telegram_auth_service.sign_in(user_id, phone, code)
            
            # Verify workdir removed
            assert not os.path.exists(temp_workdir)


# ==================== sign_in_public Tests ====================

class TestSignInPublic:
    """Test sign_in_public method (public auth without DB save)"""

    @pytest.mark.asyncio
    async def test_sign_in_public_success(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user
    ):
        """Test successful public sign_in"""
        phone = "+1234567890"
        code = "12345"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.return_value = mock_user
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            result = await telegram_auth_service.sign_in_public(phone, code)
            
            # Assertions
            assert result["status"] == "success"
            assert result["telegram_id"] == 123456789
            assert result["first_name"] == "Test"
            assert result["username"] == "testuser"
            assert result["phone"] == phone
            assert result["session_string"] == "session_string_12345"
            
            # Verify cleanup
            assert phone not in _pending_clients
            mock_redis.delete.assert_called_once_with(f"auth:{phone}:hash")

    @pytest.mark.asyncio
    async def test_sign_in_public_2fa_required(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client
    ):
        """Test public sign_in returns 2fa_required"""
        phone = "+1234567890"
        code = "12345"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = SessionPasswordNeeded()
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            result = await telegram_auth_service.sign_in_public(phone, code)
            
            assert result["status"] == "2fa_required"
            
            # Verify client NOT disconnected
            mock_pyrogram_client.disconnect.assert_not_called()
            
            # Verify still in memory
            assert phone in _pending_clients

    @pytest.mark.asyncio
    async def test_sign_in_public_with_password(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_user
    ):
        """Test public sign_in with 2FA password"""
        phone = "+1234567890"
        code = "12345"
        password = "my_password"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.check_password.return_value = mock_user
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            result = await telegram_auth_service.sign_in_public(phone, code, password)
            
            assert result["status"] == "success"
            mock_pyrogram_client.check_password.assert_called_once_with(password)
            mock_pyrogram_client.sign_in.assert_not_called()

    @pytest.mark.asyncio
    async def test_sign_in_public_invalid_password(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test public sign_in with invalid 2FA password"""
        phone = "+1234567890"
        code = "12345"
        password = "wrong"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.check_password.side_effect = PasswordHashInvalid()
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in_public(phone, code, password)
        
        assert "Неверный пароль 2FA" in str(exc_info.value)
        # Verify cleanup on error
        assert phone not in _pending_clients

    @pytest.mark.asyncio
    async def test_sign_in_public_no_pending_client(self, telegram_auth_service):
        """Test public sign_in fails without pending client"""
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in_public("+1234567890", "12345")
        
        assert "Сессия истекла" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_public_client_disconnected(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test public sign_in fails when client disconnected"""
        phone = "+1234567890"
        
        mock_pyrogram_client.is_connected = False
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in_public(phone, "12345")
        
        assert "Клиент отключился" in str(exc_info.value)
        assert phone not in _pending_clients

    @pytest.mark.asyncio
    async def test_sign_in_public_phone_code_expired(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test public sign_in with expired code"""
        phone = "+1234567890"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = PhoneCodeExpired()
        
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.sign_in_public(phone, "12345")
        
        assert "Код истёк" in str(exc_info.value)
        assert phone not in _pending_clients


# ==================== resend_code Tests ====================

class TestResendCode:
    """Test resend_code method"""

    @pytest.mark.asyncio
    async def test_resend_code_success(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_sent_code
    ):
        """Test successful code resend"""
        phone = "+1234567890"
        
        _pending_clients[phone] = (mock_pyrogram_client, "old_hash")
        
        # New sent code after resend
        new_sent_code = Mock()
        new_sent_code.phone_code_hash = "new_hash_67890"
        new_sent_code.type = Mock()
        new_sent_code.type.__class__.__name__ = "SentCodeTypeSms"
        new_sent_code.next_type = Mock()
        new_sent_code.next_type.__class__.__name__ = "SentCodeTypeCall"
        new_sent_code.timeout = 60
        
        mock_pyrogram_client.resend_code.return_value = new_sent_code
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)):
            result = await telegram_auth_service.resend_code(phone)
            
            # Assertions
            assert result["status"] == "code_resent"
            assert result["phone_code_hash"] == "new_hash_67890"
            assert result["code_type"] == "SentCodeTypeSms"
            assert result["next_type"] == "SentCodeTypeCall"
            assert result["timeout"] == 60
            
            # Verify client method called
            mock_pyrogram_client.resend_code.assert_called_once_with(phone, "old_hash")
            
            # Verify updated in memory
            stored_client, stored_hash = _pending_clients[phone]
            assert stored_hash == "new_hash_67890"
            
            # Verify Redis updated
            mock_redis.setex.assert_called_once_with(f"auth:{phone}:hash", 300, "new_hash_67890")

    @pytest.mark.asyncio
    async def test_resend_code_no_pending_client(self, telegram_auth_service):
        """Test resend_code fails without pending client"""
        with pytest.raises(ValueError) as exc_info:
            await telegram_auth_service.resend_code("+1234567890")
        
        assert "Session expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resend_code_error(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test resend_code error handling"""
        phone = "+1234567890"
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        error = Exception("Resend not available yet")
        mock_pyrogram_client.resend_code.side_effect = error
        
        with pytest.raises(Exception) as exc_info:
            await telegram_auth_service.resend_code(phone)
        
        assert "Resend not available yet" in str(exc_info.value)


# ==================== Edge Cases ====================

class TestTelegramAuthEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_rate_limit_error_has_limit_info(self, telegram_auth_service, mock_rate_limiter):
        """Test RateLimitError carries limit_info"""
        limit_info = Mock()
        limit_info.is_active = True
        limit_info.remaining_seconds = 300
        limit_info.message = "Test limit"
        
        try:
            raise RateLimitError(limit_info)
        except RateLimitError as e:
            assert e.limit_info == limit_info
            assert str(e) == "Test limit"

    @pytest.mark.asyncio
    async def test_pending_clients_isolation(
        self, 
        telegram_auth_service, 
        mock_redis, 
        mock_pyrogram_client, 
        mock_sent_code,
        mock_rate_limiter
    ):
        """Test different phones have isolated pending clients"""
        phone1 = "+1234567890"
        phone2 = "+9876543210"
        
        with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_redis)), \
             patch("src.services.telegram_auth.Client", return_value=mock_pyrogram_client), \
             patch("src.services.telegram_auth.rate_limiter", mock_rate_limiter):
            
            mock_pyrogram_client.send_code.return_value = mock_sent_code
            
            await telegram_auth_service.send_code(phone1)
            
            # Verify phone1 stored
            assert phone1 in _pending_clients
            assert phone2 not in _pending_clients

    @pytest.mark.asyncio
    async def test_workdir_cleanup_on_error(
        self, 
        telegram_auth_service, 
        mock_pyrogram_client
    ):
        """Test workdir cleanup when disconnect fails"""
        phone = "+1234567890"
        
        temp_workdir = tempfile.mkdtemp(prefix="test_cleanup_")
        mock_pyrogram_client.workdir = temp_workdir
        
        _pending_clients[phone] = (mock_pyrogram_client, "hash_12345")
        
        mock_pyrogram_client.sign_in.side_effect = PhoneCodeInvalid()
        
        with pytest.raises(ValueError):
            await telegram_auth_service.sign_in("user_123", phone, "12345")
        
        # Verify workdir cleaned up even on error
        # Note: cleanup happens in finally block
        assert not os.path.exists(temp_workdir)

    def test_clear_pending_clients_fixture(self):
        """Test fixture clears _pending_clients between tests"""
        # This is implicitly tested by all tests using the fixture
        # Just verify it's empty at start
        assert len(_pending_clients) == 0
