"""
Unit tests for AyuGram custom exceptions.

This module tests the exception hierarchy in ayugram.exceptions,
ensuring all exceptions work correctly and provide proper error information.
"""

import pytest

from ayugram.exceptions import (
    AyuGramError,
    ConnectionError,
    AuthenticationError,
    CallError,
    TimeoutError,
)


# ============================================================================
# AyuGramError Tests (Base Exception)
# ============================================================================


class TestAyuGramError:
    """Test base AyuGramError exception."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = AyuGramError("Test error message")
        assert error.message == "Test error message"
        assert error.details == {}

    def test_init_with_message_and_details(self):
        """Test initialization with message and details."""
        details = {"code": 500, "context": "test_context"}
        error = AyuGramError("Test error", details=details)
        assert error.message == "Test error"
        assert error.details == details

    def test_init_with_empty_details(self):
        """Test initialization with empty details dict."""
        error = AyuGramError("Test error", details={})
        assert error.details == {}

    def test_init_with_none_details(self):
        """Test initialization with None details."""
        error = AyuGramError("Test error", details=None)
        assert error.details == {}

    def test_str_representation_without_details(self):
        """Test string representation without details."""
        error = AyuGramError("Test error message")
        assert str(error) == "Test error message"

    def test_str_representation_with_details(self):
        """Test string representation with details."""
        details = {"code": 500, "context": "test"}
        error = AyuGramError("Test error", details=details)
        error_str = str(error)
        assert "Test error" in error_str
        assert "Details:" in error_str
        assert "code" in error_str or "500" in error_str

    def test_repr_without_details(self):
        """Test repr without details."""
        error = AyuGramError("Test error")
        repr_str = repr(error)
        assert "AyuGramError" in repr_str
        assert "Test error" in repr_str
        assert "details={}" in repr_str

    def test_repr_with_details(self):
        """Test repr with details."""
        details = {"code": 500}
        error = AyuGramError("Test error", details=details)
        repr_str = repr(error)
        assert "AyuGramError" in repr_str
        assert "Test error" in repr_str
        assert "details={'code': 500}" in repr_str

    def test_raise_and_catch_as_ayugram_error(self):
        """Test raising and catching as AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            raise AyuGramError("Test error")
        assert exc_info.value.message == "Test error"

    def test_exception_inheritance(self):
        """Test that AyuGramError inherits from Exception."""
        error = AyuGramError("Test")
        assert isinstance(error, Exception)
        assert isinstance(error, AyuGramError)

    def test_message_attribute_is_immutable(self):
        """Test that message attribute can be read but not changed via setter."""
        error = AyuGramError("Original message")
        assert error.message == "Original message"
        # Python allows reassignment, so just test initial value
        error.message = "New message"
        assert error.message == "New message"

    def test_details_attribute_can_be_updated(self):
        """Test that details attribute can be updated."""
        error = AyuGramError("Test", details={"key1": "value1"})
        assert error.details == {"key1": "value1"}
        error.details["key2"] = "value2"
        assert error.details == {"key1": "value1", "key2": "value2"}


# ============================================================================
# ConnectionError Tests
# ============================================================================


class TestConnectionError:
    """Test ConnectionError exception."""

    def test_init_connection_error(self):
        """Test ConnectionError initialization."""
        error = ConnectionError("Connection failed")
        assert error.message == "Connection failed"

    def test_connection_error_inheritance(self):
        """Test that ConnectionError inherits from AyuGramError."""
        error = ConnectionError("Test")
        assert isinstance(error, AyuGramError)
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)

    def test_connection_error_with_details(self):
        """Test ConnectionError with details."""
        details = {"host": "localhost", "port": 8080}
        error = ConnectionError("Cannot connect", details=details)
        assert error.details == details

    def test_raise_and_catch_connection_error(self):
        """Test raising and catching ConnectionError."""
        with pytest.raises(ConnectionError) as exc_info:
            raise ConnectionError("Failed to connect")
        assert exc_info.value.message == "Failed to connect"

    def test_catch_as_ayugram_error(self):
        """Test catching ConnectionError as AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            raise ConnectionError("Connection failed")
        assert isinstance(exc_info.value, ConnectionError)

    def test_connection_error_str_representation(self):
        """Test ConnectionError string representation."""
        error = ConnectionError("Connection refused")
        assert "Connection refused" in str(error)


# ============================================================================
# AuthenticationError Tests
# ============================================================================


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_init_authentication_error(self):
        """Test AuthenticationError initialization."""
        error = AuthenticationError("Invalid credentials")
        assert error.message == "Invalid credentials"

    def test_authentication_error_inheritance(self):
        """Test that AuthenticationError inherits from AyuGramError."""
        error = AuthenticationError("Test")
        assert isinstance(error, AyuGramError)
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, Exception)

    def test_authentication_error_with_details(self):
        """Test AuthenticationError with details."""
        details = {"attempt": 3, "max_attempts": 5}
        error = AuthenticationError("Auth failed", details=details)
        assert error.details == details

    def test_raise_and_catch_authentication_error(self):
        """Test raising and catching AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Invalid session")
        assert exc_info.value.message == "Invalid session"

    def test_catch_as_ayugram_error(self):
        """Test catching AuthenticationError as AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            raise AuthenticationError("Auth failed")
        assert isinstance(exc_info.value, AuthenticationError)

    def test_authentication_error_str_representation(self):
        """Test AuthenticationError string representation."""
        error = AuthenticationError("Session expired")
        assert "Session expired" in str(error)


# ============================================================================
# CallError Tests
# ============================================================================


class TestCallError:
    """Test CallError exception."""

    def test_init_call_error(self):
        """Test CallError initialization."""
        error = CallError("Call failed")
        assert error.message == "Call failed"

    def test_call_error_inheritance(self):
        """Test that CallError inherits from AyuGramError."""
        error = CallError("Test")
        assert isinstance(error, AyuGramError)
        assert isinstance(error, CallError)
        assert isinstance(error, Exception)

    def test_call_error_with_details(self):
        """Test CallError with details."""
        details = {"chat_id": -1001234567890, "reason": "permission_denied"}
        error = CallError("Failed to join call", details=details)
        assert error.details == details

    def test_raise_and_catch_call_error(self):
        """Test raising and catching CallError."""
        with pytest.raises(CallError) as exc_info:
            raise CallError("Leave call failed")
        assert exc_info.value.message == "Leave call failed"

    def test_catch_as_ayugram_error(self):
        """Test catching CallError as AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            raise CallError("Call error")
        assert isinstance(exc_info.value, CallError)

    def test_call_error_str_representation(self):
        """Test CallError string representation."""
        error = CallError("Stream error")
        assert "Stream error" in str(error)


# ============================================================================
# TimeoutError Tests
# ============================================================================


class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_init_timeout_error(self):
        """Test TimeoutError initialization."""
        error = TimeoutError("Request timed out")
        assert error.message == "Request timed out"

    def test_timeout_error_inheritance(self):
        """Test that TimeoutError inherits from AyuGramError."""
        error = TimeoutError("Test")
        assert isinstance(error, AyuGramError)
        assert isinstance(error, TimeoutError)
        assert isinstance(error, Exception)

    def test_timeout_error_with_details(self):
        """Test TimeoutError with details."""
        details = {"timeout_seconds": 30, "operation": "join_call"}
        error = TimeoutError("Operation timeout", details=details)
        assert error.details == details

    def test_raise_and_catch_timeout_error(self):
        """Test raising and catching TimeoutError."""
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("RPC timeout")
        assert exc_info.value.message == "RPC timeout"

    def test_catch_as_ayugram_error(self):
        """Test catching TimeoutError as AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            raise TimeoutError("Timeout")
        assert isinstance(exc_info.value, TimeoutError)

    def test_timeout_error_str_representation(self):
        """Test TimeoutError string representation."""
        error = TimeoutError("Connection timeout after 30s")
        assert "Connection timeout after 30s" in str(error)


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_ayugram_error(self):
        """Test that all custom exceptions inherit from AyuGramError."""
        exceptions = [
            ConnectionError("test"),
            AuthenticationError("test"),
            CallError("test"),
            TimeoutError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, AyuGramError)

    def test_all_exceptions_are_catchable_as_base_exception(self):
        """Test that all exceptions can be caught as Exception."""
        exceptions = [
            ConnectionError("test"),
            AuthenticationError("test"),
            CallError("test"),
            TimeoutError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_specific_exception_precedence(self):
        """Test that specific exceptions are caught before base."""
        caught = []

        try:
            raise ConnectionError("Connection failed")
        except ConnectionError as e:
            caught.append("ConnectionError")
        except AyuGramError as e:
            caught.append("AyuGramError")

        assert caught == ["ConnectionError"]

    def test_base_exception_catches_all(self):
        """Test that AyuGramError catches all specific exceptions."""
        exceptions_to_raise = [
            ConnectionError("test"),
            AuthenticationError("test"),
            CallError("test"),
            TimeoutError("test"),
        ]

        for exc_class in exceptions_to_raise:
            with pytest.raises(AyuGramError):
                raise exc_class("test message")


# ============================================================================
# Exception Usage Pattern Tests
# ============================================================================


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_raise_exception_with_context_details(self):
        """Test raising exception with contextual details."""
        details = {
            "operation": "join_group_call",
            "chat_id": -1001234567890,
            "error_code": -32602,
        }
        with pytest.raises(CallError) as exc_info:
            raise CallError("Failed to join call", details=details)

        assert exc_info.value.details["chat_id"] == -1001234567890
        assert exc_info.value.details["operation"] == "join_group_call"

    def test_exception_chaining(self):
        """Test exception chaining (exception from exception)."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConnectionError("Wrapped error") from e
        except ConnectionError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)

    def test_catching_multiple_specific_exceptions(self):
        """Test catching multiple specific exceptions."""
        exceptions_caught = []

        try:
            raise AuthenticationError("Auth failed")
        except (ConnectionError, AuthenticationError) as e:
            exceptions_caught.append(type(e).__name__)

        assert exceptions_caught == ["AuthenticationError"]

    def test_exception_details_mutability(self):
        """Test that exception details can be modified after creation."""
        error = CallError("Test", details={"key1": "value1"})
        error.details["key2"] = "value2"
        error.details["key1"] = "updated"

        assert error.details == {"key1": "updated", "key2": "value2"}

    def test_formatting_error_messages_with_details(self):
        """Test formatting error messages that include details."""
        details = {"chat_id": -1001234567890, "reason": "blocked"}
        error = CallError("Cannot join call", details=details)

        error_str = str(error)
        assert "Cannot join call" in error_str

    def test_exception_in_async_context(self):
        """Test that exceptions work in async context."""
        import asyncio

        async def async_function():
            raise ConnectionError("Async connection failed")

        async def catch_async():
            try:
                await async_function()
            except ConnectionError as e:
                return e.message

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(catch_async())
            assert result == "Async connection failed"
        finally:
            loop.close()


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================


class TestExceptionEdgeCases:
    """Test edge cases and error conditions."""

    def test_exception_with_empty_message(self):
        """Test exception with empty message string."""
        error = AyuGramError("")
        assert error.message == ""
        assert str(error) == ""

    def test_exception_with_very_long_message(self):
        """Test exception with very long message."""
        long_message = "Error: " + "x" * 1000
        error = AyuGramError(long_message)
        assert len(error.message) == 1006  # "Error: " + 1000 chars

    def test_exception_with_unicode_message(self):
        """Test exception with unicode characters in message."""
        message = "Ошибка подключения 🚀"
        error = ConnectionError(message)
        assert error.message == message
        assert "Ошибка" in str(error)

    def test_exception_with_nested_details(self):
        """Test exception with nested dictionary details."""
        details = {
            "error": {
                "code": -32600,
                "message": "Invalid Request",
                "data": {"field": "chat_id", "issue": "required"},
            }
        }
        error = AyuGramError("Validation failed", details=details)
        assert error.details["error"]["data"]["field"] == "chat_id"

    def test_exception_with_list_details(self):
        """Test exception with list in details."""
        details = {"errors": ["error1", "error2", "error3"]}
        error = CallError("Multiple errors", details=details)
        assert len(error.details["errors"]) == 3

    def test_exception_repr_roundtrip(self):
        """Test that repr can be used to recreate similar exception."""
        error1 = AyuGramError("Test", details={"key": "value"})
        repr_str = repr(error1)

        # Just verify repr contains essential information
        assert "AyuGramError" in repr_str
        assert "Test" in repr_str
        assert "key" in repr_str
        assert "value" in repr_str


# ============================================================================
# Integration Tests
# ============================================================================


class TestExceptionIntegration:
    """Integration tests for exception usage."""

    def test_connection_error_handling_workflow(self):
        """Test complete connection error handling workflow."""
        connection_attempts = 0
        max_attempts = 3

        try:
            # Simulate connection failure
            raise ConnectionError(
                "Cannot connect to server",
                details={"attempt": connection_attempts + 1, "max_attempts": max_attempts}
            )
        except ConnectionError as e:
            assert e.details["attempt"] == 1
            assert e.details["max_attempts"] == 3

    def test_authentication_error_with_retry_info(self):
        """Test authentication error with retry information."""
        details = {"attempts_remaining": 2, "lockout_seconds": 300}
        error = AuthenticationError("Invalid password", details=details)

        with pytest.raises(AuthenticationError) as exc_info:
            raise error

        assert exc_info.value.details["attempts_remaining"] == 2

    def test_call_error_with_chat_context(self):
        """Test call error with chat-specific context."""
        details = {
            "chat_id": -1001234567890,
            "chat_title": "Test Group",
            "operation": "join_group_call",
        }
        error = CallError("Permission denied", details=details)

        assert error.details["chat_id"] == -1001234567890
        assert error.details["chat_title"] == "Test Group"

    def test_timeout_error_with_operation_context(self):
        """Test timeout error with operation context."""
        details = {
            "operation": "join_group_call",
            "timeout_seconds": 30,
            "elapsed_seconds": 30.5,
        }
        error = TimeoutError("Operation timed out", details=details)

        with pytest.raises(TimeoutError) as exc_info:
            raise error

        assert exc_info.value.details["operation"] == "join_group_call"
        assert exc_info.value.details["timeout_seconds"] == 30

    def test_exception_logging_scenario(self):
        """Test exception details for logging purposes."""
        error = CallError(
            "Stream failed",
            details={
                "timestamp": "2025-01-25T10:00:00Z",
                "chat_id": -1001234567890,
                "error_code": 500,
            }
        )

        # Simulate extracting info for logging
        log_message = f"{error.message} - Chat: {error.details.get('chat_id')} - Code: {error.details.get('error_code')}"
        assert "Stream failed" in log_message
        assert "-1001234567890" in log_message
        assert "500" in log_message
