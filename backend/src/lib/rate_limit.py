"""
Rate limiting configuration for the Telegram broadcast platform.

This module configures rate limiting using slowapi with Redis backend
to protect against abuse and ensure fair resource usage.
"""

import os
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from redis.asyncio import Redis

from .error_handlers import ErrorCode, create_error_response


class RedisLimiter:
    """Redis-backed rate limiter."""

    def __init__(self):
        """Initialize Redis connection for rate limiting."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Create Redis client
        self.redis = Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def close(self):
        """Close Redis connection."""
        await self.redis.close()


# Global rate limiter instance
_redis_limiter: Optional[RedisLimiter] = None


def get_redis_limiter() -> RedisLimiter:
    """Get the global Redis limiter instance."""
    global _redis_limiter
    if _redis_limiter is None:
        _redis_limiter = RedisLimiter()
    return _redis_limiter


# Configure rate limiter
limiter = Limiter(
    key_func=get_remote_address,  # Use client IP as key
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    strategy="fixed-window",  # Fixed window rate limiting
    auto_check=False  # We'll check manually in middleware
)


# Rate limit configurations
RATE_LIMITS = {
    # General API limits
    "default": "100/minute",  # 100 requests per minute per IP

    # Authentication endpoints (stricter limits)
    "login": "5/minute",      # 5 login attempts per minute per IP
    "register": "3/minute",   # 3 registration attempts per minute per IP
    "password_reset": "3/hour",  # 3 password reset requests per hour per IP
    "telegram_auth": f"{os.getenv('TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR', '5')}/hour",  # Telegram auth limit

    # Content upload endpoints
    "upload_video": "10/hour",   # 10 video uploads per hour per IP
    "upload_file": "50/hour",    # 50 file uploads per hour per IP

    # Administrative endpoints
    "admin_actions": "60/minute",  # 60 admin actions per minute per IP

    # API endpoints
    "api_read": "200/minute",   # 200 read operations per minute per IP
    "api_write": "50/minute",   # 50 write operations per minute per IP
}


def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on endpoint and user context.

    Args:
        request: FastAPI request object

    Returns:
        str: Rate limit key
    """
    # Base key from client IP
    key = get_remote_address(request)

    # Add user ID if authenticated (per-user limits)
    if hasattr(request.state, 'user_id') and request.state.user_id:
        key = f"user:{request.state.user_id}"
    else:
        key = f"ip:{key}"

    # Add endpoint-specific prefix
    path = request.url.path

    if path.startswith("/auth/login"):
        key = f"login:{key}"
    elif path.startswith("/auth/register") or path.startswith("/users"):
        key = f"register:{key}"
    elif path.startswith("/auth/password-reset"):
        key = f"password_reset:{key}"
    elif path.startswith("/auth/telegram-widget"):
        key = f"telegram_auth:{key}"
    elif path.startswith("/videos/upload"):
        key = f"upload_video:{key}"
    elif "upload" in path or "file" in path:
        key = f"upload_file:{key}"
    elif path.startswith("/admin") or path.startswith("/users"):
        key = f"admin:{key}"
    elif request.method in ["GET", "HEAD", "OPTIONS"]:
        key = f"read:{key}"
    else:
        key = f"write:{key}"

    return key


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Handle rate limit exceeded exceptions.

    Returns a standardized error response.
    """
    # Create error response
    error_response = create_error_response(
        message="Rate limit exceeded. Please try again later.",
        error_code=ErrorCode.QUOTA_EXCEEDED,
        status_code=429,
        details={
            "retry_after": exc.retry_after,
            "limit": exc.limit,
            "remaining": 0
        }
    )

    # Add Retry-After header
    from fastapi.responses import JSONResponse
    response = JSONResponse(
        status_code=429,
        content=error_response.dict(),
        headers={"Retry-After": str(exc.retry_after)}
    )

    return response


# Custom limiter class with enhanced functionality
class EnhancedLimiter(Limiter):
    """Enhanced limiter with custom key functions and error handling."""

    def __init__(self):
        super().__init__(
            key_func=get_rate_limit_key,
            storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            strategy="fixed-window",
            auto_check=False
        )

    async def check_limit(self, request: Request) -> Optional[RateLimitExceeded]:
        """
        Check if request exceeds rate limit.

        Args:
            request: FastAPI request object

        Returns:
            Optional[RateLimitExceeded]: Exception if limit exceeded, None otherwise
        """
        try:
            # Get the limit for this request
            limit = self._get_limit_for_request(request)

            # Check the limit
            return await self.limit(limit)(lambda: None)(request)
        except RateLimitExceeded as e:
            return e
        except Exception:
            # If rate limiting fails, allow the request (fail open)
            return None

    def _get_limit_for_request(self, request: Request) -> str:
        """
        Get the appropriate rate limit for a request.

        Args:
            request: FastAPI request object

        Returns:
            str: Rate limit string (e.g., "100/minute")
        """
        path = request.url.path
        method = request.method

        # Authentication endpoints
        if path.startswith("/auth/login"):
            return RATE_LIMITS["login"]
        elif path.startswith("/auth/register"):
            return RATE_LIMITS["register"]
        elif path.startswith("/auth/password-reset"):
            return RATE_LIMITS["password_reset"]

        # Upload endpoints
        elif path.startswith("/videos/upload") or "upload" in path:
            return RATE_LIMITS["upload_video"]

        # Admin endpoints
        elif path.startswith("/admin") or (path.startswith("/users") and method != "GET"):
            return RATE_LIMITS["admin_actions"]

        # API endpoints
        elif method in ["GET", "HEAD", "OPTIONS"]:
            return RATE_LIMITS["api_read"]
        else:
            return RATE_LIMITS["api_write"]


# Global enhanced limiter instance
_enhanced_limiter: Optional[EnhancedLimiter] = None


def get_enhanced_limiter() -> EnhancedLimiter:
    """Get the global enhanced limiter instance."""
    global _enhanced_limiter
    if _enhanced_limiter is None:
        _enhanced_limiter = EnhancedLimiter()
    return _enhanced_limiter


# Middleware setup function
def setup_rate_limiting(app):
    """
    Setup rate limiting middleware for FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Store limiter instance on app
    app.state.limiter = get_enhanced_limiter()


# Decorator for manual rate limiting
def rate_limit(limit: str):
    """
    Decorator to apply rate limiting to specific endpoints.

    Args:
        limit: Rate limit string (e.g., "10/minute")

    Returns:
        Callable: Decorated function with rate limiting

    Usage:
        @app.post("/special-endpoint")
        @rate_limit("5/minute")
        async def special_endpoint():
            pass
    """
    limiter = get_enhanced_limiter()
    return limiter.limit(limit)


# Utility functions for rate limit management
async def get_rate_limit_status(request: Request) -> dict:
    """
    Get current rate limit status for a request.

    Args:
        request: FastAPI request object

    Returns:
        dict: Rate limit status information
    """
    limiter = get_enhanced_limiter()

    try:
        # This is a simplified version - in practice you'd need to check Redis
        # for the actual remaining requests and reset time
        return {
            "limit": "100/minute",  # Would be dynamic based on endpoint
            "remaining": 95,        # Would be fetched from Redis
            "reset_time": None,     # Would be calculated from Redis TTL
            "retry_after": None
        }
    except Exception:
        return {
            "limit": "unknown",
            "remaining": "unknown",
            "reset_time": None,
            "retry_after": None
        }


async def reset_rate_limit(key: str):
    """
    Reset rate limit for a specific key.

    Args:
        key: Rate limit key to reset

    Note:
        This is an administrative function that should be used carefully.
    """
    redis_limiter = get_redis_limiter()
    # Clear all keys matching the pattern
    # This is a simplified version - actual implementation would depend on Redis key structure
    pass