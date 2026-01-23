"""Exception classes for Sattva API SDK."""


class SattvaAPIError(Exception):
    """Base exception for all Sattva API errors."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(SattvaAPIError):
    """Raised when authentication fails (invalid API key)."""

    pass


class RateLimitError(SattvaAPIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int = None,
        status_code: int = None,
        response: dict = None,
    ):
        super().__init__(message, status_code, response)
        self.retry_after = retry_after


class NotFoundError(SattvaAPIError):
    """Raised when a resource is not found."""

    pass


class ValidationError(SattvaAPIError):
    """Raised when request validation fails."""

    pass
