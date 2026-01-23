"""
Rate Limit Service
Spec: 026-api-webhook-ecosystem

Service for per-API-key rate limiting using Redis with fallback to in-memory storage.
"""
import logging
import time
import os
from typing import Optional, Dict, Any
from uuid import UUID

import redis.asyncio as redis

from src.core.config import settings
from src.models.api_key import APIKey

logger = logging.getLogger(__name__)

# Default rate limits (can be overridden per API key)
DEFAULT_REQUESTS = 100
DEFAULT_WINDOW = 60  # seconds

# Redis key prefix
REDIS_PREFIX = "ratelimit"


class RateLimitService:
    """Service for rate limiting API requests per API key."""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._in_memory_store: Dict[str, list[float]] = {}

    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        return await redis.from_url(self.redis_url, decode_responses=True)

    def _get_limit_from_key(self, api_key: APIKey) -> tuple[int, int]:
        """
        Extract rate limit from API key.

        Returns:
            tuple: (max_requests, window_seconds)
        """
        if api_key.rate_limit and isinstance(api_key.rate_limit, dict):
            requests = api_key.rate_limit.get("requests", DEFAULT_REQUESTS)
            window = api_key.rate_limit.get("window", DEFAULT_WINDOW)
            return int(requests), int(window)
        return DEFAULT_REQUESTS, DEFAULT_WINDOW

    def _make_redis_key(self, api_key_id: UUID) -> str:
        """Create Redis key for API key rate limiting."""
        return f"{REDIS_PREFIX}:key:{api_key_id}"

    async def check_rate_limit(self, api_key: APIKey) -> tuple[bool, Dict[str, Any]]:
        """
        Check if API key is within rate limit.

        Args:
            api_key: The API key to check

        Returns:
            tuple: (allowed, info_dict)
            - allowed: True if request is allowed, False if rate limited
            - info_dict: Information about current rate limit status
        """
        api_key_id = api_key.id
        max_requests, window = self._get_limit_from_key(api_key)

        # Try Redis first
        redis_available = False
        try:
            r = await self._get_redis()
            redis_available = True
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting: {e}")

        if redis_available:
            try:
                result = await self._check_redis(r, api_key_id, max_requests, window)
                await r.close()
                return result
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                # Fall back to in-memory
                await r.close()

        # Fallback to in-memory rate limiting
        return self._check_in_memory(api_key_id, max_requests, window)

    async def _check_redis(
        self,
        r: redis.Redis,
        api_key_id: UUID,
        max_requests: int,
        window: int,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check rate limit using Redis with sliding window.

        Uses Redis sorted set with timestamps as scores for accurate sliding window.
        """
        key = self._make_redis_key(api_key_id)
        now = time.time()
        window_start = now - window

        # Use a pipeline for atomic operations
        pipe = r.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on the key
        pipe.expire(key, window + 1)

        # Execute pipeline
        results = await pipe.execute()

        current_count = results[1]

        # Check if limit exceeded
        allowed = current_count < max_requests

        # Calculate reset time (oldest timestamp + window)
        reset_at = None
        if not allowed and current_count > 0:
            # Get the oldest timestamp
            oldest = await r.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                reset_at = oldest_timestamp + window

        info = {
            "allowed": allowed,
            "current": current_count,
            "limit": max_requests,
            "window": window,
            "reset_at": int(reset_at) if reset_at else None,
            "remaining": max(0, max_requests - current_count - (1 if not allowed else 0)),
        }

        return allowed, info

    def _check_in_memory(
        self,
        api_key_id: UUID,
        max_requests: int,
        window: int,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check rate limit using in-memory storage (fallback).

        WARNING: This is not suitable for production with multiple workers.
        """
        key = str(api_key_id)
        now = time.time()
        window_start = now - window

        # Get or initialize request list for this key
        requests = self._in_memory_store.get(key, [])

        # Filter out old requests outside the window
        requests = [t for t in requests if t > window_start]

        # Check if limit exceeded
        allowed = len(requests) < max_requests

        # Add current request if allowed
        if allowed:
            requests.append(now)

        # Store updated list
        self._in_memory_store[key] = requests

        # Calculate reset time (oldest timestamp + window)
        reset_at = None
        if not allowed and requests:
            oldest = min(requests)
            reset_at = oldest + window

        info = {
            "allowed": allowed,
            "current": len(requests),
            "limit": max_requests,
            "window": window,
            "reset_at": int(reset_at) if reset_at else None,
            "remaining": max(0, max_requests - len(requests) - (1 if not allowed else 0)),
        }

        return allowed, info

    async def reset_rate_limit(self, api_key_id: UUID) -> bool:
        """
        Reset rate limit for a specific API key.

        Args:
            api_key_id: The API key ID to reset

        Returns:
            True if reset was successful, False otherwise
        """
        try:
            r = await self._get_redis()
            key = self._make_redis_key(api_key_id)
            await r.delete(key)
            await r.close()

            # Also clear from in-memory store
            self._in_memory_store.pop(str(api_key_id), None)

            logger.info(f"Reset rate limit for API key {api_key_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {api_key_id}: {e}")
            return False

    async def get_rate_limit_info(self, api_key: APIKey) -> Dict[str, Any]:
        """
        Get current rate limit status for an API key without incrementing.

        Args:
            api_key: The API key to check

        Returns:
            Dictionary with rate limit information
        """
        api_key_id = api_key.id
        max_requests, window = self._get_limit_from_key(api_key)

        # Try Redis first
        try:
            r = await self._get_redis()
            key = self._make_redis_key(api_key_id)

            now = time.time()
            window_start = now - window

            # Count requests in current window
            await r.zremrangebyscore(key, 0, window_start)
            current_count = await r.zcard(key)

            await r.close()

            return {
                "limit": max_requests,
                "window": window,
                "current": current_count,
                "remaining": max(0, max_requests - current_count),
            }
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limit info: {e}")

        # Fallback to in-memory
        key = str(api_key_id)
        requests = self._in_memory_store.get(key, [])
        now = time.time()
        window_start = now - window
        current_count = len([t for t in requests if t > window_start])

        return {
            "limit": max_requests,
            "window": window,
            "current": current_count,
            "remaining": max(0, max_requests - current_count),
        }

    async def cleanup_expired_keys(self) -> int:
        """
        Cleanup expired rate limit entries (maintenance task).

        Returns:
            Number of keys cleaned up
        """
        cleaned = 0

        # Cleanup in-memory store
        now = time.time()
        keys_to_delete = []
        for key, requests in self._in_memory_store.items():
            # Remove very old entries (older than 1 hour)
            requests = [t for t in requests if t > now - 3600]
            if not requests:
                keys_to_delete.append(key)
            else:
                self._in_memory_store[key] = requests

        for key in keys_to_delete:
            del self._in_memory_store[key]
            cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired in-memory rate limit entries")

        return cleaned


# Global service instance
rate_limit_service = RateLimitService()
