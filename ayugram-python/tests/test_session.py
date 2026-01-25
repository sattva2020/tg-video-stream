"""
Unit tests for Session Management.

This module tests the SessionManager implementation including session creation,
loading, saving, deletion, caching, and corruption handling.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ayugram.session import SessionManager
from ayugram.exceptions import AyuGramError, AuthenticationError


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_session_dir():
    """
    Create a temporary directory for session files.

    Automatically cleaned up after each test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def session_manager(temp_session_dir):
    """Create a SessionManager instance for testing."""
    return SessionManager(temp_session_dir)


@pytest.fixture
def sample_session_data():
    """Create sample session data for testing."""
    return {
        "phone": "+1234567890",
        "user_id": 123456789,
        "auth_key": "base64_encoded_auth_key",
        "created_at": "2025-01-25T10:00:00Z",
        "last_used": "2025-01-25T12:00:00Z",
    }


@pytest.fixture
def invalid_session_data():
    """Create invalid session data for testing error handling."""
    return {
        "phone": "+1234567890",
        # Missing user_id and auth_key
    }


@pytest.fixture
def mock_rpc_client():
    """Create a mock RPC client for authentication tests."""
    client = MagicMock()
    client.call = AsyncMock()
    return client


@pytest.fixture
async def mock_redis():
    """Create a mock Redis client for caching tests."""
    redis = AsyncMock()
    redis.from_url = AsyncMock(return_value=redis)
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.scan_iter = AsyncMock(return_value=[])
    redis.close = AsyncMock()
    return redis


# ============================================================================
# Initialization Tests
# ============================================================================


class TestSessionManagerInit:
    """Test SessionManager initialization and configuration."""

    def test_init_with_default_parameters(self, temp_session_dir):
        """Test initialization with default parameters."""
        manager = SessionManager(temp_session_dir)
        assert manager.session_dir == Path(temp_session_dir).resolve()
        assert manager._redis_enabled is False
        assert manager._redis is None
        assert manager._redis_url is None
        assert manager._redis_ttl == 3600
        assert isinstance(manager._session_cache, dict)

    def test_init_with_redis_enabled(self, temp_session_dir):
        """Test initialization with Redis URL."""
        manager = SessionManager(temp_session_dir, redis_url="redis://localhost:6379")
        assert manager._redis_url == "redis://localhost:6379"
        # Note: redis_enabled depends on REDIS_AVAILABLE, which may be False

    def test_init_with_custom_ttl(self, temp_session_dir):
        """Test initialization with custom Redis TTL."""
        manager = SessionManager(temp_session_dir, redis_ttl=7200)
        assert manager._redis_ttl == 7200

    def test_init_with_empty_session_dir_raises_error(self):
        """Test that empty session_dir raises ValueError."""
        with pytest.raises(ValueError, match="session_dir cannot be empty"):
            SessionManager("")

    def test_init_creates_session_directory(self, temp_session_dir):
        """Test that initialization creates session directory."""
        new_dir = os.path.join(temp_session_dir, "new_sessions")
        manager = SessionManager(new_dir)
        assert manager.session_dir.exists()
        assert manager.session_dir.is_dir()

    def test_init_resolves_path(self, temp_session_dir):
        """Test that session_dir path is resolved."""
        manager = SessionManager(temp_session_dir)
        assert manager.session_dir.is_absolute()


# ============================================================================
# Session Creation Tests
# ============================================================================


class TestCreateSession:
    """Test session creation functionality."""

    @pytest.mark.asyncio
    async def test_create_session_with_mock_auth(self, session_manager):
        """Test session creation with mock authentication (no RPC client)."""
        phone_number = "+1234567890"

        async def mock_callback(phone):
            return "123456"

        session_data = await session_manager.create_session(phone_number, mock_callback)

        assert session_data["phone"] == phone_number
        assert session_data["user_id"] is not None
        assert isinstance(session_data["user_id"], int)
        assert session_data["auth_key"] is not None
        assert isinstance(session_data["auth_key"], str)
        assert "created_at" in session_data
        assert "last_used" in session_data

    @pytest.mark.asyncio
    async def test_create_session_with_empty_phone_raises_error(self, session_manager):
        """Test that empty phone number raises ValueError."""
        async def mock_callback(phone):
            return "123456"

        with pytest.raises(ValueError, match="phone_number cannot be empty"):
            await session_manager.create_session("", mock_callback)

    @pytest.mark.asyncio
    async def test_create_session_with_invalid_phone_format_raises_error(self, session_manager):
        """Test that phone without + prefix raises ValueError."""
        async def mock_callback(phone):
            return "123456"

        with pytest.raises(ValueError, match="must start with '\\+' and country code"):
            await session_manager.create_session("1234567890", mock_callback)

    @pytest.mark.asyncio
    async def test_create_session_with_non_callable_callback_raises_error(self, session_manager):
        """Test that non-callable callback raises ValueError."""
        with pytest.raises(ValueError, match="on_code_callback must be callable"):
            await session_manager.create_session("+1234567890", "not_callable")

    @pytest.mark.asyncio
    async def test_create_session_with_callback_exception_raises_auth_error(self, session_manager):
        """Test that callback exception raises AuthenticationError."""
        async def failing_callback(phone):
            raise Exception("User cancelled")

        with pytest.raises(AuthenticationError, match="Failed to get code from callback"):
            await session_manager.create_session("+1234567890", failing_callback)

    @pytest.mark.asyncio
    async def test_create_session_with_invalid_code_raises_auth_error(self, session_manager):
        """Test that invalid code from callback raises AuthenticationError."""
        async def mock_callback(phone):
            return None  # Invalid code

        with pytest.raises(AuthenticationError, match="Invalid code received from callback"):
            await session_manager.create_session("+1234567890", mock_callback)

    @pytest.mark.asyncio
    async def test_create_session_with_sync_callback(self, session_manager):
        """Test that synchronous callback works."""
        def sync_callback(phone):
            return "123456"

        session_data = await session_manager.create_session("+1234567890", sync_callback)
        assert session_data["phone"] == "+1234567890"

    @pytest.mark.asyncio
    async def test_create_session_with_rpc_client_success(self, session_manager, mock_rpc_client):
        """Test session creation with successful RPC authentication."""
        phone_number = "+1234567890"

        async def mock_callback(phone):
            return "123456"

        # Mock successful RPC responses
        mock_rpc_client.call.side_effect = [
            {"status": "ok"},  # auth.send_code response
            {"user_id": 123456789, "auth_key": "real_auth_key"},  # auth.sign_in response
        ]

        session_data = await session_manager.create_session(phone_number, mock_callback, mock_rpc_client)

        assert session_data["user_id"] == 123456789
        assert session_data["auth_key"] == "real_auth_key"
        assert mock_rpc_client.call.call_count == 2

    @pytest.mark.asyncio
    async def test_create_session_with_rpc_error_falls_back_to_mock(self, session_manager, mock_rpc_client):
        """Test that RPC error falls back to mock authentication."""
        phone_number = "+1234567890"

        async def mock_callback(phone):
            return "123456"

        # Mock RPC failure
        mock_rpc_client.call.side_effect = Exception("RPC unavailable")

        # Should fall back to mock auth
        session_data = await session_manager.create_session(phone_number, mock_callback, mock_rpc_client)

        assert session_data["phone"] == phone_number
        assert "auth_key" in session_data

    @pytest.mark.asyncio
    async def test_create_session_with_invalid_code_from_rpc(self, session_manager, mock_rpc_client):
        """Test that invalid code from RPC raises AuthenticationError."""
        phone_number = "+1234567890"

        async def mock_callback(phone):
            return "wrong_code"

        # Mock successful send_code, failed sign_in
        mock_rpc_client.call.side_effect = [
            {"status": "ok"},
            {"error": {"message": "Invalid code"}},
        ]

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await session_manager.create_session(phone_number, mock_callback, mock_rpc_client)


# ============================================================================
# Session Saving Tests
# ============================================================================


class TestSaveSession:
    """Test session saving functionality."""

    @pytest.mark.asyncio
    async def test_save_session_creates_file(self, session_manager, sample_session_data):
        """Test that save_session creates a file."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        session_path = session_manager._get_session_path(session_name)
        assert session_path.exists()

    @pytest.mark.asyncio
    async def test_save_session_stores_correct_data(self, session_manager, sample_session_data):
        """Test that saved data matches input."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        with open(session_manager._get_session_path(session_name), "r") as f:
            loaded_data = json.load(f)

        assert loaded_data["phone"] == sample_session_data["phone"]
        assert loaded_data["user_id"] == sample_session_data["user_id"]
        assert loaded_data["auth_key"] == sample_session_data["auth_key"]

    @pytest.mark.asyncio
    async def test_save_session_creates_backup(self, session_manager, sample_session_data):
        """Test that save_session creates backup on second save."""
        session_name = "test_session"

        # First save
        await session_manager.save_session(session_name, sample_session_data)

        # Modify and save again
        sample_session_data["user_id"] = 999999999
        await session_manager.save_session(session_name, sample_session_data)

        # Check backup exists
        backup_path = session_manager.session_dir / f"{session_name}.json.bak"
        assert backup_path.exists()

    @pytest.mark.asyncio
    async def test_save_session_adds_timestamps(self, session_manager):
        """Test that save_session adds timestamps."""
        session_name = "test_session"
        session_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
            "auth_key": "test_key",
        }

        await session_manager.save_session(session_name, session_data)

        loaded = await session_manager.load_session(session_name)
        assert "created_at" in loaded
        assert "last_used" in loaded

    @pytest.mark.asyncio
    async def test_save_session_with_empty_name_raises_error(self, session_manager, sample_session_data):
        """Test that empty session_name raises ValueError."""
        with pytest.raises(ValueError, match="session_name cannot be empty"):
            await session_manager.save_session("", sample_session_data)

    @pytest.mark.asyncio
    async def test_save_session_with_empty_data_raises_error(self, session_manager):
        """Test that empty session_data raises ValueError."""
        with pytest.raises(ValueError, match="session_data cannot be empty"):
            await session_manager.save_session("test", {})

    @pytest.mark.asyncio
    async def test_save_session_with_invalid_data_raises_error(self, session_manager):
        """Test that invalid session data raises AyuGramError."""
        invalid_data = {"phone": "+1234567890"}  # Missing user_id and auth_key

        with pytest.raises(AyuGramError, match="missing required field"):
            await session_manager.save_session("test", invalid_data)

    @pytest.mark.asyncio
    async def test_save_session_updates_cache(self, session_manager, sample_session_data):
        """Test that save_session updates in-memory cache."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        assert session_name in session_manager._session_cache
        assert session_manager._session_cache[session_name]["phone"] == sample_session_data["phone"]


# ============================================================================
# Session Loading Tests
# ============================================================================


class TestLoadSession:
    """Test session loading functionality."""

    @pytest.mark.asyncio
    async def test_load_session_from_file(self, session_manager, sample_session_data):
        """Test loading session from file."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        loaded = await session_manager.load_session(session_name)

        assert loaded["phone"] == sample_session_data["phone"]
        assert loaded["user_id"] == sample_session_data["user_id"]
        assert loaded["auth_key"] == sample_session_data["auth_key"]

    @pytest.mark.asyncio
    async def test_load_session_from_cache(self, session_manager, sample_session_data):
        """Test loading session from in-memory cache."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        # Load first time (from file)
        loaded1 = await session_manager.load_session(session_name)

        # Load second time (from cache)
        loaded2 = await session_manager.load_session(session_name)

        assert loaded1["phone"] == loaded2["phone"]

    @pytest.mark.asyncio
    async def test_load_session_updates_last_used(self, session_manager):
        """Test that load_session updates last_used timestamp."""
        session_name = "test_session"

        # Create session with specific initial timestamp
        session_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
            "auth_key": "test_key",
            "created_at": "2025-01-25T10:00:00Z",
            "last_used": "2025-01-25T10:00:00Z",
        }

        # Manually write to file to avoid timestamp updates from save_session
        import json
        session_path = session_manager._get_session_path(session_name)
        session_manager._ensure_session_directory()
        with open(session_path, "w") as f:
            json.dump(session_data, f)

        # Load session (should update last_used)
        loaded = await session_manager.load_session(session_name)

        # Check cache has updated timestamp
        assert session_manager._session_cache[session_name]["last_used"] != "2025-01-25T10:00:00Z"

    @pytest.mark.asyncio
    async def test_load_session_with_empty_name_raises_error(self, session_manager):
        """Test that empty session_name raises ValueError."""
        with pytest.raises(ValueError, match="session_name cannot be empty"):
            await session_manager.load_session("")

    @pytest.mark.asyncio
    async def test_load_nonexistent_session_raises_error(self, session_manager):
        """Test that loading nonexistent session raises AyuGramError."""
        with pytest.raises(AyuGramError, match="Session file not found"):
            await session_manager.load_session("nonexistent")

    @pytest.mark.asyncio
    async def test_load_session_with_corrupted_json_restores_from_backup(self, session_manager, sample_session_data):
        """Test that corrupted main file is restored from backup."""
        session_name = "test_session"

        # Create initial session and backup
        await session_manager.save_session(session_name, sample_session_data)

        # Corrupt the main file
        session_path = session_manager._get_session_path(session_name)
        with open(session_path, "w") as f:
            f.write("corrupted json data")

        # Should restore from backup
        loaded = await session_manager.load_session(session_name)

        assert loaded["phone"] == sample_session_data["phone"]

    @pytest.mark.asyncio
    async def test_load_session_with_corrupted_json_no_backup_raises_error(self, session_manager):
        """Test that corrupted file without backup raises error."""
        session_name = "test_session"

        # Create corrupted file
        session_path = session_manager._get_session_path(session_name)
        with open(session_path, "w") as f:
            f.write("corrupted json data")

        with pytest.raises(AyuGramError, match="Corrupted session file"):
            await session_manager.load_session(session_name)

    @pytest.mark.asyncio
    async def test_load_session_with_missing_backup_from_main(self, session_manager, sample_session_data):
        """Test that missing main file can be restored from backup."""
        session_name = "test_session"

        # Create initial session
        await session_manager.save_session(session_name, sample_session_data)

        # Save again to create backup
        sample_session_data_copy = sample_session_data.copy()
        await session_manager.save_session(session_name, sample_session_data_copy)

        backup_path = session_manager.session_dir / f"{session_name}.json.bak"
        session_path = session_manager._get_session_path(session_name)

        assert backup_path.exists(), "Backup should exist"
        assert session_path.exists(), "Main file should exist initially"

        # Delete main file
        session_path.unlink()
        assert not session_path.exists(), "Main file should be deleted"

        # Verify backup still exists and can be loaded
        assert backup_path.exists(), "Backup should still exist after deleting main file"

        # Should load from backup successfully
        loaded = await session_manager.load_session(session_name)
        assert loaded["phone"] == sample_session_data["phone"]
        assert loaded["user_id"] == sample_session_data["user_id"]

        # Verify the session is now in cache
        assert session_name in session_manager._session_cache


# ============================================================================
# Session Deletion Tests
# ============================================================================


class TestDeleteSession:
    """Test session deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_session_removes_file(self, session_manager, sample_session_data):
        """Test that delete_session removes the file."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        result = await session_manager.delete_session(session_name)

        assert result is True
        assert not session_manager._get_session_path(session_name).exists()

    @pytest.mark.asyncio
    async def test_delete_session_removes_backup(self, session_manager, sample_session_data):
        """Test that delete_session also removes backup."""
        session_name = "test_session"

        # Create session with backup
        await session_manager.save_session(session_name, sample_session_data)
        # Save again to create backup
        await session_manager.save_session(session_name, sample_session_data)

        backup_path = session_manager.session_dir / f"{session_name}.json.bak"
        assert backup_path.exists()

        await session_manager.delete_session(session_name)

        assert not backup_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_false(self, session_manager):
        """Test that deleting nonexistent session returns False."""
        result = await session_manager.delete_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_clears_cache(self, session_manager, sample_session_data):
        """Test that delete_session clears in-memory cache."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        # Load into cache
        await session_manager.load_session(session_name)
        assert session_name in session_manager._session_cache

        # Delete should clear cache
        await session_manager.delete_session(session_name)
        assert session_name not in session_manager._session_cache

    @pytest.mark.asyncio
    async def test_delete_session_with_empty_name_raises_error(self, session_manager):
        """Test that empty session_name raises ValueError."""
        with pytest.raises(ValueError, match="session_name cannot be empty"):
            await session_manager.delete_session("")


# ============================================================================
# Session Listing Tests
# ============================================================================


class TestListSessions:
    """Test session listing functionality."""

    @pytest.mark.asyncio
    async def test_list_sessions_returns_empty_list_when_empty(self, session_manager):
        """Test listing sessions when directory is empty."""
        sessions = session_manager.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_returns_session_names(self, session_manager, sample_session_data):
        """Test listing sessions returns correct names."""
        await session_manager.save_session("session1", sample_session_data)
        await session_manager.save_session("session2", sample_session_data)
        await session_manager.save_session("session3", sample_session_data)

        sessions = session_manager.list_sessions()

        assert len(sessions) == 3
        assert "session1" in sessions
        assert "session2" in sessions
        assert "session3" in sessions

    @pytest.mark.asyncio
    async def test_list_sessions_excludes_backups(self, session_manager, sample_session_data):
        """Test that backup files are not listed."""
        await session_manager.save_session("session1", sample_session_data)
        await session_manager.save_session("session1", sample_session_data)  # Create backup

        sessions = session_manager.list_sessions()

        assert len(sessions) == 1
        assert "session1" in sessions

    @pytest.mark.asyncio
    async def test_list_sessions_with_nonexistent_directory(self, temp_session_dir):
        """Test listing sessions when directory doesn't exist."""
        manager = SessionManager(os.path.join(temp_session_dir, "nonexistent"))
        sessions = manager.list_sessions()
        assert sessions == []


# ============================================================================
# Session Existence Tests
# ============================================================================


class TestSessionExists:
    """Test session existence checking."""

    @pytest.mark.asyncio
    async def test_session_exists_returns_true_for_existing(self, session_manager, sample_session_data):
        """Test that existing session returns True."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        result = await session_manager.session_exists(session_name)
        assert result is True

    @pytest.mark.asyncio
    async def test_session_exists_returns_false_for_nonexistent(self, session_manager):
        """Test that nonexistent session returns False."""
        result = await session_manager.session_exists("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_session_exists_checks_cache_first(self, session_manager, sample_session_data):
        """Test that session_exists checks in-memory cache."""
        session_name = "test_session"

        # Add to cache without saving
        session_manager._session_cache[session_name] = sample_session_data

        result = await session_manager.session_exists(session_name)
        assert result is True

    @pytest.mark.asyncio
    async def test_session_exists_with_empty_name_returns_false(self, session_manager):
        """Test that empty session_name returns False."""
        result = await session_manager.session_exists("")
        assert result is False


# ============================================================================
# Cache Management Tests
# ============================================================================


class TestCacheManagement:
    """Test in-memory cache management."""

    @pytest.mark.asyncio
    async def test_clear_cache_clears_memory_cache(self, session_manager, sample_session_data):
        """Test that clear_cache clears in-memory cache."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        # Load into cache
        await session_manager.load_session(session_name)
        assert session_name in session_manager._session_cache

        # Clear cache
        session_manager.clear_cache()
        assert session_name not in session_manager._session_cache

    @pytest.mark.asyncio
    async def test_clear_cache_does_not_delete_files(self, session_manager, sample_session_data):
        """Test that clear_cache doesn't delete session files."""
        session_name = "test_session"
        await session_manager.save_session(session_name, sample_session_data)

        session_manager.clear_cache()

        # File should still exist
        assert session_manager._get_session_path(session_name).exists()


# ============================================================================
# Redis Caching Tests
# ============================================================================


class TestRedisCaching:
    """Test Redis caching functionality."""

    @pytest.mark.asyncio
    async def test_redis_key_generation(self, session_manager):
        """Test Redis key generation."""
        key = session_manager._get_redis_key("test_session")
        assert key == "ayugram:session:test_session"

    @pytest.mark.asyncio
    async def test_cache_session_redis_when_disabled(self, session_manager, sample_session_data):
        """Test that Redis caching is skipped when disabled."""
        # Should not raise even though Redis is not available
        await session_manager._cache_session_redis("test", sample_session_data)

    @pytest.mark.asyncio
    async def test_get_cached_session_redis_when_disabled(self, session_manager):
        """Test that Redis get returns None when disabled."""
        result = await session_manager._get_cached_session_redis("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_session_redis_when_disabled(self, session_manager):
        """Test that Redis invalidation is skipped when disabled."""
        # Should not raise even though Redis is not available
        await session_manager._invalidate_session_redis("test")

    @pytest.mark.asyncio
    async def test_close_redis_when_disabled(self, session_manager):
        """Test that close_redis is safe when disabled."""
        # Should not raise
        await session_manager.close_redis()


# ============================================================================
# Session Validation Tests
# ============================================================================


class TestSessionValidation:
    """Test session data validation."""

    def test_validate_valid_session_data(self, session_manager, sample_session_data):
        """Test validation of valid session data."""
        session_manager._validate_session_data(sample_session_data, "test")  # Should not raise

    def test_validate_missing_phone_raises_error(self, session_manager):
        """Test that missing phone field raises error."""
        invalid_data = {
            "user_id": 123456789,
            "auth_key": "test_key",
        }
        with pytest.raises(AyuGramError, match="missing required field 'phone'"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_missing_user_id_raises_error(self, session_manager):
        """Test that missing user_id field raises error."""
        invalid_data = {
            "phone": "+1234567890",
            "auth_key": "test_key",
        }
        with pytest.raises(AyuGramError, match="missing required field 'user_id'"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_missing_auth_key_raises_error(self, session_manager):
        """Test that missing auth_key field raises error."""
        invalid_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
        }
        with pytest.raises(AyuGramError, match="missing required field 'auth_key'"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_invalid_phone_type_raises_error(self, session_manager):
        """Test that non-string phone raises error."""
        invalid_data = {
            "phone": 1234567890,  # Should be string
            "user_id": 123456789,
            "auth_key": "test_key",
        }
        with pytest.raises(AyuGramError, match="'phone' must be a non-empty string"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_empty_phone_raises_error(self, session_manager):
        """Test that empty phone string raises error."""
        invalid_data = {
            "phone": "",
            "user_id": 123456789,
            "auth_key": "test_key",
        }
        with pytest.raises(AyuGramError, match="'phone' must be a non-empty string"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_invalid_user_id_type_raises_error(self, session_manager):
        """Test that non-integer user_id raises error."""
        invalid_data = {
            "phone": "+1234567890",
            "user_id": "123456789",  # Should be int
            "auth_key": "test_key",
        }
        with pytest.raises(AyuGramError, match="'user_id' must be an integer"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_invalid_auth_key_type_raises_error(self, session_manager):
        """Test that non-string auth_key raises error."""
        invalid_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
            "auth_key": 12345,  # Should be string
        }
        with pytest.raises(AyuGramError, match="'auth_key' must be a non-empty string"):
            session_manager._validate_session_data(invalid_data, "test")

    def test_validate_empty_auth_key_raises_error(self, session_manager):
        """Test that empty auth_key string raises error."""
        invalid_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
            "auth_key": "",
        }
        with pytest.raises(AyuGramError, match="'auth_key' must be a non-empty string"):
            session_manager._validate_session_data(invalid_data, "test")


# ============================================================================
# Integration Tests
# ============================================================================


class TestSessionIntegration:
    """Integration tests for complete session workflows."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, session_manager):
        """Test complete session lifecycle: create -> save -> load -> delete."""
        phone_number = "+1234567890"

        # Create session (mock auth)
        async def mock_callback(phone):
            return "123456"

        session_data = await session_manager.create_session(phone_number, mock_callback)

        # Save session
        session_name = "test_account"
        await session_manager.save_session(session_name, session_data)

        # Load session
        loaded = await session_manager.load_session(session_name)
        assert loaded["phone"] == phone_number

        # Check exists
        assert await session_manager.session_exists(session_name) is True

        # Delete session
        result = await session_manager.delete_session(session_name)
        assert result is True

        # Verify deleted
        assert await session_manager.session_exists(session_name) is False

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, session_manager, sample_session_data):
        """Test that multiple sessions are managed independently."""
        await session_manager.save_session("account1", sample_session_data)
        await session_manager.save_session("account2", sample_session_data)
        await session_manager.save_session("account3", sample_session_data)

        sessions = session_manager.list_sessions()
        assert len(sessions) == 3

        # Delete one
        await session_manager.delete_session("account2")

        # Others should still exist
        sessions = session_manager.list_sessions()
        assert len(sessions) == 2
        assert "account1" in sessions
        assert "account3" in sessions
        assert "account2" not in sessions

    @pytest.mark.asyncio
    async def test_session_update_workflow(self, session_manager):
        """Test updating an existing session."""
        session_name = "test_session"

        # Create initial session
        session_data = {
            "phone": "+1234567890",
            "user_id": 111111111,
            "auth_key": "initial_key",
        }
        await session_manager.save_session(session_name, session_data)

        # Load and verify
        loaded = await session_manager.load_session(session_name)
        assert loaded["user_id"] == 111111111

        # Update session data
        session_data["user_id"] = 999999999
        session_data["auth_key"] = "updated_key"
        await session_manager.save_session(session_name, session_data)

        # Load updated version
        updated = await session_manager.load_session(session_name)
        assert updated["user_id"] == 999999999
        assert updated["auth_key"] == "updated_key"

        # Verify backup exists with old data
        backup_path = session_manager.session_dir / f"{session_name}.json.bak"
        assert backup_path.exists()

        with open(backup_path, "r") as f:
            backup_data = json.load(f)
        assert backup_data["user_id"] == 111111111
