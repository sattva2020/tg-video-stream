"""
Error handling infrastructure for the Telegram broadcast platform.

This module defines custom exceptions, HTTP exception mappers,
and structured error responses following the OpenAPI specification.
"""

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    # Authentication errors
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"

    # Business logic errors
    INVALID_OPERATION = "INVALID_OPERATION"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class APIError(Exception):
    """Base exception class for API errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API error.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(APIError):
    """Exception for authentication-related errors."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            status_code=401,
            details=details
        )


class AuthorizationError(APIError):
    """Exception for authorization/permission errors."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=403,
            details=details
        )


class NotFoundError(APIError):
    """Exception for resource not found errors."""

    def __init__(self, resource: str, resource_id: Any = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id is not None:
            message += f" with id {resource_id}"

        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


class ValidationError(APIError):
    """Exception for input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=error_details
        )


class ConflictError(APIError):
    """Exception for resource conflict errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )


class ServiceUnavailableError(APIError):
    """Exception for service unavailable errors."""

    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Service {service} is currently unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details=details
        )


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {
                        "field": "email",
                        "reason": "Invalid email format"
                    }
                }
            }
        }


def create_error_response(
    message: str,
    error_code: ErrorCode,
    status_code: int,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        message: Human-readable error message
        error_code: Standardized error code
        status_code: HTTP status code
        details: Additional error details

    Returns:
        ErrorResponse: Standardized error response
    """
    return ErrorResponse(
        error={
            "code": error_code.value,
            "message": message,
            "details": details or {}
        }
    )


def map_exception_to_response(exception: Exception) -> tuple[ErrorResponse, int]:
    """
    Map an exception to a standardized error response and status code.

    Args:
        exception: The exception to map

    Returns:
        tuple: (ErrorResponse, status_code)
    """
    if isinstance(exception, APIError):
        return create_error_response(
            exception.message,
            exception.error_code,
            exception.status_code,
            exception.details
        ), exception.status_code

    elif isinstance(exception, HTTPException):
        # Map FastAPI HTTPException to our format
        error_code = ErrorCode.INTERNAL_ERROR
        if exception.status_code == 401:
            error_code = ErrorCode.AUTHENTICATION_REQUIRED
        elif exception.status_code == 403:
            error_code = ErrorCode.INSUFFICIENT_PERMISSIONS
        elif exception.status_code == 404:
            error_code = ErrorCode.NOT_FOUND
        elif exception.status_code == 409:
            error_code = ErrorCode.CONFLICT

        return create_error_response(
            exception.detail,
            error_code,
            exception.status_code
        ), exception.status_code

    else:
        # Generic internal server error for unhandled exceptions
        return create_error_response(
            "An internal server error occurred",
            ErrorCode.INTERNAL_ERROR,
            500,
            {"original_error": str(exception)} if __debug__ else {}
        ), 500


# FastAPI exception handlers
async def api_error_handler(request, exc: APIError):
    """Handle APIError exceptions."""
    error_response, status_code = map_exception_to_response(exc)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


async def http_exception_handler(request, exc: HTTPException):
    """Handle FastAPI HTTPException."""
    error_response, status_code = map_exception_to_response(exc)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


async def generic_exception_handler(request, exc: Exception):
    """Handle generic exceptions."""
    error_response, status_code = map_exception_to_response(exc)
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


# Utility functions for common error scenarios
def raise_not_found(resource: str, resource_id: Any = None):
    """Raise a NotFoundError."""
    raise NotFoundError(resource, resource_id)


def raise_validation_error(message: str, field: Optional[str] = None):
    """Raise a ValidationError."""
    raise ValidationError(message, field)


def raise_conflict_error(message: str):
    """Raise a ConflictError."""
    raise ConflictError(message)


def raise_authentication_error(message: str = "Authentication required"):
    """Raise an AuthenticationError."""
    raise AuthenticationError(message)


def raise_authorization_error(message: str = "Insufficient permissions"):
    """Raise an AuthorizationError."""
    raise AuthorizationError(message)


def raise_service_unavailable(service: str):
    """Raise a ServiceUnavailableError."""
    raise ServiceUnavailableError(service)