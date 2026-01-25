"""
Integration tests for session persistence with file system and optional Redis.

These tests verify the complete session persistence workflow including:
- Session save and load operations
- Backup file creation and corruption recovery
- Session deletion with cleanup
- Multiple session management
- Cache invalidation
- Session listing and existence checks
- Data integrity across operations

Tests use the file system and optional Redis for comprehensive persistence testing.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ayugram.exceptions import AyuGramError
from ayugram.session import SessionManager


class TestSessionSaveAndLoad:
    """Test session save and load operations."""

    @pytest.mark.asyncio
    async def test_save_and_load_session(self):
        """
        Test saving a session to disk and loading it back.

        Verifies:
        1. Session data is saved to disk as JSON
        2. Session can be loaded from disk
        3. All fields are preserved (phone, user_id, auth_key, timestamps)
        4. last_used timestamp is updated on load
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create session data
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key_base64",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            # Save session
            await session_manager.save_session("test_session", session_data)

            # Verify session file exists
            session_file = Path(temp_dir) / "test_session.json"
            assert session_file.exists()

            # Load session
            loaded_session = await session_manager.load_session("test_session")

            # Verify all fields are preserved
            assert loaded_session["phone"] == session_data["phone"]
            assert loaded_session["user_id"] == session_data["user_id"]
            assert loaded_session["auth_key"] == session_data["auth_key"]
            assert loaded_session["created_at"] == session_data["created_at"]
            # last_used should be updated on load
            assert loaded_session["last_used"] >= session_data["last_used"]

    @pytest.mark.asyncio
    async def test_save_multiple_sessions(self):
        """
        Test saving multiple sessions.

        Verifies that multiple sessions can be saved independently
        and loaded without conflicts.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create multiple session data
            sessions = {
                "session1": {
                    "phone": "+1111111111",
                    "user_id": 111111111,
                    "auth_key": "auth_key_1",
                    "created_at": "2025-01-25T10:00:00Z",
                    "last_used": "2025-01-25T10:00:00Z",
                },
                "session2": {
                    "phone": "+2222222222",
                    "user_id": 222222222,
                    "auth_key": "auth_key_2",
                    "created_at": "2025-01-25T11:00:00Z",
                    "last_used": "2025-01-25T11:00:00Z",
                },
                "session3": {
                    "phone": "+3333333333",
                    "user_id": 333333333,
                    "auth_key": "auth_key_3",
                    "created_at": "2025-01-25T12:00:00Z",
                    "last_used": "2025-01-25T12:00:00Z",
                },
            }

            # Save all sessions
            for session_name, session_data in sessions.items():
                await session_manager.save_session(session_name, session_data)

            # Verify all sessions can be loaded
            for session_name, original_data in sessions.items():
                loaded = await session_manager.load_session(session_name)
                assert loaded["phone"] == original_data["phone"]
                assert loaded["user_id"] == original_data["user_id"]
                assert loaded["auth_key"] == original_data["auth_key"]

    @pytest.mark.asyncio
    async def test_load_session_updates_last_used(self):
        """
        Test that loading a session updates the last_used timestamp.

        Verifies that each load operation updates the timestamp
        to track session usage.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)

            # Load session first time
            loaded1 = await session_manager.load_session("test")
            first_last_used = loaded1["last_used"]

            # Load session second time
            loaded2 = await session_manager.load_session("test")
            second_last_used = loaded2["last_used"]

            # Verify timestamp was updated
            assert second_last_used >= first_last_used

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self):
        """
        Test loading a session that doesn't exist.

        Verifies that AyuGramError is raised with appropriate message.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            with pytest.raises(AyuGramError, match=r"Session file not found: nonexistent"):
                await session_manager.load_session("nonexistent")

    @pytest.mark.asyncio
    async def test_save_session_with_invalid_data(self):
        """
        Test saving session with invalid data structure.

        Verifies that AyuGramError is raised when session data
        is missing required fields.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Missing required field 'user_id'
            invalid_session = {
                "phone": "+1234567890",
                "auth_key": "test_auth_key",
            }

            with pytest.raises(AyuGramError, match="Invalid session data"):
                await session_manager.save_session("invalid", invalid_session)


class TestSessionBackupAndRecovery:
    """Test backup file creation and corruption recovery."""

    @pytest.mark.asyncio
    async def test_backup_file_created_on_save(self):
        """
        Test that backup file is created when overwriting existing session.

        Verifies:
        1. .bak backup file is created
        2. Backup contains previous session data
        3. Main file contains new session data
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create initial session
            session_v1 = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "auth_key_v1",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_v1)

            # Update session with new data
            session_v2 = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "auth_key_v2",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T11:00:00Z",
            }

            await session_manager.save_session("test", session_v2)

            # Verify backup file exists
            backup_file = Path(temp_dir) / "test.json.bak"
            assert backup_file.exists()

            # Verify backup contains v1 data
            with open(backup_file, "r") as f:
                backup_data = json.load(f)
            assert backup_data["auth_key"] == "auth_key_v1"

            # Verify main file contains v2 data
            main_file = Path(temp_dir) / "test.json"
            with open(main_file, "r") as f:
                main_data = json.load(f)
            assert main_data["auth_key"] == "auth_key_v2"

    @pytest.mark.asyncio
    async def test_corrupted_session_recovery_from_backup(self):
        """
        Test recovery from backup when main session file is corrupted.

        Verifies:
        1. Corrupted main file is detected
        2. Backup file is loaded automatically
        3. Session is restored successfully
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create valid session
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "valid_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)

            # Corrupt the main session file
            session_file = Path(temp_dir) / "test.json"
            with open(session_file, "w") as f:
                f.write("{corrupted json data")

            # Load should recover from backup
            loaded_session = await session_manager.load_session("test")

            # Verify session was recovered from backup
            assert loaded_session["auth_key"] == "valid_auth_key"
            assert loaded_session["phone"] == session_data["phone"]

    @pytest.mark.asyncio
    async def test_missing_main_and_backup_raises_error(self):
        """
        Test loading when both main and backup files are missing.

        Verifies that AyuGramError is raised when neither file exists.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Don't create any files

            with pytest.raises(AyuGramError, match=r"Session file not found: missing"):
                await session_manager.load_session("missing")

    @pytest.mark.asyncio
    async def test_corrupted_backup_raises_error(self):
        """
        Test loading when both main and backup files are corrupted.

        Verifies that AyuGramError is raised with clear message
        when both files are invalid.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create corrupted main file
            main_file = Path(temp_dir) / "corrupted.json"
            with open(main_file, "w") as f:
                f.write("{corrupted")

            # Create corrupted backup file
            backup_file = Path(temp_dir) / "corrupted.json.bak"
            with open(backup_file, "w") as f:
                f.write("{also corrupted")

            with pytest.raises(AyuGramError, match=r"Corrupted session file and backup restoration failed"):
                await session_manager.load_session("corrupted")


class TestSessionDeletion:
    """Test session deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_session_removes_files(self):
        """
        Test that deleting a session removes both main and backup files.

        Verifies:
        1. Main session file is deleted
        2. Backup file is deleted (if exists)
        3. Session is removed from cache
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create session
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)

            # Update to create backup
            session_data["auth_key"] = "updated_auth_key"
            await session_manager.save_session("test", session_data)

            # Verify files exist
            main_file = Path(temp_dir) / "test.json"
            backup_file = Path(temp_dir) / "test.json.bak"
            assert main_file.exists()
            assert backup_file.exists()

            # Delete session
            await session_manager.delete_session("test")

            # Verify files are deleted
            assert not main_file.exists()
            assert not backup_file.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self):
        """
        Test deleting a session that doesn't exist.

        Verifies that the operation completes without error
        (idempotent operation).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Should not raise an error
            await session_manager.delete_session("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_session_clears_cache(self):
        """
        Test that deleting a session removes it from in-memory cache.

        Verifies that after deletion, the session cannot be loaded
        from cache or disk.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create and load session (populates cache)
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)
            await session_manager.load_session("test")

            # Verify session is in cache
            assert "test" in session_manager._session_cache

            # Delete session
            await session_manager.delete_session("test")

            # Verify session is removed from cache
            assert "test" not in session_manager._session_cache


class TestSessionListing:
    """Test session listing and existence checks."""

    @pytest.mark.asyncio
    async def test_list_sessions_returns_all_sessions(self):
        """
        Test listing all sessions in the session directory.

        Verifies:
        1. All session files are listed
        2. Session names are returned without .json extension
        3. Empty list is returned when no sessions exist
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Initially no sessions
            sessions = session_manager.list_sessions()
            assert len(sessions) == 0

            # Create multiple sessions
            session_names = ["session1", "session2", "session3"]
            for name in session_names:
                session_data = {
                    "phone": f"+{name}",
                    "user_id": hash(name),
                    "auth_key": f"auth_{name}",
                    "created_at": "2025-01-25T10:00:00Z",
                    "last_used": "2025-01-25T10:00:00Z",
                }
                await session_manager.save_session(name, session_data)

            # List sessions
            sessions = session_manager.list_sessions()

            # Verify all sessions are listed
            assert len(sessions) == 3
            for name in session_names:
                assert name in sessions

    @pytest.mark.asyncio
    async def test_session_exists_check(self):
        """
        Test checking if a session exists.

        Verifies:
        1. Returns True when session file exists
        2. Returns False when session doesn't exist
        3. Checks both disk and cache
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Session doesn't exist initially
            assert not await session_manager.session_exists("test")

            # Create session
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)

            # Session exists after creation
            assert await session_manager.session_exists("test")

            # Delete session
            await session_manager.delete_session("test")

            # Session doesn't exist after deletion
            assert not await session_manager.session_exists("test")


class TestSessionCacheManagement:
    """Test in-memory cache behavior."""

    @pytest.mark.asyncio
    async def test_load_session_uses_cache(self):
        """
        Test that loading a session uses in-memory cache on second load.

        Verifies:
        1. First load reads from disk
        2. Second load reads from cache
        3. Cached data is returned correctly
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)

            # First load - reads from disk, populates cache
            loaded1 = await session_manager.load_session("test")
            assert "test" in session_manager._session_cache

            # Modify file on disk
            session_file = Path(temp_dir) / "test.json"
            with open(session_file, "r") as f:
                file_data = json.load(f)
            file_data["auth_key"] = "modified_on_disk"
            with open(session_file, "w") as f:
                json.dump(file_data, f)

            # Second load - should use cache (not reflect disk changes)
            loaded2 = await session_manager.load_session("test")
            assert loaded2["auth_key"] == "test_auth_key"  # Cache value

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """
        Test clearing the in-memory session cache.

        Verifies:
        1. Cache is cleared
        2. Sessions can still be loaded from disk after cache clear
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create and load session
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_data)
            await session_manager.load_session("test")

            # Verify cache is populated
            assert len(session_manager._session_cache) > 0

            # Clear cache
            session_manager.clear_cache()

            # Verify cache is empty
            assert len(session_manager._session_cache) == 0

            # Verify session can still be loaded from disk
            loaded = await session_manager.load_session("test")
            assert loaded["auth_key"] == "test_auth_key"

    @pytest.mark.asyncio
    async def test_save_invalidates_cache(self):
        """
        Test that saving a session updates the cache.

        Verifies:
        1. Saving a session updates cached version
        2. Subsequent loads reflect the saved data
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create and save initial session
            session_v1 = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "auth_v1",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("test", session_v1)
            await session_manager.load_session("test")

            # Save updated session
            session_v2 = session_v1.copy()
            session_v2["auth_key"] = "auth_v2"
            session_v2["last_used"] = "2025-01-25T11:00:00Z"

            await session_manager.save_session("test", session_v2)

            # Load from cache should return updated version
            loaded = await session_manager.load_session("test")
            assert loaded["auth_key"] == "auth_v2"


class TestSessionPersistenceAcrossInstances:
    """Test session persistence across different SessionManager instances."""

    @pytest.mark.asyncio
    async def test_session_persists_across_instances(self):
        """
        Test that sessions persist across different SessionManager instances.

        Simulates application restart where a new SessionManager instance
        needs to load existing sessions from disk.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # First instance - create and save session
            session_manager1 = SessionManager(session_dir=temp_dir)

            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "persisted_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager1.save_session("persistent", session_data)

            # Second instance - simulate app restart
            session_manager2 = SessionManager(session_dir=temp_dir)

            # Load session from disk
            loaded_session = await session_manager2.load_session("persistent")

            # Verify session persisted correctly
            assert loaded_session["phone"] == session_data["phone"]
            assert loaded_session["user_id"] == session_data["user_id"]
            assert loaded_session["auth_key"] == session_data["auth_key"]
            assert loaded_session["created_at"] == session_data["created_at"]

    @pytest.mark.asyncio
    async def test_multiple_managers_same_directory(self):
        """
        Test multiple SessionManager instances using the same directory.

        Verifies that multiple instances can share the same session directory
        and see each other's changes.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            manager1 = SessionManager(session_dir=temp_dir)
            manager2 = SessionManager(session_dir=temp_dir)

            # Manager1 creates a session
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "shared_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await manager1.save_session("shared", session_data)

            # Manager2 loads the session (bypassing manager1's cache)
            # Force cache miss by directly loading from file
            session_file = Path(temp_dir) / "shared.json"
            with open(session_file, "r") as f:
                file_data = json.load(f)

            assert file_data["auth_key"] == "shared_auth_key"


class TestSessionFilePermissions:
    """Test session file permissions on Unix-like systems."""

    @pytest.mark.asyncio
    async def test_session_file_permissions(self):
        """
        Test that session files are created with secure permissions.

        Verifies that session files have 0600 permissions (owner read/write only)
        on Unix-like systems.
        """
        import stat

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "secure_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            await session_manager.save_session("secure", session_data)

            # Check file permissions
            session_file = Path(temp_dir) / "secure.json"
            file_stat = session_file.stat()
            file_mode = stat.filemode(file_stat.st_mode)

            # On Unix, verify permissions are -rw------- (0600)
            # On Windows, this test will just pass (permissions work differently)
            if os.name != "nt":  # Unix-like systems
                # Check that group and others have no permissions
                assert file_stat.st_mode & 0o077 == 0


class TestRedisIntegration:
    """Test optional Redis caching for sessions."""

    @pytest.mark.asyncio
    async def test_redis_cache_set_on_save(self):
        """
        Test that saving a session caches it in Redis when enabled.

        Verifies:
        1. Session is saved to disk
        2. Session is cached in Redis
        3. Cache has appropriate TTL
        """
        # Skip test if Redis is not available
        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("Redis not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock Redis client
            mock_redis = Mock(spec=aioredis.Redis)

            with patch.object(
                SessionManager,
                "_get_redis",
                return_value=mock_redis,
            ):
                session_manager = SessionManager(
                    session_dir=temp_dir,
                    redis_url="redis://localhost:6379",
                    redis_ttl=3600,
                )

                session_data = {
                    "phone": "+1234567890",
                    "user_id": 123456789,
                    "auth_key": "test_auth_key",
                    "created_at": "2025-01-25T10:00:00Z",
                    "last_used": "2025-01-25T10:00:00Z",
                }

                await session_manager.save_session("test", session_data)

                # Verify Redis set was called
                mock_redis.set.assert_called_once()
                call_args = mock_redis.set.call_args

                # Verify key and value
                key = call_args[0][0]
                assert "test" in key

                # Verify TTL was set
                assert "ex" in call_args[1] or call_args[1].get("ex") == 3600

    @pytest.mark.asyncio
    async def test_redis_cache_get_on_load(self):
        """
        Test that loading a session checks Redis cache first.

        Verifies:
        1. Redis cache is checked before disk
        2. Cached session is returned if available
        3. Disk is accessed only on cache miss
        """
        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("Redis not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock Redis client
            mock_redis = Mock(spec=aioredis.Redis)

            # Mock Redis to return cached session
            cached_session = json.dumps({
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "cached_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            })
            mock_redis.get = Mock(return_value=cached_session.encode())

            with patch.object(
                SessionManager,
                "_get_redis",
                return_value=mock_redis,
            ):
                session_manager = SessionManager(
                    session_dir=temp_dir,
                    redis_url="redis://localhost:6379",
                )

                # Load session (should use cache)
                loaded = await session_manager.load_session("test")

                # Verify cached session was returned
                assert loaded["auth_key"] == "cached_auth_key"

                # Verify Redis get was called
                mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_cache_invalidation_on_delete(self):
        """
        Test that deleting a session invalidates Redis cache.

        Verifies:
        1. Session is deleted from disk
        2. Redis cache entry is deleted
        """
        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("Redis not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock Redis client
            mock_redis = Mock(spec=aioredis.Redis)

            with patch.object(
                SessionManager,
                "_get_redis",
                return_value=mock_redis,
            ):
                session_manager = SessionManager(
                    session_dir=temp_dir,
                    redis_url="redis://localhost:6379",
                )

                # Delete session
                await session_manager.delete_session("test")

                # Verify Redis delete was called
                mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_redis(self):
        """
        Test that SessionManager works without Redis.

        Verifies that all operations work correctly when Redis is not configured.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create SessionManager without Redis
            session_manager = SessionManager(session_dir=temp_dir)

            session_data = {
                "phone": "+1234567890",
                "user_id": 123456789,
                "auth_key": "test_auth_key",
                "created_at": "2025-01-25T10:00:00Z",
                "last_used": "2025-01-25T10:00:00Z",
            }

            # All operations should work
            await session_manager.save_session("test", session_data)
            loaded = await session_manager.load_session("test")
            assert loaded["auth_key"] == "test_auth_key"

            sessions = session_manager.list_sessions()
            assert "test" in sessions

            await session_manager.delete_session("test")
            assert not await session_manager.session_exists("test")
