"""
Comprehensive tests for SessionService
Target: 70%+ coverage of session_service.py (107 lines)

Test coverage:
- __init__ and configuration loading
- issue_tokens (access + refresh token creation, Redis storage)
- rotate_refresh (token validation, jti rotation, new pair generation)
- revoke_all (logout from all devices)
- list_active_sessions (active sessions listing with TTL)
- Login lockout mechanism (is_locked, register_failure, clear_failures)
- Error handling (Redis unavailable, invalid tokens)
- Edge cases (missing jti, revoked tokens, expired sessions)
"""
import os
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from services.session_service import SessionService, TokenPair


# ======================== FIXTURES ========================
@pytest.fixture
def mock_redis():
    """Mock Redis client with common operations."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = "user_123"  # Default: jti exists
    redis_mock.exists.return_value = 0  # Default: not locked
    redis_mock.incr.return_value = 1  # Default: first failure
    redis_mock.smembers.return_value = set()  # Default: no active sessions
    redis_mock.ttl.return_value = 604800  # 7 days default TTL
    redis_mock.pipeline.return_value = redis_mock  # Support pipeline().execute()
    redis_mock.execute.return_value = [True, 1, True]  # Pipeline results
    return redis_mock


@pytest.fixture
def mock_user():
    """Sample user object with role enum."""
    user = Mock()
    user.id = 123
    user.role = Mock()
    user.role.value = "admin"
    return user


@pytest.fixture
def session_service_with_redis(mock_redis, monkeypatch):
    """SessionService with mocked Redis."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("LOGIN_LOCKOUT_THRESHOLD", "5")
    monkeypatch.setenv("LOGIN_LOCKOUT_WINDOW_MINUTES", "15")
    
    with patch("redis.from_url", return_value=mock_redis):
        service = SessionService()
    return service


@pytest.fixture
def session_service_no_redis(monkeypatch):
    """SessionService without Redis (REDIS_URL not set)."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    service = SessionService()
    return service


# ======================== TEST CLASSES ========================

class TestSessionServiceInit:
    """Test SessionService initialization and configuration."""

    def test_init_with_redis_url(self, monkeypatch):
        """Test initialization with REDIS_URL set."""
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "10")
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        monkeypatch.setenv("LOGIN_LOCKOUT_THRESHOLD", "3")
        monkeypatch.setenv("LOGIN_LOCKOUT_WINDOW_MINUTES", "30")
        
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            service = SessionService()
            
            mock_from_url.assert_called_once_with("redis://localhost:6379", decode_responses=True)
            assert service.redis is not None
            assert service.refresh_days == 10
            assert service.access_minutes == 30
            assert service.lockout_threshold == 3
            assert service.lockout_window_minutes == 30

    def test_init_without_redis_url(self, monkeypatch):
        """Test initialization without REDIS_URL (Redis disabled)."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
        monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
        
        service = SessionService()
        
        assert service.redis is None
        assert service.refresh_days == 7  # Default
        assert service.access_minutes == 15

    def test_init_default_config_values(self, monkeypatch):
        """Test default configuration values when env vars not set."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
        monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
        monkeypatch.delenv("LOGIN_LOCKOUT_THRESHOLD", raising=False)
        monkeypatch.delenv("LOGIN_LOCKOUT_WINDOW_MINUTES", raising=False)
        
        service = SessionService()
        
        assert service.redis is None
        assert service.refresh_days == 7
        assert service.access_minutes == 15
        assert service.lockout_threshold == 5
        assert service.lockout_window_minutes == 15


class TestSessionServiceRequireRedis:
    """Test _require_redis validation."""

    def test_require_redis_raises_when_no_redis(self, session_service_no_redis):
        """Test that operations requiring Redis raise HTTP 503 when Redis is None."""
        with pytest.raises(HTTPException) as exc_info:
            session_service_no_redis._require_redis()
        
        assert exc_info.value.status_code == 503
        assert "Redis is required" in exc_info.value.detail


class TestSessionServiceIssueTokens:
    """Test issue_tokens method."""

    def test_issue_tokens_success(self, session_service_with_redis, mock_redis, mock_user):
        """Test successful token pair generation with Redis storage."""
        with patch("auth.jwt.create_access_token") as mock_access, \
             patch("auth.jwt.create_refresh_token") as mock_refresh, \
             patch("uuid.uuid4") as mock_uuid:
            
            mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
            mock_access.return_value = "access_token_xyz"
            mock_refresh.return_value = "refresh_token_abc"
            
            result = session_service_with_redis.issue_tokens(mock_user)
            
            # Verify token creation
            assert isinstance(result, TokenPair)
            assert result.access_token == "access_token_xyz"
            assert result.refresh_token == "refresh_token_abc"
            
            # Verify JWT creation with correct parameters
            mock_access.assert_called_once()
            access_call = mock_access.call_args
            assert access_call[0][0] == {"sub": "123", "role": "admin"}
            assert access_call[1]["expires_delta"] == timedelta(minutes=15)
            
            mock_refresh.assert_called_once()
            refresh_call = mock_refresh.call_args
            assert refresh_call[0][0] == {"sub": "123", "role": "admin", "jti": "12345678-1234-5678-1234-567812345678"}
            assert refresh_call[1]["expires_delta"] == timedelta(days=7)
            
            # Verify Redis storage (pipeline operations)
            mock_redis.pipeline.assert_called_once()
            mock_redis.setex.assert_called_once_with(
                "auth:refresh:12345678-1234-5678-1234-567812345678",
                604800,  # 7 days * 86400
                "123"
            )
            mock_redis.sadd.assert_called_once_with(
                "auth:user-refresh:123",
                "12345678-1234-5678-1234-567812345678"
            )
            mock_redis.expire.assert_called_once_with("auth:user-refresh:123", 604800)

    def test_issue_tokens_user_without_role_value(self, session_service_with_redis, mock_redis):
        """Test issue_tokens with user.role as string (no .value attribute)."""
        user = Mock()
        user.id = 456
        user.role = "moderator"  # String, no .value attribute
        
        with patch("auth.jwt.create_access_token") as mock_access, \
             patch("auth.jwt.create_refresh_token") as mock_refresh, \
             patch("uuid.uuid4"):
            
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"
            
            result = session_service_with_redis.issue_tokens(user)
            
            assert result.access_token == "access_token"
            assert result.refresh_token == "refresh_token"
            
            # Verify role is converted to string
            access_call = mock_access.call_args
            assert access_call[0][0]["role"] == "moderator"

    def test_issue_tokens_user_with_none_role(self, session_service_with_redis, mock_redis):
        """Test issue_tokens with user.role = None."""
        user = Mock()
        user.id = 789
        user.role = None
        
        with patch("auth.jwt.create_access_token") as mock_access, \
             patch("auth.jwt.create_refresh_token") as mock_refresh, \
             patch("uuid.uuid4"):
            
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"
            
            result = session_service_with_redis.issue_tokens(user)
            
            assert result.access_token == "access_token"
            
            # Verify role is None
            access_call = mock_access.call_args
            assert access_call[0][0]["role"] is None

    def test_issue_tokens_no_redis_raises_503(self, session_service_no_redis, mock_user):
        """Test issue_tokens raises HTTP 503 when Redis is not available."""
        with pytest.raises(HTTPException) as exc_info:
            session_service_no_redis.issue_tokens(mock_user)
        
        assert exc_info.value.status_code == 503
        assert "Redis is required" in exc_info.value.detail


class TestSessionServiceRotateRefresh:
    """Test rotate_refresh method."""

    def test_rotate_refresh_success(self, session_service_with_redis, mock_redis):
        """Test successful refresh token rotation."""
        old_jti = "old-jti-12345"
        new_jti_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        mock_redis.get.return_value = "user_123"  # Old jti exists
        
        with patch("auth.jwt.decode_refresh_token") as mock_decode, \
             patch("auth.jwt.create_access_token") as mock_access, \
             patch("auth.jwt.create_refresh_token") as mock_refresh, \
             patch("uuid.uuid4") as mock_uuid:
            
            mock_decode.return_value = {"jti": old_jti, "sub": "123", "role": "admin"}
            mock_uuid.return_value = new_jti_uuid
            mock_access.return_value = "new_access_token"
            mock_refresh.return_value = "new_refresh_token"
            
            result = session_service_with_redis.rotate_refresh("old_refresh_token")
            
            assert result.access_token == "new_access_token"
            assert result.refresh_token == "new_refresh_token"
            
            # Verify old jti deletion
            mock_redis.delete.assert_any_call(f"auth:refresh:{old_jti}")
            mock_redis.srem.assert_called_once_with("auth:user-refresh:123", old_jti)
            
            # Verify new jti storage
            mock_redis.setex.assert_called_once()
            assert "12345678-1234-5678-1234-567812345678" in str(mock_redis.setex.call_args)

    def test_rotate_refresh_invalid_token_payload(self, session_service_with_redis):
        """Test rotate_refresh with invalid token (decode returns None)."""
        with patch("auth.jwt.decode_refresh_token") as mock_decode:
            mock_decode.return_value = None  # Invalid token
            
            with pytest.raises(HTTPException) as exc_info:
                session_service_with_redis.rotate_refresh("invalid_token")
            
            assert exc_info.value.status_code == 401
            assert "Invalid refresh token" in exc_info.value.detail

    def test_rotate_refresh_missing_jti(self, session_service_with_redis):
        """Test rotate_refresh with token missing jti."""
        with patch("auth.jwt.decode_refresh_token") as mock_decode:
            mock_decode.return_value = {"sub": "123", "role": "admin"}  # No jti
            
            with pytest.raises(HTTPException) as exc_info:
                session_service_with_redis.rotate_refresh("token_without_jti")
            
            assert exc_info.value.status_code == 401
            assert "Invalid refresh token" in exc_info.value.detail

    def test_rotate_refresh_missing_sub(self, session_service_with_redis):
        """Test rotate_refresh with token missing sub."""
        with patch("auth.jwt.decode_refresh_token") as mock_decode:
            mock_decode.return_value = {"jti": "some-jti", "role": "admin"}  # No sub
            
            with pytest.raises(HTTPException) as exc_info:
                session_service_with_redis.rotate_refresh("token_without_sub")
            
            assert exc_info.value.status_code == 401
            assert "Invalid refresh token" in exc_info.value.detail

    def test_rotate_refresh_revoked_token(self, session_service_with_redis, mock_redis):
        """Test rotate_refresh with revoked token (jti not in Redis)."""
        mock_redis.get.return_value = None  # jti not found (revoked)
        
        with patch("auth.jwt.decode_refresh_token") as mock_decode:
            mock_decode.return_value = {"jti": "revoked-jti", "sub": "123", "role": "user"}
            
            with pytest.raises(HTTPException) as exc_info:
                session_service_with_redis.rotate_refresh("revoked_token")
            
            assert exc_info.value.status_code == 401
            assert "Refresh token revoked" in exc_info.value.detail

    def test_rotate_refresh_no_redis_raises_503(self, session_service_no_redis):
        """Test rotate_refresh raises HTTP 503 when Redis is not available."""
        with pytest.raises(HTTPException) as exc_info:
            session_service_no_redis.rotate_refresh("some_token")
        
        assert exc_info.value.status_code == 503


class TestSessionServiceRevokeAll:
    """Test revoke_all method."""

    def test_revoke_all_success(self, session_service_with_redis, mock_redis):
        """Test successful revocation of all user sessions."""
        mock_redis.smembers.return_value = {"jti1", "jti2", "jti3"}
        
        session_service_with_redis.revoke_all(123)
        
        # Verify pipeline operations
        mock_redis.pipeline.assert_called_once()
        assert mock_redis.delete.call_count == 4  # 3 jtis + 1 user set
        mock_redis.delete.assert_any_call("auth:refresh:jti1")
        mock_redis.delete.assert_any_call("auth:refresh:jti2")
        mock_redis.delete.assert_any_call("auth:refresh:jti3")
        mock_redis.delete.assert_any_call("auth:user-refresh:123")

    def test_revoke_all_no_active_sessions(self, session_service_with_redis, mock_redis):
        """Test revoke_all when user has no active sessions."""
        mock_redis.smembers.return_value = set()  # Empty set
        
        session_service_with_redis.revoke_all(456)
        
        # Pipeline should not be created if no jtis to delete
        mock_redis.pipeline.assert_not_called()

    def test_revoke_all_none_return_from_smembers(self, session_service_with_redis, mock_redis):
        """Test revoke_all when smembers returns None."""
        mock_redis.smembers.return_value = None
        
        session_service_with_redis.revoke_all(789)
        
        mock_redis.pipeline.assert_not_called()

    def test_revoke_all_no_redis_raises_503(self, session_service_no_redis):
        """Test revoke_all raises HTTP 503 when Redis is not available."""
        with pytest.raises(HTTPException) as exc_info:
            session_service_no_redis.revoke_all(123)
        
        assert exc_info.value.status_code == 503


class TestSessionServiceListActiveSessions:
    """Test list_active_sessions method."""

    def test_list_active_sessions_success(self, session_service_with_redis, mock_redis):
        """Test listing active sessions with valid TTLs."""
        jtis_set = {"jti1", "jti2", "jti3"}
        mock_redis.smembers.return_value = jtis_set
        
        # Use ttl side_effect function to map TTL by key
        def ttl_side_effect(key):
            if "jti1" in key:
                return 3600
            elif "jti2" in key:
                return 7200
            elif "jti3" in key:
                return 10800
            return -1
        
        mock_redis.ttl.side_effect = ttl_side_effect
        
        sessions = session_service_with_redis.list_active_sessions(123)
        
        assert len(sessions) == 3
        # Check each jti exists with correct TTL
        jti_ttls = {s["jti"]: s["ttl_sec"] for s in sessions}
        assert jti_ttls["jti1"] == 3600
        assert jti_ttls["jti2"] == 7200
        assert jti_ttls["jti3"] == 10800

    def test_list_active_sessions_auto_cleanup_expired(self, session_service_with_redis, mock_redis):
        """Test auto-cleanup of expired sessions (TTL <= 0)."""
        # Use ordered list for deterministic ttl.side_effect mapping
        jtis_list = ["jti_active", "jti_expired1", "jti_expired2"]
        mock_redis.smembers.return_value = set(jtis_list)
        
        # Map TTL by jti for correct behavior
        def ttl_side_effect(key):
            if "jti_active" in key:
                return 5000
            elif "jti_expired1" in key:
                return -1
            elif "jti_expired2" in key:
                return 0
            return -2
        
        mock_redis.ttl.side_effect = ttl_side_effect
        
        sessions = session_service_with_redis.list_active_sessions(456)
        
        # Only active session returned
        assert len(sessions) == 1
        active_session = next(s for s in sessions if s["jti"] == "jti_active")
        assert active_session["ttl_sec"] == 5000
        
        # Expired jtis removed from user set
        assert mock_redis.srem.call_count == 2
        mock_redis.srem.assert_any_call("auth:user-refresh:456", "jti_expired1")
        mock_redis.srem.assert_any_call("auth:user-refresh:456", "jti_expired2")

    def test_list_active_sessions_no_sessions(self, session_service_with_redis, mock_redis):
        """Test list_active_sessions when user has no sessions."""
        mock_redis.smembers.return_value = set()
        
        sessions = session_service_with_redis.list_active_sessions(789)
        
        assert sessions == []

    def test_list_active_sessions_none_from_smembers(self, session_service_with_redis, mock_redis):
        """Test list_active_sessions when smembers returns None."""
        mock_redis.smembers.return_value = None
        
        sessions = session_service_with_redis.list_active_sessions(101)
        
        assert sessions == []

    def test_list_active_sessions_no_redis_raises_503(self, session_service_no_redis):
        """Test list_active_sessions raises HTTP 503 when Redis is not available."""
        with pytest.raises(HTTPException) as exc_info:
            session_service_no_redis.list_active_sessions(123)
        
        assert exc_info.value.status_code == 503


class TestSessionServiceLoginLockout:
    """Test login lockout mechanism (is_locked, register_failure, clear_failures)."""

    def test_is_locked_returns_true_when_locked(self, session_service_with_redis, mock_redis):
        """Test is_locked returns True when lock key exists."""
        mock_redis.exists.return_value = 1
        
        assert session_service_with_redis.is_locked("user@example.com") is True
        mock_redis.exists.assert_called_once_with("auth:lock:user@example.com")

    def test_is_locked_returns_false_when_not_locked(self, session_service_with_redis, mock_redis):
        """Test is_locked returns False when lock key does not exist."""
        mock_redis.exists.return_value = 0
        
        assert session_service_with_redis.is_locked("user@example.com") is False

    def test_is_locked_no_redis_returns_false(self, session_service_no_redis):
        """Test is_locked returns False when Redis is not available."""
        assert session_service_no_redis.is_locked("user@example.com") is False

    def test_is_locked_normalizes_identifier(self, session_service_with_redis, mock_redis):
        """Test is_locked converts identifier to lowercase."""
        mock_redis.exists.return_value = 0
        
        session_service_with_redis.is_locked("User@Example.COM")
        
        mock_redis.exists.assert_called_once_with("auth:lock:user@example.com")

    def test_register_failure_increments_and_sets_expiry(self, session_service_with_redis, mock_redis):
        """Test register_failure increments failure counter and sets expiry."""
        mock_redis.incr.return_value = 3  # 3rd failure
        
        session_service_with_redis.register_failure("user@example.com")
        
        mock_redis.incr.assert_called_once_with("auth:fail:user@example.com")
        mock_redis.expire.assert_called_once_with("auth:fail:user@example.com", 900)  # 15 min * 60

    def test_register_failure_locks_after_threshold(self, session_service_with_redis, mock_redis):
        """Test register_failure creates lock key after reaching threshold."""
        mock_redis.incr.return_value = 5  # Reached threshold
        
        session_service_with_redis.register_failure("attacker@example.com")
        
        mock_redis.setex.assert_called_once_with("auth:lock:attacker@example.com", 900, "1")

    def test_register_failure_does_not_lock_below_threshold(self, session_service_with_redis, mock_redis):
        """Test register_failure does not lock before threshold."""
        mock_redis.incr.return_value = 4  # Below threshold (5)
        
        session_service_with_redis.register_failure("user@example.com")
        
        mock_redis.setex.assert_not_called()

    def test_register_failure_no_redis_does_nothing(self, session_service_no_redis):
        """Test register_failure does nothing when Redis is not available."""
        # Should not raise, just return silently
        session_service_no_redis.register_failure("user@example.com")

    def test_clear_failures_deletes_both_keys(self, session_service_with_redis, mock_redis):
        """Test clear_failures removes both fail and lock keys."""
        session_service_with_redis.clear_failures("user@example.com")
        
        assert mock_redis.delete.call_count == 2
        mock_redis.delete.assert_any_call("auth:fail:user@example.com")
        mock_redis.delete.assert_any_call("auth:lock:user@example.com")

    def test_clear_failures_no_redis_does_nothing(self, session_service_no_redis):
        """Test clear_failures does nothing when Redis is not available."""
        # Should not raise
        session_service_no_redis.clear_failures("user@example.com")

    def test_fail_key_normalizes_identifier(self):
        """Test _fail_key static method converts to lowercase."""
        assert SessionService._fail_key("User@Example.COM") == "auth:fail:user@example.com"

    def test_lock_key_normalizes_identifier(self):
        """Test _lock_key static method converts to lowercase."""
        assert SessionService._lock_key("User@Example.COM") == "auth:lock:user@example.com"


class TestSessionServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_store_refresh_pipeline_execution(self, session_service_with_redis, mock_redis):
        """Test _store_refresh uses Redis pipeline correctly."""
        session_service_with_redis._store_refresh(999, "test-jti-999")
        
        mock_redis.pipeline.assert_called_once()
        mock_redis.setex.assert_called_once_with("auth:refresh:test-jti-999", 604800, "999")
        mock_redis.sadd.assert_called_once_with("auth:user-refresh:999", "test-jti-999")
        mock_redis.expire.assert_called_once_with("auth:user-refresh:999", 604800)
        mock_redis.execute.assert_called_once()

    def test_rotate_refresh_with_string_user_id(self, session_service_with_redis, mock_redis):
        """Test rotate_refresh handles string user_id correctly."""
        mock_redis.get.return_value = "user_str"
        
        with patch("auth.jwt.decode_refresh_token") as mock_decode, \
             patch("auth.jwt.create_access_token") as mock_access, \
             patch("auth.jwt.create_refresh_token") as mock_refresh, \
             patch("uuid.uuid4"):
            
            mock_decode.return_value = {"jti": "jti-123", "sub": "string_user_id", "role": "guest"}
            mock_access.return_value = "access"
            mock_refresh.return_value = "refresh"
            
            result = session_service_with_redis.rotate_refresh("token")
            
            assert result.access_token == "access"
            mock_redis.srem.assert_called_once_with("auth:user-refresh:string_user_id", "jti-123")
