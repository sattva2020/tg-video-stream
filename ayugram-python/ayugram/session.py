"""
Session Management for AyuGram SDK.

This module provides session management functionality for AyuGram clients,
including session creation, loading, saving, and deletion with file system storage.

Session data is stored in the local file system as the primary storage mechanism,
with optional Redis caching for faster access (added in subsequent subtasks).

Example:
    >>> from ayugram.session import SessionManager
    >>> manager = SessionManager("./sessions")
    >>> session_data = await manager.create_session("+1234567890", callback)
    >>> await manager.save_session("my_session", session_data)
    >>> loaded = await manager.load_session("my_session")
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ayugram.exceptions import AyuGramError, AuthenticationError

logger = logging.getLogger("ayugram.session")


class SessionManager:
    """
    Manages AyuGram sessions with file system storage.

    Provides methods for creating, loading, saving, and deleting sessions.
    Sessions are stored as JSON files on the local file system with secure
    file permissions (0600 for Unix-like systems).

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

    Example:
        >>> manager = SessionManager("./sessions")
        >>> session_data = await manager.create_session("+1234567890", code_callback)
        >>> await manager.save_session("my_account", session_data)
        >>> loaded = await manager.load_session("my_account")
    """

    def __init__(self, session_dir: str = "./sessions"):
        """
        Initialize SessionManager.

        Args:
            session_dir: Directory path for storing session files (default: "./sessions")

        Raises:
            ValueError: If session_dir is empty
        """
        if not session_dir:
            raise ValueError("session_dir cannot be empty")

        self.session_dir = Path(session_dir).resolve()
        self._session_cache: Dict[str, Dict[str, Any]] = {}
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
            logger.warning("Failed to create session directory %s: %s", self.session_dir, e)

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

        Note: This is a stub implementation. Full authentication flow
        will be implemented in subtask-4-2.

        Args:
            phone_number: Phone number with country code (e.g., "+1234567890")
            on_code_callback: Async callback function to receive OTP code
            rpc_client: Optional JsonRpcClient for AyuGram communication

        Returns:
            Dictionary containing session data

        Raises:
            AuthenticationError: If authentication fails
            ValueError: If phone_number is invalid

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

        # Stub implementation - will be completed in subtask-4-2
        # For now, return a minimal session structure
        session_data = {
            "phone": phone_number,
            "user_id": None,  # Will be populated after auth
            "auth_key": None,  # Will be populated after auth
            "created_at": None,  # Will be populated after auth
            "last_used": None,
        }

        logger.debug("Session created for phone: %s", phone_number)
        return session_data

    async def load_session(self, session_name: str) -> Dict[str, Any]:
        """
        Load an existing session from file system.

        Args:
            session_name: Name of the session to load (without .json extension)

        Returns:
            Dictionary containing session data

        Raises:
            AyuGramError: If session file doesn't exist or is corrupted
            ValueError: If session_name is empty

        Example:
            >>> manager = SessionManager()
            >>> session = await manager.load_session("my_account")
            >>> print(session["phone"])
        """
        if not session_name:
            raise ValueError("session_name cannot be empty")

        session_path = self._get_session_path(session_name)

        # Check cache first
        if session_name in self._session_cache:
            logger.debug("Session loaded from cache: %s", session_name)
            return self._session_cache[session_name].copy()

        if not session_path.exists():
            raise AyuGramError(
                f"Session file not found: {session_name}",
                {"session_path": str(session_path)},
            )

        try:
            # Read file asynchronously
            loop = asyncio.get_event_loop()
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            logger.info("Session loaded from file: %s", session_name)

            # Update last_used timestamp
            from datetime import datetime
            session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

            # Cache the session
            self._session_cache[session_name] = session_data

            return session_data

        except json.JSONDecodeError as e:
            error_msg = f"Corrupted session file: {session_name} - Invalid JSON"
            logger.error(error_msg)
            raise AyuGramError(error_msg, {"session_path": str(session_path), "json_error": str(e)}) from e

        except OSError as e:
            error_msg = f"Failed to read session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(error_msg, {"session_path": str(session_path), "os_error": str(e)}) from e

    async def save_session(
        self,
        session_name: str,
        session_data: Dict[str, Any],
    ) -> None:
        """
        Save session data to file system.

        Session files are saved with restricted permissions (0600 on Unix-like systems)
        to protect sensitive authentication data.

        Args:
            session_name: Name for the session (without .json extension)
            session_data: Dictionary containing session data to save

        Raises:
            ValueError: If session_name or session_data is empty
            AyuGramError: If file write fails

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

        session_path = self._get_session_path(session_name)

        logger.info("Saving session: %s", session_name)

        try:
            # Ensure session directory exists
            self._ensure_session_directory()

            # Add timestamps if not present
            from datetime import datetime

            if "created_at" not in session_data:
                session_data["created_at"] = datetime.utcnow().isoformat() + "Z"

            session_data["last_used"] = datetime.utcnow().isoformat() + "Z"

            # Write to file asynchronously
            loop = asyncio.get_event_loop()
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)

            # Set restrictive permissions (Unix-like systems only)
            try:
                os.chmod(session_path, 0o600)
            except (OSError, AttributeError) as e:
                logger.debug("Could not set file permissions for %s: %s", session_path, e)

            # Update cache
            self._session_cache[session_name] = session_data

            logger.info("Session saved successfully: %s", session_name)

        except OSError as e:
            error_msg = f"Failed to save session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(error_msg, {"session_path": str(session_path), "os_error": str(e)}) from e

        except TypeError as e:
            error_msg = f"Failed to serialize session data: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(error_msg, {"session_path": str(session_path), "type_error": str(e)}) from e

    async def delete_session(self, session_name: str) -> bool:
        """
        Delete a session from file system and cache.

        Args:
            session_name: Name of the session to delete (without .json extension)

        Returns:
            True if session was deleted, False if it didn't exist

        Raises:
            ValueError: If session_name is empty

        Example:
            >>> manager = SessionManager()
            >>> success = await manager.delete_session("my_account")
            >>> print(success)
        """
        if not session_name:
            raise ValueError("session_name cannot be empty")

        session_path = self._get_session_path(session_name)

        # Remove from cache
        self._session_cache.pop(session_name, None)

        if not session_path.exists():
            logger.debug("Session file does not exist, nothing to delete: %s", session_name)
            return False

        try:
            # Delete file asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, session_path.unlink)

            logger.info("Session deleted: %s", session_name)
            return True

        except OSError as e:
            error_msg = f"Failed to delete session file: {session_name}"
            logger.error(error_msg)
            raise AyuGramError(error_msg, {"session_path": str(session_path), "os_error": str(e)}) from e

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

            logger.debug("Found %d sessions in %s", len(session_names), self.session_dir)
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

        This does not delete session files from disk, only clears
        the cached copies in memory.

        Example:
            >>> manager = SessionManager()
            >>> manager.clear_cache()
        """
        self._session_cache.clear()
        logger.debug("Session cache cleared")


__all__ = [
    "SessionManager",
]
