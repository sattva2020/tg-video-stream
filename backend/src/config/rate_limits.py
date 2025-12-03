"""
Rate limit configuration for API endpoints.

Implements Fixed Window Counter pattern using Redis INCR+EXPIRE.
Protects against abuse and DDoS attacks.

Technical Decision (TD-005): Fixed Window Counter chosen over Sliding Window
- Simpler Redis operations (single INCR + EXPIRE)
- Acceptable for most use cases
- Trades slight timing variation for performance
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimit:
    """Rate limit configuration for an endpoint."""
    
    requests: int  # Number of allowed requests
    window_seconds: int  # Time window in seconds
    key_prefix: str  # Redis key prefix for this limit


# Global rate limits (applied to all users)
GLOBAL_LIMITS = {
    "playback": RateLimit(requests=100, window_seconds=60, key_prefix="rl:playback:"),
    "api": RateLimit(requests=1000, window_seconds=60, key_prefix="rl:api:"),
    "recognition": RateLimit(requests=10, window_seconds=60, key_prefix="rl:recognition:"),
}

# Per-user rate limits (identified by user_id or IP)
USER_LIMITS = {
    "playback": RateLimit(requests=50, window_seconds=60, key_prefix="rl:user:playback:"),
    "api": RateLimit(requests=500, window_seconds=60, key_prefix="rl:user:api:"),
    "recognition": RateLimit(requests=10, window_seconds=60, key_prefix="rl:user:recognition:"),
}

# VIP user overrides (for premium/admin users)
VIP_LIMITS = {
    "playback": RateLimit(requests=500, window_seconds=60, key_prefix="rl:vip:playback:"),
    "api": RateLimit(requests=5000, window_seconds=60, key_prefix="rl:vip:api:"),
    "recognition": RateLimit(requests=100, window_seconds=60, key_prefix="rl:vip:recognition:"),
}


def get_limit(endpoint: str, user_role: Optional[str] = None) -> RateLimit:
    """
    Get rate limit configuration for an endpoint.
    
    Args:
        endpoint: Endpoint identifier (e.g., 'playback', 'api', 'recognition')
        user_role: User role ('vip', 'user', or None for global)
        
    Returns:
        RateLimit configuration object
        
    Raises:
        ValueError: If endpoint is not recognized
    """
    if user_role == "vip" and endpoint in VIP_LIMITS:
        return VIP_LIMITS[endpoint]
    elif user_role == "user" and endpoint in USER_LIMITS:
        return USER_LIMITS[endpoint]
    elif endpoint in GLOBAL_LIMITS:
        return GLOBAL_LIMITS[endpoint]
    else:
        raise ValueError(f"Unknown rate limit endpoint: {endpoint}")
