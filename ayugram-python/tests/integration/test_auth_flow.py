"""
Integration tests for full authentication flow with mock JSON-RPC server.

These tests verify the complete authentication workflow including:
- Phone number validation
- OTP code request and callback handling
- Authentication with AyuGram via JSON-RPC
- Session creation and persistence
- Error handling for invalid credentials

Tests use the MockAyuGramServer to simulate the AyuGram JSON-RPC API.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from ayugram.exceptions import AuthenticationError
from ayugram.rpc import JsonRpcClient
from ayugram.session import SessionManager


class TestAuthenticationFlow:
    """Test complete authentication flow with mock server."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow_success(self, mock_server):
        """
        Test complete authentication flow with valid credentials.

        This test verifies:
        1. RPC client connects to mock server
        2. auth.send_code is called with phone number
        3. Callback receives phone number and returns OTP code
        4. auth.sign_in is called with phone and code
        5. Session data is returned with user_id and auth_key
        6. Session can be saved to disk
        """
        # Create RPC client connected to mock server
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        # Create session manager with temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Track callback invocations
            callback_invocations = []

            async def code_callback(phone_number: str) -> str:
                """Mock callback that simulates user entering OTP code."""
                callback_invocations.append(phone_number)
                # Return mock 5-digit OTP code
                return "12345"

            # Create session with authentication flow
            phone_number = "+1234567890"
            session_data = await session_manager.create_session(
                phone_number=phone_number,
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )

            # Verify session data structure
            assert session_data is not None
            assert session_data["phone"] == phone_number
            assert session_data["user_id"] == 123456789
            assert session_data["auth_key"] == "mock_auth_key_base64_encoded"
            assert "created_at" in session_data
            assert "last_used" in session_data

            # Verify callback was invoked with correct phone number
            assert len(callback_invocations) == 1
            assert callback_invocations[0] == phone_number

            # Verify session can be saved
            await session_manager.save_session("test_session", session_data)

            # Verify session can be loaded
            loaded_session = await session_manager.load_session("test_session")
            assert loaded_session["phone"] == phone_number
            assert loaded_session["user_id"] == session_data["user_id"]

        # Cleanup RPC client
        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_with_invalid_phone(self, mock_server):
        """
        Test authentication flow with invalid phone number.

        Verifies that authentication fails appropriately when phone number
        doesn't start with '+' or is missing.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            # Test with phone number missing '+'
            with pytest.raises(ValueError, match="must start with"):
                await session_manager.create_session(
                    phone_number="1234567890",  # Missing '+'
                    on_code_callback=code_callback,
                    rpc_client=rpc_client,
                )

            # Test with empty phone number
            with pytest.raises(ValueError, match="cannot be empty"):
                await session_manager.create_session(
                    phone_number="",
                    on_code_callback=code_callback,
                    rpc_client=rpc_client,
                )

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_with_invalid_code(self, mock_server):
        """
        Test authentication flow with invalid OTP code.

        Verifies that authentication fails when the callback returns
        an invalid code format (not 5 digits).
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Test with non-5-digit code
            async def invalid_code_callback(phone_number: str) -> str:
                return "123"  # Only 3 digits

            with pytest.raises(Exception):  # Mock server rejects non-5-digit codes
                await session_manager.create_session(
                    phone_number="+1234567890",
                    on_code_callback=invalid_code_callback,
                    rpc_client=rpc_client,
                )

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_callback_error_handling(self, mock_server):
        """
        Test authentication flow when callback raises an exception.

        Verifies that errors in the callback are properly wrapped in
        AuthenticationError with appropriate details.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Callback that raises an exception
            async def failing_callback(phone_number: str) -> str:
                raise ValueError("User cancelled authentication")

            with pytest.raises(AuthenticationError) as exc_info:
                await session_manager.create_session(
                    phone_number="+1234567890",
                    on_code_callback=failing_callback,
                    rpc_client=rpc_client,
                )

            # Verify error contains context about callback failure
            assert "callback" in str(exc_info.value).lower()

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_with_sync_callback(self, mock_server):
        """
        Test authentication flow with synchronous callback.

        Verifies that both sync and async callbacks are supported
        for code retrieval.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Synchronous callback (not async)
            def sync_code_callback(phone_number: str) -> str:
                return "12345"

            session_data = await session_manager.create_session(
                phone_number="+1234567890",
                on_code_callback=sync_code_callback,
                rpc_client=rpc_client,
            )

            # Verify authentication succeeded
            assert session_data is not None
            assert session_data["phone"] == "+1234567890"

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_session_persistence_after_authentication(self, mock_server):
        """
        Test that session persists correctly after authentication.

        Verifies:
        1. Session is created via authentication
        2. Session is saved to disk
        3. Session can be loaded after restart
        4. Session data includes all required fields
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            # First session manager - create and save session
            session_manager1 = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            phone_number = "+9876543210"
            session_data = await session_manager1.create_session(
                phone_number=phone_number,
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )

            session_name = "persist_test"
            await session_manager1.save_session(session_name, session_data)

            # Second session manager - simulate app restart
            session_manager2 = SessionManager(session_dir=temp_dir)

            # Load session from disk
            loaded_session = await session_manager2.load_session(session_name)

            # Verify all required fields are present
            assert loaded_session["phone"] == phone_number
            assert loaded_session["user_id"] == session_data["user_id"]
            assert loaded_session["auth_key"] == session_data["auth_key"]
            assert "created_at" in loaded_session
            assert "last_used" in loaded_session

            # Verify last_used timestamp was updated on load
            assert loaded_session["last_used"] >= session_data["last_used"]

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_mock_authentication_without_rpc_client(self):
        """
        Test mock authentication flow without RPC client.

        Verifies that SessionManager can create sessions in mock mode
        for testing purposes when no RPC client is provided.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            # Create session WITHOUT rpc_client (mock mode)
            phone_number = "+1555123456"
            session_data = await session_manager.create_session(
                phone_number=phone_number,
                on_code_callback=code_callback,
                rpc_client=None,  # No RPC client
            )

            # Verify mock session was created
            assert session_data is not None
            assert session_data["phone"] == phone_number
            # Mock authentication generates user_id from hash
            assert isinstance(session_data["user_id"], int)
            # Mock auth_key contains phone number
            assert phone_number in session_data["auth_key"]

            # Verify session can be saved and loaded
            await session_manager.save_session("mock_session", session_data)
            loaded = await session_manager.load_session("mock_session")
            assert loaded["phone"] == phone_number

    @pytest.mark.asyncio
    async def test_multiple_simultaneous_authentications(self, mock_server):
        """
        Test multiple concurrent authentication flows.

        Verifies that the SDK can handle multiple authentication
        requests simultaneously without conflicts.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Create multiple authentication tasks
            async def authenticate_phone(phone: str) -> dict:
                async def code_callback(phone_number: str) -> str:
                    # Simulate different codes for different phones numbers
                    return str(hash(phone) % 100000).zfill(5)

                return await session_manager.create_session(
                    phone_number=phone,
                    on_code_callback=code_callback,
                    rpc_client=rpc_client,
                )

            # Run multiple authentications concurrently
            phone_numbers = [
                "+1111111111",
                "+2222222222",
                "+3333333333",
            ]

            results = await asyncio.gather(*[
                authenticate_phone(phone) for phone in phone_numbers
            ])

            # Verify all authentications succeeded
            assert len(results) == 3
            for i, session_data in enumerate(results):
                assert session_data["phone"] == phone_numbers[i]
                assert session_data["user_id"] == 123456789
                assert "auth_key" in session_data

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_with_non_callable_callback(self, mock_server):
        """
        Test authentication with invalid callback parameter.

        Verifies that ValueError is raised when callback is not callable.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            with pytest.raises(ValueError, match="must be callable"):
                await session_manager.create_session(
                    phone_number="+1234567890",
                    on_code_callback="not_a_callable",  # type: ignore
                    rpc_client=rpc_client,
                )

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_authentication_state_updates(self, mock_server):
        """
        Test that authentication properly updates session state.

        Verifies that last_used timestamp is set correctly and
        session data contains all required fields.
        """
        from datetime import datetime

        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            # Record time before authentication
            before_auth = datetime.utcnow()

            # Create session
            session_data = await session_manager.create_session(
                phone_number="+1234567890",
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )

            # Record time after authentication
            after_auth = datetime.utcnow()

            # Verify timestamps
            assert "created_at" in session_data
            assert "last_used" in session_data

            # Parse timestamps and verify they're within expected range
            created_at = session_data["created_at"]
            last_used = session_data["last_used"]

            # Verify format (ISO 8601 with Z suffix)
            assert created_at.endswith("Z")
            assert last_used.endswith("Z")

            # Verify timestamps are recent
            created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            assert before_auth <= created_time <= after_auth

        await rpc_client.stop()


class TestAuthenticationErrorHandling:
    """Test error handling in authentication flow."""

    @pytest.mark.asyncio
    async def test_rpc_connection_failure(self):
        """
        Test authentication when RPC server is unavailable.

        Verifies graceful degradation to mock authentication when
        RPC connection fails.
        """
        # Create RPC client with invalid endpoint
        rpc_client = JsonRpcClient("http://localhost:9999/jsonrpc")

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            # Should fall back to mock authentication
            session_data = await session_manager.create_session(
                phone_number="+1234567890",
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )

            # Verify mock session was created
            assert session_data is not None
            assert session_data["phone"] == "+1234567890"

    @pytest.mark.asyncio
    async def test_callback_returns_non_string(self, mock_server):
        """
        Test authentication when callback returns non-string value.

        Verifies AuthenticationError is raised with appropriate message.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            # Callback that returns integer instead of string
            async def invalid_callback(phone_number: str) -> int:
                return 12345  # type: ignore

            with pytest.raises(AuthenticationError, match="Invalid code"):
                await session_manager.create_session(
                    phone_number="+1234567890",
                    on_code_callback=invalid_callback,
                    rpc_client=rpc_client,
                )

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_callback_returns_empty_code(self, mock_server):
        """
        Test authentication when callback returns empty string.

        Verifies AuthenticationError is raised when code is empty.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def empty_callback(phone_number: str) -> str:
                return ""

            with pytest.raises(AuthenticationError, match="Invalid code"):
                await session_manager.create_session(
                    phone_number="+1234567890",
                    on_code_callback=empty_callback,
                    rpc_client=rpc_client,
                )

        await rpc_client.stop()


class TestSessionReauth:
    """Test re-authentication scenarios."""

    @pytest.mark.asyncio
    async def test_reauth_after_session_deletion(self, mock_server):
        """
        Test re-authentication after deleting existing session.

        Verifies that a new session can be created after deleting
        an old one.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            phone_number = "+1234567890"

            # Create and save session
            session1 = await session_manager.create_session(
                phone_number=phone_number,
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )
            await session_manager.save_session("test", session1)

            # Delete session
            await session_manager.delete_session("test")

            # Create new session (re-authenticate)
            session2 = await session_manager.create_session(
                phone_number=phone_number,
                on_code_callback=code_callback,
                rpc_client=rpc_client,
            )

            # Verify new session was created
            assert session2 is not None
            assert session2["phone"] == phone_number

        await rpc_client.stop()

    @pytest.mark.asyncio
    async def test_auth_with_different_phone_numbers(self, mock_server):
        """
        Test multiple authentications with different phone numbers.

        Verifies that each phone number gets a unique session.
        """
        rpc_client = JsonRpcClient(mock_server.server_url)
        await rpc_client.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(session_dir=temp_dir)

            async def code_callback(phone_number: str) -> str:
                return "12345"

            # Authenticate with different phone numbers
            phones = ["+1111111111", "+2222222222", "+3333333333"]

            sessions = {}
            for phone in phones:
                session = await session_manager.create_session(
                    phone_number=phone,
                    on_code_callback=code_callback,
                    rpc_client=rpc_client,
                )
                sessions[phone] = session

            # Verify each phone got a unique session
            assert len(sessions) == 3
            for phone, session in sessions.items():
                assert session["phone"] == phone
                await session_manager.save_session(phone, session)

            # Verify all sessions can be loaded
            for phone in phones:
                loaded = await session_manager.load_session(phone)
                assert loaded["phone"] == phone

        await rpc_client.stop()
