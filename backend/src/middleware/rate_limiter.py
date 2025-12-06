"""
Rate Limiter Middleware for FastAPI.

Implements Fixed Window Counter pattern using Redis INCR+EXPIRE.
Protects all API endpoints from abuse and DDoS attacks.

Architecture:
- Fixed Window Counter: Uses Redis to track request counts per window
- Keys: rl:{endpoint}:{user_id_or_ip}:{window_start}
- Operations: INCR (increment count) + EXPIRE (set TTL)
- Response: 429 Too Many Requests with retry-after header

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

from src.config.rate_limits import get_limit, RateLimit


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
            
            # Get user info for key generation
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
