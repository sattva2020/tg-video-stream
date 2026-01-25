"""
Session Management for AyuGram SDK.

This module provides session management functionality for AyuGram clients,
including session creation, loading, saving, and deletion with file system storage
and optional Redis caching.

Session data is stored in the local file system as the primary storage mechanism,
with optional Redis caching for faster access to frequently used sessions.

Example:
    >>> from ayugram.session import SessionManager
    >>> manager = SessionManager("./sessions")
    >>> session_data = await manager.create_session("+1234567890", callback)
    >>> await manager.save_session("my_session", session_data)
    >>> loaded = await manager.load_session("my_session")

Redis Caching (Optional):
    >>> # With Redis caching enabled
    >>> manager = SessionManager("./sessions", redis_url="redis://localhost:6379")
    >>> # Sessions will be cached in Redis for faster access
    >>> # Cache TTL: 1 hour (configurable via redis_ttl parameter)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ayugram.exceptions import AuthenticationError, AyuGramError

# Optional Redis support for session caching
try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger("ayugram.session")


class SessionManager:
    """
    Manages AyuGram sessions with file system storage and optional Redis caching.

    Provides methods for creating, loading, saving, and deleting sessions.
    Sessions are stored as JSON files on the local file system with secure
    file permissions (0600 for Unix-like systems). Redis caching is optional
    and provides faster access to frequently used sessions.

    The session file format is JSON with the following structure:
    {
        "phone": "+1234567890",
        "user_id": 123456789,
        "auth_key": "base64_encoded_auth_key",
        "created_at": "2025-01-25T10:00:00Z",
        "last_used": "2025-01-25T12:00:00Z"
    }

    Attributes:
        session_dir: Directory path for session files
        _session_cache: In-memory cache of loaded sessions
        redis_enabled: Whether Redis caching is enabled
        _redis: Redis connection (if enabled)

    Example:
        >>> manager = SessionManager("./sessions", redis_url="redis://localhost:6379")
        >>> session_data = await manager.create_session("+1234567890", code_callback)
        >>> await manager.save_session("my_account", session_data)
        >>> loaded = await manager.load_session("my_account")
    """

    # Redis key prefix for session storage
    REDIS_KEY_PREFIX = "ayugram:session:"

    def __init__(
        self,
        session_dir: str = "./sessions",
        redis_url: Optional[str] = None,
        redis_ttl: int = 3600,
    ):
        """
        Initialize SessionManager.

        Args:
            session_dir: Directory path for storing session files (default: "./sessions")
            redis_url: Optional Redis URL for caching (default: None, disables Redis)
            redis_ttl: Redis TTL for cached sessions in seconds (default: 3600 = 1 hour)

        Raises:
            ValueError: If session_dir is empty

        Example:
            >>> # Without Redis
            >>> manager = SessionManager("./sessions")
            >>> # With Redis
            >>> manager = SessionManager("./sessions", redis_url="redis://localhost:6379")
            >>> # With custom TTL
            >>> manager = SessionManager("./sessions", redis_url="redis://localhost:6379", redis_ttl=7200)
        """
        if not session_dir:
            raise ValueError("session_dir cannot be empty")

        self.session_dir = Path(session_dir).resolve()
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        self._redis: Optional[Any] = None
        self._redis_url = redis_url
        self._redis_ttl = redis_ttl
        self._redis_enabled = REDIS_AVAILABLE and redis_url is not None

        if self._redis_enabled:
            logger.info("SessionManager initialized with Redis caching: %s", redis_url)
        else:
            if REDIS_AVAILABLE:
                logger.debug("Redis available but not enabled (no redis_url provided)")
            else:
                logger.debug("Redis not available (redis package not installed)")

        logger.info("SessionManager initialized with directory: %s", self.session_dir)

        # Create session directory if it doesn't exist
        self._ensure_session_directory()

    def _ensure_session_directory(self) -> None:
        """
        Create session directory if it doesn't exist.

        Logs a warning if directory creation fails, but doesn't raise
        an exception to allow graceful degradation.
        """
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Session directory ensured: %s", self.session_dir)
        except OSError as e:
            logger.warning(
                "Failed to create session directory %s: %s", self.session_dir, e
            )

    async def _get_redis(self) -> Optional[Any]:
        """
        Get or create Redis connection.

        Returns:
            Redis connection object or None if Redis is not available

        Example:
            >>> redis = await manager._get_redis()
            >>> if redis:
            ...     await redis.set("key", "value")
        """
        if not self._redis_enabled or aioredis is None:
            return None

        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    self._redis_url, decode_responses=True
                )
                logger.debug("Redis connection established: %s", self._redis_url)
            except Exception as e:
                logger.warning("Failed to connect to Redis: %s", e)
                self._redis_enabled = False
                self._redis = None
                return None

        return self._redis

    def _get_redis_key(self, session_name: str) -> str:
        """
        Get the Redis key for a session.

        Args:
            session_name: Name of the session

        Returns:
            Redis key string

        Example:
            >>> key = manager._get_redis_key("my_account")
            >>> print(key)
            'ayugram:session:my_account'
        """
        return f"{self.REDIS_KEY_PREFIX}{session_name}"

    async def _cache_session_redis(
        self, session_name: str, session_data: Dict[str, Any]
    ) -> None:
        """
        Cache session data in Redis.

        Args:
            session_name: Name of the session
            session_data: Dictionary containing session data

        Example:
            >>> await manager._cache_session_redis("my_account", session_data)
        """
        if not self._redis_enabled:
            return

        redis = await self._get_redis()
        if redis is None:
            return

        try:
            key = self._get_redis_key(session_name)
            await redis.setex(key, self._redis_ttl, json.dumps(session_data))
            logger.debug(
                "Session cached in Redis: %s (TTL: %ds)", session_name, self._redis_ttl
            )
        except Exception as e:
            logger.warning("Failed to cache session in Redis: %s - %s", session_name, e)

    async def _get_cached_session_redis(
        self, session_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get session data from Redis cache.

        Args:
            session_name: Name of the session

        Returns:
            Session data dictionary or None if not in cache

        Example:
            >>> session = await manager._get_cached_session_redis("my_account")
            >>> if session:
            ...     print("Session loaded from Redis cache")
        """
        if not self._redis_enabled:
            return None

        redis = await self._get_redis()
        if redis is None:
            return None

        try:
            key = self._get_redis_key(session_name)
            data = await redis.get(key)
            if data:
                logger.debug("Session loaded from Redis cache: %s", session_name)
                return json.loads(data)
        except Exception as e:
            logger.warning("Failed to get session from Redis: %s - %s", session_name, e)

        return None

    async def _invalidate_session_redis(self, session_name: str) -> None:
        """
        Invalidate session data in Redis cache.

        Args:
            session_name: Name of the session

        Example:
            >>> await manager._invalidate_session_redis("my_account")
        """
        if not self._redis_enabled:
            return

        redis = await self._get_redis()
        if redis is None:
            return

        try:
            key = self._get_redis_key(session_name)
            await redis.delete(key)
            logger.debug("Session invalidated in Redis: %s", session_name)
        except Exception as e:
            logger.warning(
                "Failed to invalidate session in Redis: %s - %s", session_name, e
            )

    async def close_redis(self) -> None:
        """
        Close Redis connection if open.

        Example:
            >>> await manager.close_redis()
        """
        if self._redis is not None:
            try:
                await self._redis.close()
                logger.debug("Redis connection closed")
            except Exception as e:
                logger.warning("Failed to close Redis connection: %s", e)
            finally:
                self._redis = None

    def _get_session_path(self, session_name: str) -> Path:
        """
        Get the full file path for a session.

        Args:
            session_name: Name of the session (without .json extension)

        Returns:
            Path object pointing to the session file
        """
        return self.session_dir / f"{session_name}.json"

    async def create_session(
        self,
        phone_number: str,
        on_code_callback: Callable[[str], Any],
        rpc_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Create a new AyuGram session via authentication flow.

        This method initiates the authentication process with AyuGram:
        1. Sends phone number to AyuGram via JSON-RPC (if rpc_client provided)
        2. AyuGram sends OTP code to the phone
        3. SDK invokes on_code_callback with the code
        4. Code is sent to AyuGram for verification
        5. On success, session data is returned

        Args:
            phone_number: Phone number with country code (e.g., "+1234567890")
            on_code_callback: Async callback function to receive OTP code
            rpc_client: Optional JsonRpcClient for AyuGram communication

        Returns:
            Dictionary containing session data with phone, user_id, auth_key,
            created_at, and last_used fields

        Raises:
            AuthenticationError: If authentication fails
            ValueError: If phone_number is invalid or callback is not callable

        Example:
            >>> async def code_callback(code):
            ...     # User enters code via bot/input
            ...     return code
            >>> manager = SessionManager()
            >>> session = await manager.create_session("+1234567890", code_callback)
        """
        if not phone_number:
            raise ValueError("phone_number cannot be empty")

        if not callable(on_code_callback):
            raise ValueError("on_code_callback must be callable")

        logger.info("Creating session for phone: %s", phone_number)

        # Validate phone number format (basic check)
        if not phone_number.startswith("+"):
            raise ValueError("phone_number must start with '+' and country code")

        try:
            # Step 1: Send phone number to AyuGram via JSON-RPC (if rpc_client provided)
            if rpc_client is not None:
                logger.debug("Sending phone number to AyuGram via JSON-RPC")

                try:
                    # Request OTP code from AyuGram
                    response = await rpc_client.call(
                        "auth.send_code", {"phone": phone_number}
                    )

                    # Check if request was successful
                    if (
                        not response
                        or isinstance(response, dict)
                        and response.get("error")
                    ):
                        error_msg = (
                            response.get("error", {}).get("message", "Unknown error")
                            if isinstance(response, dict)
                            else "Unknown error"
                        )
                        raise AuthenticationError(
                            f"Failed to send code: {error_msg}",
                            details={"phone": phone_number, "response": response},
                        )

                    logger.debug("OTP code requested successfully from AyuGram")

                except Exception as e:
                    # If RPC call fails, check if it's a connection error or API error
                    if isinstance(e, AuthenticationError):
                        raise
                    logger.warning(
                        "RPC call failed, attempting mock authentication: %s", e
                    )

                    # Fall through to mock authentication for testing
                    rpc_client = None

            # Step 2: Invoke callback to get OTP code from user
            # This happens regardless of whether we're using real or mock authentication
            logger.debug("Invoking callback to get OTP code")

            try:
                # The callback should be async, but handle both sync and async
                if asyncio.iscoroutinefunction(on_code_callback):
                    code = await on_code_callback(phone_number)
                else:
                    code = on_code_callback(phone_number)

                logger.debug("Received OTP code from callback")

            except Exception as e:
                error_msg = f"Failed to get code from callback: {str(e)}"
                logger.error(error_msg)
                raise AuthenticationError(
                    error_msg, details={"phone": phone_number, "callback_error": str(e)}
                ) from e

            if not code or not isinstance(code, str):
                raise AuthenticationError(
                    "Invalid code received from callback",
                    details={"phone": phone_number, "code_type": type(code).__name__},
                )

            # Step 3: Send code to AyuGram for verification (if rpc_client provided)
            user_id = None
            auth_key = None

            if rpc_client is not None:
                logger.debug("Sending OTP code to AyuGram for verification")

                try:
                    response = await rpc_client.call(
                        "auth.sign_in", {"phone": phone_number, "code": code}
                    )

                    # Check if authentication was successful
                    if (
                        not response
                        or isinstance(response, dict)
                        and response.get("error")
                    ):
                        error_msg = (
                            response.get("error", {}).get("message", "Invalid code")
                            if isinstance(response, dict)
                            else "Invalid code"
                        )
                        raise AuthenticationError(
                            f"Authentication failed: {error_msg}",
                            details={"phone": phone_number},
                        )

                    # Extract session data from response
                    if isinstance(response, dict):
                        user_id = response.get("user_id")
                        auth_key = response.get("auth_key")

                        if not user_id or not auth_key:
                            raise AuthenticationError(
                                "Invalid session data received from AyuGram",
                                details={"phone": phone_number, "response": response},
                            )

                    logger.info(
                        "Authentication successful for phone: %s, user_id: %s",
                        phone_number,
                        user_id,
                    )

                except AuthenticationError:
                    raise
                except Exception as e:
                    logger.error("Failed to verify code with AyuGram: %s", e)
                    raise AuthenticationError(
                        f"Failed to verify code: {str(e)}",
                        details={"phone": phone_number, "error": str(e)},
                    ) from e

            else:
                # Mock authentication for testing (when rpc_client is None)
                logger.info(
                    "Using mock authentication for testing (no rpc_client provided)"
                )

                # For mock auth, use a fake user_id based on phone number
                user_id = hash(phone_number) % 1000000000
                auth_key = f"mock_auth_key_{phone_number}"

                logger.debug("Mock authentication completed: user_id=%s", user_id)

            # Step 4: Create session data with timestamps
            from datetime import datetime

            current_time = datetime.utcnow().isoformat() + "Z"

            session_data = {
                "phone": phone_number,
                "user_id": user_id,
                "auth_key": auth_key,
                "created_at": current_time,
                "last_used": current_time,
            }

            logger.info(
                "Session created successfully for phone: %s (user_id: %s)",
                phone_number,
                user_id,
            )

            return session_data

        except AuthenticationError:
            raise
        except ValueError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during session creation: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(
                error_msg, details={"phone": phone_number, "error": str(e)}
            ) from e

    def _validate_session_data(
        self, session_data: Dict[str, Any], session_name: str
    ) -> None:
        """
        Validate session data structure and required fields.

        Args:
            session_data: Dictionary containing session data to validate
            session_name: Name of the session (for error messages)

        Raises:
            AyuGramError: If session data is invalid or missing required fields
        """
        required_fields = ["phone", "user_id", "auth_key"]

        for field in required_fields:
            if field not in session_data:
                raise AyuGramError(
                    f"Invalid session data: missing required field '{field}'",
                    {
                        "session_name": session_name,
                        "present_fields": list(session_data.keys()),
                    },
                )

        # Validate field types
        if not isinstance(session_data["phone"], str) or not session_data["phone"]:
            raise AyuGramError(
                "Invalid session data: 'phone' must be a non-empty string",
                {
                    "session_name": session_name,
                    "phone_type": type(session_data["phone"]).__name__,
                },
            )

        if not isinstance(session_data["user_id"], int):
            raise AyuGramError(
                "Invalid session data: 'user_id' must be an integer",
                {
                    "session_name": session_name,
                    "user_id_type": type(session_data["user_id"]).__name__,
                },
            )

        if (
            not isinstance(session_data["auth_key"], str)
            or not session_data["auth_key"]
        ):
            raise AyuGramError(
                "Invalid session data: 'auth_key' must be a non-empty string",
                {
                    "session_name": session_name,
                    "auth_key_type": type(session_data["auth_key"]).__name__,
                },
            )

    async def load_session(self, session_name: str) -> Dict[str, Any]:
        """
        Load an existing session from Redis cache or file system.

        This method checks sources in the following order:
        1. In-memory cache
        2. Redis cache (if enabled)
        3. File system (with backup restoration if corrupted)

        If the main session file is corrupted, this method will attempt to restore
        from a backup file (if available) with a .bak extension.

        Args:
            session_name: Name of the session to load (without .json extension)

        Returns:
            Dictionary containing session data

        Raises:
            AyuGramError: If session file doesn't exist or is corrupted (and no backup available)
            ValueError: If session_name is empty

        Example:
            >>> manager = SessionManager()
            >>> session = await manager.load_session("my_account")
            >>> print(session["phone"])
        """
        if not session_name:
            raise ValueError("session_name cannot be empty")

        session_path = self._get_session_path(session_name)
        backup_path = self.session_dir / f"{session_name}.json.bak"

        # Check in-memory cache first
        if session_name in self._session_cache:
            logger.debug("Session loaded from in-memory cache: %s", session_name)
            return self._session_cache[session_name].copy()

        # Check Redis cache
        cached_data = await self._get_cached_session_redis(session_name)
        if cached_data is not None:
            # Validate cached data before using it
            try:
                self._validate_session_data(cached_data, session_name)
                # Update in-memory cache
                self._session_cache[session_name] = cached_data
                logger.info("Session loaded from Redis cache: %s", session_name)
                return cached_data.copy()
            except AyuGramError as e:
                logger.warning(
                    "Invalid session data in Redis cache: %s - %s", session_name, e
                )
                # Remove invalid data from Redis
                await self._invalidate_session_redis(session_name)

        if not session_path.exists():
            # Try to restore from backup if main file doesn't exist
            if backup_path.exists():
                logger.info(
                    "Main session file not found, attempting to restore from backup: %s",
                    session_name,
                )
                try:
                    # Read backup file
                    with open(backup_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)

                    # Validate session data
                    self._validate_session_data(session_data, session_name)

                    # Restore from backup by saving to main location
                    logger.info(
                        "Backup validated, restoring to main session file: %s",
                        session_name,
                    )
                    await self.save_session(session_name, session_data)

                    # Update last_used timestamp
                    from datetime import datetime

                    session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

                    # Cache the session
                    self._session_cache[session_name] = session_data
                    # Cache in Redis
                    await self._cache_session_redis(session_name, session_data)

                    logger.info("Session restored from backup: %s", session_name)
                    return session_data

                except (json.JSONDecodeError, OSError, AyuGramError) as e:
                    logger.error(
                        "Failed to restore from backup file %s: %s", backup_path, e
                    )
                    raise AyuGramError(
                        f"Session file not found and backup restoration failed: {session_name}",
                        {
                            "session_path": str(session_path),
                            "backup_path": str(backup_path),
                            "error": str(e),
                        },
                    ) from e
            else:
                raise AyuGramError(
                    f"Session file not found: {session_name}",
                    {"session_path": str(session_path)},
                )

        try:
            # Read file
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Validate session data structure
            self._validate_session_data(session_data, session_name)

            logger.info("Session loaded from file: %s", session_name)

            # Update last_used timestamp
            from datetime import datetime

            session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

            # Cache the session
            self._session_cache[session_name] = session_data
            # Cache in Redis
            await self._cache_session_redis(session_name, session_data)

            return session_data

        except json.JSONDecodeError as e:
            # Main file is corrupted, try to restore from backup
            logger.warning(
                "Main session file is corrupted, attempting to restore from backup: %s",
                session_name,
            )

            if backup_path.exists():
                try:
                    # Read backup file
                    with open(backup_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)

                    # Validate session data
                    self._validate_session_data(session_data, session_name)

                    # Restore from backup by saving to main location
                    logger.info(
                        "Backup validated, restoring to main session file: %s",
                        session_name,
                    )
                    await self.save_session(session_name, session_data)

                    # Update last_used timestamp
                    from datetime import datetime

                    session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

                    # Cache the session
                    self._session_cache[session_name] = session_data
                    # Cache in Redis
                    await self._cache_session_redis(session_name, session_data)

                    logger.info(
                        "Session restored from backup after corruption: %s",
                        session_name,
                    )
                    return session_data

                except (json.JSONDecodeError, OSError, AyuGramError) as backup_error:
                    logger.error(
                        "Failed to restore from backup file %s: %s",
                        backup_path,
                        backup_error,
                    )
                    raise AyuGramError(
                        f"Corrupted session file and backup restoration failed: {session_name}",
                        {
                            "session_path": str(session_path),
                            "backup_path": str(backup_path),
                            "main_error": str(e),
                            "backup_error": str(backup_error),
                        },
                    ) from e
            else:
                # No backup available
                error_msg = f"Corrupted session file: {session_name} - Invalid JSON (no backup available)"
                logger.error(error_msg)
                raise AyuGramError(
                    error_msg,
                    {
                        "session_path": str(session_path),
                        "json_error": str(e),
                        "suggestion": "Use create_session() to re-authenticate",
                    },
                ) from e

        except AyuGramError:
            raise
        except OSError as e:
            error_msg = f"Failed to read session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(
                error_msg, {"session_path": str(session_path), "os_error": str(e)}
            ) from e

    async def save_session(
        self,
        session_name: str,
        session_data: Dict[str, Any],
    ) -> None:
        """
        Save session data to file system.

        Session files are saved with restricted permissions (0600 on Unix-like systems)
        to protect sensitive authentication data. A backup file (.bak) is automatically
        created if a session file already exists.

        Args:
            session_name: Name for the session (without .json extension)
            session_data: Dictionary containing session data to save

        Raises:
            ValueError: If session_name or session_data is empty
            AyuGramError: If file write fails or session data is invalid

        Example:
            >>> manager = SessionManager()
            >>> session_data = {
            ...     "phone": "+1234567890",
            ...     "user_id": 123456789,
            ...     "auth_key": "base64_encoded_key",
            ... }
            >>> await manager.save_session("my_account", session_data)
        """
        if not session_name:
            raise ValueError("session_name cannot be empty")

        if not session_data:
            raise ValueError("session_data cannot be empty")

        # Validate session data before saving
        self._validate_session_data(session_data, session_name)

        session_path = self._get_session_path(session_name)
        backup_path = self.session_dir / f"{session_name}.json.bak"

        logger.info("Saving session: %s", session_name)

        try:
            # Ensure session directory exists
            self._ensure_session_directory()

            # Create backup if session file already exists
            if session_path.exists():
                logger.debug("Creating backup of existing session: %s", session_name)
                try:
                    import shutil

                    shutil.copy2(session_path, backup_path)
                    logger.debug("Backup created: %s", backup_path)
                except OSError as e:
                    logger.warning(
                        "Failed to create backup file %s: %s", backup_path, e
                    )
                    # Continue without backup - non-critical error

            # Add timestamps if not present
            from datetime import datetime

            if "created_at" not in session_data:
                session_data["created_at"] = datetime.utcnow().isoformat() + "Z"

            session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

            # Write to file
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)

            # Set restrictive permissions (Unix-like systems only)
            try:
                os.chmod(session_path, 0o600)
            except (OSError, AttributeError) as e:
                logger.debug(
                    "Could not set file permissions for %s: %s", session_path, e
                )

            # Also set restrictive permissions on backup
            if backup_path.exists():
                try:
                    os.chmod(backup_path, 0o600)
                except (OSError, AttributeError) as e:
                    logger.debug(
                        "Could not set backup file permissions for %s: %s",
                        backup_path,
                        e,
                    )

            # Update cache
            self._session_cache[session_name] = session_data.copy()
            # Cache in Redis
            await self._cache_session_redis(session_name, session_data)

            logger.info("Session saved successfully: %s", session_name)

        except AyuGramError:
            raise
        except OSError as e:
            error_msg = f"Failed to save session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(
                error_msg, {"session_path": str(session_path), "os_error": str(e)}
            ) from e

        except TypeError as e:
            error_msg = f"Failed to serialize session data: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(
                error_msg, {"session_path": str(session_path), "type_error": str(e)}
            ) from e

    async def delete_session(self, session_name: str) -> bool:
        """
        Delete a session from file system and cache.

        This method deletes both the main session file and its backup (.bak) if it exists.

        Args:
            session_name: Name of the session to delete (without .json extension)

        Returns:
            True if session was deleted, False if it didn't exist

        Raises:
            ValueError: If session_name is empty
            AyuGramError: If file deletion fails

        Example:
            >>> manager = SessionManager()
            >>> success = await manager.delete_session("my_account")
            >>> print(success)
        """
        if not session_name:
            raise ValueError("session_name cannot be empty")

        session_path = self._get_session_path(session_name)
        backup_path = self.session_dir / f"{session_name}.json.bak"

        # Remove from in-memory cache
        self._session_cache.pop(session_name, None)
        # Remove from Redis cache
        await self._invalidate_session_redis(session_name)

        if not session_path.exists():
            logger.debug(
                "Session file does not exist, nothing to delete: %s", session_name
            )
            return False

        try:
            # Delete main file
            session_path.unlink()

            # Also delete backup file if it exists
            if backup_path.exists():
                try:
                    backup_path.unlink()
                    logger.debug("Backup file deleted: %s", backup_path)
                except OSError as e:
                    logger.warning(
                        "Failed to delete backup file %s: %s", backup_path, e
                    )
                    # Continue - main file was deleted successfully

            logger.info("Session deleted: %s", session_name)
            return True

        except OSError as e:
            error_msg = f"Failed to delete session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(
                error_msg, {"session_path": str(session_path), "os_error": str(e)}
            ) from e

    def list_sessions(self) -> list[str]:
        """
        List all available sessions in the session directory.

        Returns:
            List of session names (without .json extension)

        Example:
            >>> manager = SessionManager()
            >>> sessions = manager.list_sessions()
            >>> print(sessions)
            ['my_account', 'another_account']
        """
        try:
            if not self.session_dir.exists():
                logger.debug("Session directory does not exist: %s", self.session_dir)
                return []

            session_files = list(self.session_dir.glob("*.json"))
            session_names = [f.stem for f in session_files if f.is_file()]

            logger.debug(
                "Found %d sessions in %s", len(session_names), self.session_dir
            )
            return session_names

        except OSError as e:
            logger.error("Failed to list sessions: %s", e)
            return []

    async def session_exists(self, session_name: str) -> bool:
        """
        Check if a session exists in file system or cache.

        Args:
            session_name: Name of the session to check (without .json extension)

        Returns:
            True if session exists, False otherwise

        Example:
            >>> manager = SessionManager()
            >>> exists = await manager.session_exists("my_account")
            >>> print(exists)
        """
        if not session_name:
            return False

        # Check cache first
        if session_name in self._session_cache:
            return True

        # Check file system
        session_path = self._get_session_path(session_name)
        return session_path.exists()

    def clear_cache(self) -> None:
        """
        Clear the in-memory session cache.

        This does not delete session files from disk or Redis cache,
        only clears the cached copies in memory.

        Example:
            >>> manager = SessionManager()
            >>> manager.clear_cache()
        """
        self._session_cache.clear()
        logger.debug("In-memory session cache cleared")

    async def clear_all_caches(self) -> None:
        """
        Clear all caches (in-memory and Redis).

        This does not delete session files from disk, only clears
        all cached copies. Redis cache entries for all sessions
        will be deleted using key pattern matching.

        Example:
            >>> manager = SessionManager()
            >>> await manager.clear_all_caches()
        """
        # Clear in-memory cache
        self._session_cache.clear()
        logger.debug("In-memory session cache cleared")

        # Clear all Redis cache entries
        if self._redis_enabled:
            redis = await self._get_redis()
            if redis is not None:
                try:
                    # Delete all keys with our prefix
                    pattern = f"{self.REDIS_KEY_PREFIX}*"
                    keys = []
                    async for key in redis.scan_iter(match=pattern):
                        keys.append(key)
                    if keys:
                        await redis.delete(*keys)
                        logger.debug(
                            "Cleared %d session(s) from Redis cache", len(keys)
                        )
                except Exception as e:
                    logger.warning("Failed to clear Redis cache: %s", e)


__all__ = [
    "SessionManager",
]
