"""
Rate Limiter Middleware for FastAPI.

Implements Fixed Window Counter pattern using Redis INCR+EXPIRE.
Protects all API endpoints from abuse and DDoS attacks.

Architecture:
- Fixed Window Counter: Uses Redis to track request counts per window
- Keys: rl:{endpoint}:{user_id_or_ip}:{window_start}
- Operations: INCR (increment count) + EXPIRE (set TTL)
- Response: 429 Too Many Requests with retry-after header

Priority:
1. Per-API-key rate limits (if X-API-Key header present)
2. IP-based rate limits (fallback)

Usage:
    app.add_middleware(RateLimiterMiddleware, redis_client=redis)
"""

import time
import logging
from typing import Optional, Tuple
from functools import wraps

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis
from sqlalchemy.orm import Session

from src.config.rate_limits import get_limit, RateLimit
from src.services.api_key_service import APIKeyService
from src.services.rate_limit_service import rate_limit_service


logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis Fixed Window Counter.
    
    Protects endpoints based on configuration in rate_limits.py.
    Tracks requests per user (or IP if anonymous) per time window.
    """
    
    def __init__(self, app, redis_client: redis.Redis):
        """
        Initialize rate limiter middleware.
        
        Args:
            app: FastAPI application
            redis_client: Redis client for storing counters
        """
        super().__init__(app)
        self.redis = redis_client
        self.logger = logger
        
    async def dispatch(self, request: Request, call_next):
        """
        Process request through rate limiter.

        Returns:
            429 Too Many Requests if limit exceeded
            Otherwise continues to next middleware/handler
        """
        try:
            # Skip rate limiting for certain paths
            if self._should_skip_rate_limit(request.url.path):
                return await call_next(request)

            # Get endpoint identifier and rate limit config
            endpoint_id = self._get_endpoint_id(request.url.path)
            if not endpoint_id:
                return await call_next(request)

            # Priority 1: Check API key rate limits (if X-API-Key header present)
            api_key_limited, api_key_retry_after, api_key_info = await self._check_api_key_rate_limit(request)
            if api_key_limited:
                self.logger.warning(
                    f"API key rate limit exceeded: endpoint={endpoint_id}, "
                    f"retry_after={api_key_retry_after}s"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "API key rate limit exceeded",
                        "retry_after": api_key_retry_after,
                        "limit": api_key_info.get("limit") if api_key_info else None,
                        "remaining": 0,
                    },
                    headers={
                        "Retry-After": str(api_key_retry_after),
                        "X-RateLimit-Limit": str(api_key_info.get("limit", "unknown")) if api_key_info else "unknown",
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Scope": "api_key",
                    }
                )

            # Priority 2: Check IP-based rate limits
            user_id = self._get_user_id(request)
            user_role = self._get_user_role(request)

            # Check rate limit
            is_limited, retry_after = self._check_rate_limit(
                endpoint_id, user_id, user_role
            )

            if is_limited:
                self.logger.warning(
                    f"Rate limit exceeded: endpoint={endpoint_id}, "
                    f"user={user_id}, retry_after={retry_after}s"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": "see config",
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Scope": "ip",
                    }
                )

            # Continue to handler
            response = await call_next(request)
            return response

        except Exception as e:
            self.logger.error(f"Rate limiter error: {e}")
            # On error, allow request to proceed (fail open)
            return await call_next(request)
    
    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if path should skip rate limiting."""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/api/auth/login",
            "/api/playlist",  # Playlist needs frequent polling
            "/api/channels",  # Channels status polling
        ]
        return any(path.startswith(p) for p in skip_paths)
    
    def _get_endpoint_id(self, path: str) -> Optional[str]:
        """Extract endpoint identifier from path."""
        # Map paths to endpoint IDs
        if "/playback" in path:
            return "playback"
        elif "/recognition" in path:
            return "recognition"
        else:
            return "api"  # Default for all other API endpoints
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request (user_id or IP)."""
        # Try to get user from auth token
        try:
            if hasattr(request.state, "user_id"):
                return f"user:{request.state.user_id}"
        except AttributeError:
            pass
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_user_role(self, request: Request) -> Optional[str]:
        """Extract user role from request."""
        try:
            if hasattr(request.state, "user_role"):
                return request.state.user_role
        except AttributeError:
            pass
        return None

    async def _check_api_key_rate_limit(self, request: Request) -> Tuple[bool, int, Optional[dict]]:
        """
        Check API key rate limit before IP-based limits.

        Priority 1: Per-API-key rate limiting

        Returns:
            (is_limited, retry_after_seconds, info_dict) tuple
        """
        # Get API key from header
        api_key_header = request.headers.get("X-API-Key")
        if not api_key_header:
            # No API key present, skip to IP-based limiting
            return False, 0, None

        db = None
        try:
            # Get database session from request state (injected by dependency)
            # Note: We need to get db from app state or create a new session
            from src.database import get_db
            db_gen = get_db()
            db = next(db_gen)

            # Validate the API key
            api_key_service = APIKeyService(db)
            api_key = api_key_service.validate_key(api_key_header)

            if not api_key:
                # Invalid API key - let the request proceed to auth layer
                # (which will reject it with 401)
                return False, 0, None

            # Check per-API-key rate limit
            allowed, info = await rate_limit_service.check_rate_limit(api_key)

            # Store API key in request state for later use
            if not hasattr(request.state, "api_key"):
                request.state.api_key = api_key

            if not allowed:
                # Rate limit exceeded
                retry_after = info.get("reset_at", 0)
                if retry_after:
                    retry_after = int(max(0, retry_after - time.time()))
                return True, max(retry_after, 1), info

            return False, 0, info

        except Exception as e:
            self.logger.error(f"Error checking API key rate limit: {e}")
            # On error, allow request to proceed (fail open)
            return False, 0, None
        finally:
            # Clean up database session
            if db is not None:
                try:
                    # Close the generator to properly clean up
                    db_gen.close()
                except Exception:
                    pass
    
    def _check_rate_limit(
        self,
        endpoint: str,
        user_id: str,
        user_role: Optional[str] = None
    ) -> Tuple[bool, int]:
        """
        Check if request exceeds rate limit.
        
        Returns:
            (is_limited, retry_after_seconds) tuple
        """
        try:
            limit = get_limit(endpoint, user_role)
            window_start = int(time.time() // limit.window_seconds)
            key = f"{limit.key_prefix}{user_id}:{window_start}"
            
            # Increment counter
            current = self.redis.incr(key)
            
            # Set expiration on first increment in window
            if current == 1:
                self.redis.expire(key, limit.window_seconds + 1)
            
            # Check if limit exceeded
            if current > limit.requests:
                # Calculate seconds until next window
                next_window = window_start + limit.window_seconds
                retry_after = int(next_window - time.time()) + 1
                return True, max(retry_after, 1)
            
            return False, 0
            
        except redis.RedisError as e:
            self.logger.error(f"Redis error in rate limiter: {e}")
            return False, 0  # Fail open on Redis error


def rate_limit(endpoint: str):
    """
    Decorator for per-endpoint rate limiting.
    
    Usage:
        @rate_limit("playback")
        async def my_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be implemented based on request context
            # For now, limiting is handled by middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator
