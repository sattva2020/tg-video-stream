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

# Import alert thresholds from settings
# These can be overridden via environment variables:
# - RATE_LIMIT_ALERT_WARNING_THRESHOLD (default: 75)
# - RATE_LIMIT_ALERT_CRITICAL_THRESHOLD (default: 90)
# - RATE_LIMIT_ALERT_ENABLED (default: true)
# - RATE_LIMIT_ALERT_COOLDOWN_SECONDS (default: 300)
# - RATE_LIMIT_ALERT_CHANNELS (comma-separated list of channel IDs)


@dataclass
class RateLimitAlertConfig:
    """Alert configuration for rate limit thresholds."""

    warning_threshold_percent: float = 75.0
    critical_threshold_percent: float = 90.0
    enabled: bool = True
    cooldown_seconds: int = 300
    notification_channels: list[str] = None

    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []


# Default alert configuration (can be overridden by settings)
DEFAULT_ALERT_CONFIG = RateLimitAlertConfig()


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


def get_alert_config() -> RateLimitAlertConfig:
    """
    Get alert configuration from settings.

    Returns:
        RateLimitAlertConfig with values from environment or defaults

    Note:
        Values are loaded from environment variables:
        - RATE_LIMIT_ALERT_WARNING_THRESHOLD (default: 75)
        - RATE_LIMIT_ALERT_CRITICAL_THRESHOLD (default: 90)
        - RATE_LIMIT_ALERT_ENABLED (default: true)
        - RATE_LIMIT_ALERT_COOLDOWN_SECONDS (default: 300)
        - RATE_LIMIT_ALERT_CHANNELS (comma-separated list, default: empty)
    """
    try:
        from src.core.config import settings
        return RateLimitAlertConfig(
            warning_threshold_percent=settings.RATE_LIMIT_ALERT_WARNING_THRESHOLD,
            critical_threshold_percent=settings.RATE_LIMIT_ALERT_CRITICAL_THRESHOLD,
            enabled=settings.RATE_LIMIT_ALERT_ENABLED,
            cooldown_seconds=settings.RATE_LIMIT_ALERT_COOLDOWN_SECONDS,
            notification_channels=settings.RATE_LIMIT_ALERT_CHANNELS
        )
    except ImportError:
        # Fallback to defaults if settings are not available
        return DEFAULT_ALERT_CONFIG
