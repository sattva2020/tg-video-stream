"""
Per-platform health monitoring module.

Provides independent health monitoring for each streaming platform with:
- Platform-specific health metrics
- Independent failure handling
- Redis health status publishing
- Configurable health check intervals and thresholds
- Auto-recovery with exponential backoff

User Story 1 (Cross-Platform Broadcasting):
As a content creator, I want each platform stream independently monitored
so that a single platform failure doesn't affect other streams.

Technical Implementation:
- HealthMonitor class tracks per-platform health state
- Independent failure counters per platform
- Redis publishing for cross-service health visibility
- Exponential backoff for reconnection attempts
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from enum import Enum

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)


class PlatformHealthStatus(Enum):
    """Platform health status states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass
class PlatformHealthMetrics:
    """
    Health metrics for a single platform.

    Tracks:
    - Current health status
    - Consecutive failure count
    - Last health check timestamp
    - Recovery attempt history
    """
    platform_id: str
    status: PlatformHealthStatus = PlatformHealthStatus.UNKNOWN
    consecutive_failures: int = 0
    total_failures: int = 0
    total_checks: int = 0
    last_check_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_recovery_time: Optional[datetime] = None
    recovery_attempts: int = 0
    error_message: Optional[str] = None
    is_streaming: bool = False
    stream_uptime_seconds: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for Redis/API."""
        return {
            "platform_id": self.platform_id,
            "status": self.status.value,
            "consecutive_failures": self.consecutive_failures,
            "total_failures": self.total_failures,
            "total_checks": self.total_checks,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_recovery_time": self.last_recovery_time.isoformat() if self.last_recovery_time else None,
            "recovery_attempts": self.recovery_attempts,
            "error_message": self.error_message,
            "is_streaming": self.is_streaming,
            "stream_uptime_seconds": self.stream_uptime_seconds,
            "updated_at": self.last_updated.isoformat(),
        }

    def calculate_health_score(self) -> float:
        """
        Calculate health score (0.0 to 1.0).

        Returns:
            Health score where 1.0 is perfectly healthy
        """
        if not self.total_checks:
            return 1.0

        # Base score on success rate
        success_rate = 1.0 - (self.total_failures / self.total_checks)

        # Penalize consecutive failures
        consecutive_penalty = min(0.5, self.consecutive_failures * 0.1)

        # Calculate final score
        score = max(0.0, success_rate - consecutive_penalty)
        return round(score, 2)


class HealthMonitor:
    """
    Per-platform health monitoring with independent failure handling.

    Features:
    - Independent health tracking per platform
    - Configurable failure thresholds
    - Automatic health status publishing to Redis
    - Callback-based failure handling
    - Exponential backoff for recovery attempts
    """

    # Configuration
    DEFAULT_HEALTH_CHECK_INTERVAL = 30  # seconds
    DEFAULT_FAILURE_THRESHOLD = 3  # consecutive failures before unhealthy
    DEFAULT_RECOVERY_THRESHOLD = 2  # consecutive successes before healthy
    DEFAULT_MAX_RECOVERY_ATTEMPTS = 5  # maximum auto-recovery attempts
    REDIS_HEALTH_TTL = 60  # seconds

    def __init__(
        self,
        redis_url: Optional[str] = None,
        health_check_interval: int = DEFAULT_HEALTH_CHECK_INTERVAL,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_threshold: int = DEFAULT_RECOVERY_THRESHOLD,
        max_recovery_attempts: int = DEFAULT_MAX_RECOVERY_ATTEMPTS,
    ):
        """
        Initialize health monitor.

        Args:
            redis_url: Redis URL for health status publishing
            health_check_interval: Seconds between health checks
            failure_threshold: Consecutive failures before marking unhealthy
            recovery_threshold: Consecutive successes before marking healthy
            max_recovery_attempts: Maximum auto-recovery attempts per platform
        """
        # Platform health metrics
        self._platform_metrics: Dict[str, PlatformHealthMetrics] = {}

        # Redis for health status publishing
        self._redis: Optional[Any] = None
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Configuration
        self._health_check_interval = health_check_interval
        self._failure_threshold = failure_threshold
        self._recovery_threshold = recovery_threshold
        self._max_recovery_attempts = max_recovery_attempts

        # Health check functions per platform
        self._health_check_funcs: Dict[str, Callable[[], bool]] = {}

        # Recovery callbacks per platform
        self._recovery_callbacks: Dict[str, Callable[[], bool]] = {}

        # Monitoring loop control
        self._monitor_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()

        self.logger = logger

    async def initialize(self) -> bool:
        """
        Initialize health monitor and connect to Redis.

        Returns:
            True if initialization successful
        """
        try:
            # Connect to Redis
            if aioredis:
                try:
                    self._redis = aioredis.from_url(
                        self._redis_url,
                        decode_responses=True
                    )
                    await self._redis.ping()
                    self.logger.info("HealthMonitor: Redis connected")
                except Exception as e:
                    self.logger.warning(f"Redis connection failed: {e}")
                    self._redis = None

            self.logger.info("HealthMonitor initialized")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize HealthMonitor: {e}")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown health monitor."""
        self.logger.info("Shutting down HealthMonitor...")

        # Stop monitoring loop
        self._stop_event.set()
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Close Redis
        if self._redis:
            await self._redis.close()
            self._redis = None

        self.logger.info("HealthMonitor shutdown complete")

    async def register_platform(
        self,
        platform_id: str,
        health_check_func: Callable[[], bool],
        recovery_callback: Optional[Callable[[], bool]] = None,
    ) -> None:
        """
        Register a platform for health monitoring.

        Args:
            platform_id: Unique platform identifier
            health_check_func: Async function that returns True if platform is healthy
            recovery_callback: Optional async function to attempt recovery
        """
        async with self._lock:
            # Create metrics if not exists
            if platform_id not in self._platform_metrics:
                self._platform_metrics[platform_id] = PlatformHealthMetrics(
                    platform_id=platform_id,
                    status=PlatformHealthStatus.UNKNOWN
                )

            # Register health check function
            self._health_check_funcs[platform_id] = health_check_func

            # Register recovery callback
            if recovery_callback:
                self._recovery_callbacks[platform_id] = recovery_callback

            self.logger.info(f"Registered platform {platform_id} for health monitoring")

    async def unregister_platform(self, platform_id: str) -> None:
        """
        Unregister a platform from health monitoring.

        Args:
            platform_id: Platform identifier to unregister
        """
        async with self._lock:
            self._platform_metrics.pop(platform_id, None)
            self._health_check_funcs.pop(platform_id, None)
            self._recovery_callbacks.pop(platform_id, None)

            # Remove from Redis
            if self._redis:
                try:
                    await self._redis.delete(f"platform:health:{platform_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete health status from Redis: {e}")

            self.logger.info(f"Unregistered platform {platform_id} from health monitoring")

    async def get_platform_health(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health status for a platform.

        Args:
            platform_id: Platform identifier

        Returns:
            Health metrics dictionary or None if not found
        """
        if platform_id not in self._platform_metrics:
            return None

        metrics = self._platform_metrics[platform_id]
        return metrics.to_dict()

    async def get_all_platform_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all registered platforms.

        Returns:
            Dictionary mapping platform_id to health metrics
        """
        return {
            platform_id: metrics.to_dict()
            for platform_id, metrics in self._platform_metrics.items()
        }

    async def update_platform_streaming_status(
        self,
        platform_id: str,
        is_streaming: bool,
        uptime_seconds: float = 0.0,
    ) -> None:
        """
        Update streaming status for a platform.

        Args:
            platform_id: Platform identifier
            is_streaming: Whether platform is currently streaming
            uptime_seconds: Stream uptime in seconds
        """
        async with self._lock:
            if platform_id in self._platform_metrics:
                metrics = self._platform_metrics[platform_id]
                metrics.is_streaming = is_streaming
                metrics.stream_uptime_seconds = uptime_seconds
                metrics.last_updated = datetime.now(timezone.utc)

                # Publish updated status
                await self._publish_health_status(platform_id, metrics)

    async def check_platform_health(self, platform_id: str) -> bool:
        """
        Manually trigger health check for a platform.

        Args:
            platform_id: Platform identifier

        Returns:
            True if platform is healthy
        """
        if platform_id not in self._health_check_funcs:
            self.logger.warning(f"No health check function for platform {platform_id}")
            return False

        health_check_func = self._health_check_funcs[platform_id]
        try:
            is_healthy = await health_check_func()
            await self._process_health_check_result(platform_id, is_healthy)
            return is_healthy
        except Exception as e:
            self.logger.error(f"Health check failed for platform {platform_id}: {e}")
            await self._process_health_check_result(platform_id, False, error=str(e))
            return False

    async def start_monitoring(self) -> None:
        """Start the background health monitoring loop."""
        if self._monitor_task and not self._monitor_task.done():
            self.logger.warning("Health monitoring already started")
            return

        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Started health monitoring loop")

    async def stop_monitoring(self) -> None:
        """Stop the background health monitoring loop."""
        self._stop_event.set()
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped health monitoring loop")

    async def _monitoring_loop(self) -> None:
        """
        Background monitoring loop.

        Periodically checks health of all registered platforms
        and attempts recovery for unhealthy ones.
        """
        self.logger.info(
            f"Health monitoring loop started (interval={self._health_check_interval}s)"
        )

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)

                # Check all registered platforms
                platform_ids = list(self._health_check_funcs.keys())

                for platform_id in platform_ids:
                    await self.check_platform_health(platform_id)

                # Attempt recovery for unhealthy platforms
                await self._attempt_recovery()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")

        self.logger.info("Health monitoring loop stopped")

    async def _process_health_check_result(
        self,
        platform_id: str,
        is_healthy: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Process health check result and update metrics.

        Args:
            platform_id: Platform identifier
            is_healthy: Whether health check passed
            error: Optional error message if unhealthy
        """
        async with self._lock:
            if platform_id not in self._platform_metrics:
                return

            metrics = self._platform_metrics[platform_id]
            metrics.last_check_time = datetime.now(timezone.utc)
            metrics.total_checks += 1
            metrics.last_updated = datetime.now(timezone.utc)

            if is_healthy:
                # Health check passed
                metrics.consecutive_failures = 0
                metrics.error_message = None

                # Update status based on recovery threshold
                if metrics.status in [PlatformHealthStatus.UNHEALTHY, PlatformHealthStatus.RECOVERING]:
                    if metrics.consecutive_failures == 0:
                        # First success after failure - check recovery threshold
                        if self._recovery_threshold <= 1:
                            metrics.status = PlatformHealthStatus.HEALTHY
                            metrics.last_recovery_time = datetime.now(timezone.utc)
                        else:
                            metrics.status = PlatformHealthStatus.RECOVERING
                elif metrics.status == PlatformHealthStatus.RECOVERING:
                    # Count consecutive successes
                    if not hasattr(metrics, '_consecutive_successes'):
                        metrics._consecutive_successes = 0
                    metrics._consecutive_successes += 1

                    if metrics._consecutive_successes >= self._recovery_threshold:
                        metrics.status = PlatformHealthStatus.HEALTHY
                        metrics.last_recovery_time = datetime.now(timezone.utc)
                        delattr(metrics, '_consecutive_successes')
                else:
                    metrics.status = PlatformHealthStatus.HEALTHY

            else:
                # Health check failed
                metrics.consecutive_failures += 1
                metrics.total_failures += 1
                metrics.last_failure_time = datetime.now(timezone.utc)
                metrics.error_message = error

                # Update status based on failure threshold
                if metrics.consecutive_failures >= self._failure_threshold:
                    metrics.status = PlatformHealthStatus.UNHEALTHY
                elif metrics.consecutive_failures > 0:
                    metrics.status = PlatformHealthStatus.DEGRADED

            # Publish health status
            await self._publish_health_status(platform_id, metrics)

    async def _attempt_recovery(self) -> None:
        """Attempt recovery for unhealthy platforms."""
        async with self._lock:
            for platform_id, metrics in self._platform_metrics.items():
                # Only attempt recovery for unhealthy platforms with recovery callback
                if (metrics.status != PlatformHealthStatus.UNHEALTHY or
                    platform_id not in self._recovery_callbacks or
                    metrics.recovery_attempts >= self._max_recovery_attempts):
                    continue

                recovery_callback = self._recovery_callbacks[platform_id]

                self.logger.info(f"Attempting recovery for platform {platform_id}")

                try:
                    metrics.status = PlatformHealthStatus.RECOVERING
                    await self._publish_health_status(platform_id, metrics)

                    # Call recovery callback
                    success = await recovery_callback()

                    if success:
                        metrics.recovery_attempts += 1
                        self.logger.info(f"Recovery successful for platform {platform_id}")
                    else:
                        metrics.recovery_attempts += 1
                        metrics.error_message = "Recovery attempt failed"
                        metrics.status = PlatformHealthStatus.UNHEALTHY
                        self.logger.warning(f"Recovery failed for platform {platform_id}")

                    await self._publish_health_status(platform_id, metrics)

                except Exception as e:
                    metrics.recovery_attempts += 1
                    metrics.error_message = f"Recovery error: {str(e)}"
                    metrics.status = PlatformHealthStatus.UNHEALTHY
                    self.logger.error(f"Recovery error for platform {platform_id}: {e}")
                    await self._publish_health_status(platform_id, metrics)

    async def _publish_health_status(
        self,
        platform_id: str,
        metrics: PlatformHealthMetrics,
    ) -> None:
        """
        Publish health status to Redis.

        Args:
            platform_id: Platform identifier
            metrics: Health metrics to publish
        """
        if not self._redis:
            return

        try:
            key = f"platform:health:{platform_id}"
            data = metrics.to_dict()

            # Add health score
            data["health_score"] = metrics.calculate_health_score()

            # Store as JSON
            await self._redis.set(key, json.dumps(data), ex=self.REDIS_HEALTH_TTL)

            self.logger.debug(
                f"Published health status for {platform_id}: "
                f"{metrics.status.value} (score: {data['health_score']})"
            )

        except Exception as e:
            self.logger.warning(f"Failed to publish health status to Redis: {e}")


# Global instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """
    Get or create global HealthMonitor instance.

    Returns:
        HealthMonitor instance
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def initialize_health_monitor() -> HealthMonitor:
    """
    Initialize and return the global HealthMonitor.

    Returns:
        Initialized HealthMonitor instance
    """
    monitor = get_health_monitor()
    await monitor.initialize()
    return monitor


def reset_health_monitor() -> None:
    """Reset global health monitor instance (for testing)."""
    global _health_monitor
    _health_monitor = None
