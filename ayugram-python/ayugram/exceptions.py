"""
AyuGram Custom Exceptions

Custom exception hierarchy for AyuGram SDK operations.
All exceptions inherit from AyuGramError for easy catching.

Example:
    >>> try:
    ...     await client.join_group_call(chat_id, stream)
    ... except ayugram.ConnectionError:
    ...     print("Failed to connect to AyuGram server")
    ... except ayugram.AuthenticationError:
    ...     print("Invalid credentials")
    ... except ayugram.CallError as e:
    ...     print(f"Call failed: {e}")
    ... except ayugram.TimeoutError:
    ...     print("Operation timed out")
"""


class AyuGramError(Exception):
    """
    Base exception for all AyuGram SDK errors.

    All AyuGram-specific exceptions inherit from this class,
    allowing broad error handling with a single except clause.

    Attributes:
        message: Human-readable error description
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: dict | None = None):
        """
        Initialize AyuGramError.

        Args:
            message: Human-readable error description
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ConnectionError(AyuGramError):
    """
    Raised when connection to AyuGram server fails.

    This includes network issues, server unavailability, and
    JSON-RPC communication failures.

    Example:
        >>> ayugram.ConnectionError("Failed to connect to ayugramd: Connection refused")
    """

    pass


class AuthenticationError(AyuGramError):
    """
    Raised when authentication fails.

    This includes invalid credentials, session expiration,
    and authorization errors.

    Example:
        >>> ayugram.AuthenticationError("Invalid session string")
    """

    pass


class CallError(AyuGramError):
    """
    Raised when voice/video call operations fail.

    This includes join errors, stream errors, and leave failures.
    Specific error details are provided in the message and details dict.

    Example:
        >>> ayugram.CallError("Failed to join group call", {"chat_id": -100123456789})
    """

    pass


class TimeoutError(AyuGramError):
    """
    Raised when an operation times out.

    This includes JSON-RPC request timeouts and slow operations.

    Example:
        >>> ayugram.TimeoutError("Request timed out after 30 seconds")
    """

    pass


__all__ = [
    "AyuGramError",
    "ConnectionError",
    "AuthenticationError",
    "CallError",
    "TimeoutError",
]
