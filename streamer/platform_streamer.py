"""
Multi-platform stream management module.

Manages simultaneous broadcasts to multiple platforms (YouTube, Twitch, Custom RTMP) with:
- Independent stream state per platform
- Platform-specific settings and optimizations
- Automatic reconnection handling
- Failure isolation (one platform failure doesn't affect others)
- Redis status synchronization

User Story 1 (Cross-Platform Broadcasting):
As a content creator, I want to stream to multiple platforms at once
so that I can reach audiences everywhere.

Technical Implementation:
- Each platform has isolated RTMPStreamer instance
- Platform-specific StreamConfig and health monitoring
- Redis for cross-process status synchronization
- Graceful shutdown with platform state preservation
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

try:
    from streamer.rtmp_streamer import RTMPStreamer, StreamConfig, PlatformType
except ImportError:
    try:
        from rtmp_streamer import RTMPStreamer, StreamConfig, PlatformType
    except ImportError:
        # Module not available - define stubs
        RTMPStreamer = StreamConfig = PlatformType = None

try:
    from streamer.health_monitor import HealthMonitor, get_health_monitor
except ImportError:
    try:
        from health_monitor import HealthMonitor, get_health_monitor
    except ImportError:
        HealthMonitor = None
        get_health_monitor = None


logger = logging.getLogger(__name__)


class PlatformStreamStatus(Enum):
    """Platform stream status states."""
    IDLE = "idle"
    STARTING = "starting"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class PlatformStreamState:
    """
    State for a single platform's stream.

    Maintains:
    - Current stream status
    - Platform configuration
    - Error state
    - Health metrics
    """
    platform_id: str
    platform_type: str  # youtube, twitch, custom
    status: PlatformStreamStatus = PlatformStreamStatus.IDLE
    source_url: Optional[str] = None
    rtmp_url: Optional[str] = None
    stream_key: Optional[str] = None
    video_quality: str = "720p"
    is_enabled: bool = True
    error_message: Optional[str] = None
    restart_count: int = 0
    last_restart_time: Optional[datetime] = None
    stream_start_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for Redis/API."""
        return {
            "platform_id": self.platform_id,
            "platform_type": self.platform_type,
            "status": self.status.value,
            "is_streaming": self.status == PlatformStreamStatus.STREAMING,
            "is_enabled": self.is_enabled,
            "source_url": self.source_url,
            "video_quality": self.video_quality,
            "error": self.error_message,
            "restart_count": self.restart_count,
            "stream_start_time": self.stream_start_time.isoformat() if self.stream_start_time else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_check_failures": self.health_check_failures,
            "updated_at": self.last_updated.isoformat(),
        }


class PlatformStreamer:
    """
    Manages concurrent streams to multiple platforms.

    Provides:
    - Platform isolation (independent settings per platform)
    - Concurrent streaming support
    - Centralized status monitoring
    - Redis state synchronization
    - Failure isolation (one platform doesn't affect others)
    """

    # Limits
    MAX_CONCURRENT_PLATFORMS = 10  # Maximum platforms streaming simultaneously
    MAX_RESTART_ATTEMPTS = 3  # Maximum auto-restart attempts per platform
    REDIS_STATUS_TTL = 120  # seconds
    HEALTH_CHECK_INTERVAL = 30  # seconds

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize platform streamer manager.

        Args:
            redis_url: Redis URL for status synchronization
        """
        # Platform states (in-memory)
        self._platform_states: Dict[str, PlatformStreamState] = {}
        self._platform_streamers: Dict[str, RTMPStreamer] = {}
        self._platform_tasks: Dict[str, asyncio.Task] = {}

        # Redis for cross-process sync
        self._redis: Optional[Any] = None
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Locks for thread safety
        self._lock = asyncio.Lock()

        # Health monitoring
        self._health_monitor: Optional[HealthMonitor] = None
        self._stop_event = asyncio.Event()

        self.logger = logger

    async def initialize(self) -> bool:
        """
        Initialize manager and connect to Redis.

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
                    self.logger.info("PlatformStreamer: Redis connected")
                except Exception as e:
                    self.logger.warning(f"Redis connection failed: {e}")
                    self._redis = None

            # Initialize health monitor
            if HealthMonitor:
                self._health_monitor = HealthMonitor(redis_url=self._redis_url)
                await self._health_monitor.initialize()
                await self._health_monitor.start_monitoring()
                self.logger.info("PlatformStreamer: Health monitor started")

            self.logger.info("PlatformStreamer initialized")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize PlatformStreamer: {e}")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown all platform streams."""
        self.logger.info("Shutting down PlatformStreamer...")

        # Stop health monitor
        self._stop_event.set()
        if self._health_monitor:
            await self._health_monitor.shutdown()
            self._health_monitor = None

        # Stop all platforms
        for platform_id in list(self._platform_states.keys()):
            await self.stop_platform(platform_id)

        # Close Redis
        if self._redis:
            await self._redis.close()
            self._redis = None

        self.logger.info("PlatformStreamer shutdown complete")

    def get_active_platforms_count(self) -> int:
        """Get number of currently active (streaming) platforms."""
        return sum(
            1 for state in self._platform_states.values()
            if state.status == PlatformStreamStatus.STREAMING
        )

    async def can_start_platform(self) -> bool:
        """Check if we can start another platform."""
        return self.get_active_platforms_count() < self.MAX_CONCURRENT_PLATFORMS

    async def get_or_create_state(self, platform_id: str) -> PlatformStreamState:
        """
        Get or create state for platform.

        Args:
            platform_id: Unique platform identifier

        Returns:
            PlatformStreamState instance
        """
        async with self._lock:
            if platform_id not in self._platform_states:
                self._platform_states[platform_id] = PlatformStreamState(
                    platform_id=platform_id,
                    platform_type="custom"  # Default, will be updated on add
                )
            return self._platform_states[platform_id]

    async def add_platform(
        self,
        platform_id: str,
        platform_type: str,
        rtmp_url: str,
        stream_key: str,
        video_quality: str = "720p",
        enabled: bool = True
    ) -> bool:
        """
        Add a platform destination for streaming.

        Args:
            platform_id: Unique identifier for this platform destination
            platform_type: Type of platform (youtube, twitch, custom)
            rtmp_url: RTMP server URL
            stream_key: Stream key for the platform
            video_quality: Video quality (480p, 720p, 1080p)
            enabled: Whether this platform is enabled for streaming

        Returns:
            True if platform added successfully
        """
        try:
            # Validate platform type
            platform_type = platform_type.lower()
            if platform_type not in ["youtube", "twitch", "custom"]:
                self.logger.error(f"Invalid platform type: {platform_type}")
                return False

            # Create or update state
            state = await self.get_or_create_state(platform_id)
            state.platform_type = platform_type
            state.rtmp_url = rtmp_url
            state.stream_key = stream_key
            state.video_quality = video_quality
            state.is_enabled = enabled
            state.last_updated = datetime.now(timezone.utc)

            # Create RTMPStreamer instance (but don't start yet)
            config = StreamConfig(
                platform=platform_type,
                rtmp_url=rtmp_url,
                stream_key=stream_key,
                video_quality=video_quality
            )
            streamer = RTMPStreamer(config)
            self._platform_streamers[platform_id] = streamer

            # Register with health monitor
            if self._health_monitor:
                await self._health_monitor.register_platform(
                    platform_id=platform_id,
                    health_check_func=lambda sid=platform_id: self._check_platform_health(sid),
                    recovery_callback=lambda sid=platform_id: self._attempt_platform_recovery(sid)
                )

            # Sync to Redis
            await self._sync_status_to_redis(platform_id, state)

            self.logger.info(f"Added platform {platform_id} ({platform_type})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add platform {platform_id}: {e}")
            return False

    async def remove_platform(self, platform_id: str) -> bool:
        """
        Remove a platform destination.

        Args:
            platform_id: Platform identifier to remove

        Returns:
            True if platform removed successfully
        """
        try:
            # Stop if streaming
            if platform_id in self._platform_states:
                state = self._platform_states[platform_id]
                if state.status == PlatformStreamStatus.STREAMING:
                    await self.stop_platform(platform_id)

            # Remove streamer
            if platform_id in self._platform_streamers:
                del self._platform_streamers[platform_id]

            # Remove state
            if platform_id in self._platform_states:
                del self._platform_states[platform_id]

            # Unregister from health monitor
            if self._health_monitor:
                await self._health_monitor.unregister_platform(platform_id)

            # Remove from Redis
            if self._redis:
                try:
                    await self._redis.delete(f"platform:status:{platform_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete from Redis: {e}")

            self.logger.info(f"Removed platform {platform_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove platform {platform_id}: {e}")
            return False

    async def start_platform(
        self,
        platform_id: str,
        source_url: str
    ) -> bool:
        """
        Start streaming to a platform.

        Args:
            platform_id: Platform identifier
            source_url: Source stream URL to broadcast

        Returns:
            True if stream started successfully
        """
        # Check concurrent limit
        if not await self.can_start_platform():
            self.logger.warning(
                f"Cannot start platform {platform_id}: max concurrent limit reached"
            )
            return False

        # Get state and streamer
        if platform_id not in self._platform_states:
            self.logger.error(f"Platform {platform_id} not found")
            return False

        if platform_id not in self._platform_streamers:
            self.logger.error(f"RTMPStreamer not found for platform {platform_id}")
            return False

        state = self._platform_states[platform_id]
        streamer = self._platform_streamers[platform_id]

        if not state.is_enabled:
            self.logger.warning(f"Platform {platform_id} is disabled")
            return False

        try:
            # Update status
            state.status = PlatformStreamStatus.STARTING
            state.source_url = source_url
            state.stream_start_time = None
            state.last_updated = datetime.now(timezone.utc)

            await self._sync_status_to_redis(platform_id, state)

            # Start the stream
            await streamer.start(source_url)

            # Update status to streaming
            state.status = PlatformStreamStatus.STREAMING
            state.stream_start_time = datetime.now(timezone.utc)
            state.error_message = None
            state.last_updated = datetime.now(timezone.utc)

            await self._sync_status_to_redis(platform_id, state)

            # Update health monitor
            if self._health_monitor:
                await self._health_monitor.update_platform_streaming_status(
                    platform_id=platform_id,
                    is_streaming=True,
                    uptime_seconds=0.0
                )

            self.logger.info(f"Started streaming to platform {platform_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start platform {platform_id}: {e}")
            state.status = PlatformStreamStatus.ERROR
            state.error_message = str(e)
            state.last_updated = datetime.now(timezone.utc)
            await self._sync_status_to_redis(platform_id, state)
            return False

    async def stop_platform(self, platform_id: str) -> bool:
        """
        Stop streaming to a platform.

        Args:
            platform_id: Platform identifier

        Returns:
            True if stopped successfully
        """
        if platform_id not in self._platform_states:
            self.logger.warning(f"Platform {platform_id} not found")
            return True  # Already stopped

        state = self._platform_states[platform_id]

        try:
            # Stop streamer
            if platform_id in self._platform_streamers:
                streamer = self._platform_streamers[platform_id]
                await streamer.stop()

            # Update status
            state.status = PlatformStreamStatus.STOPPED
            state.stream_start_time = None
            state.error_message = None
            state.last_updated = datetime.now(timezone.utc)

            await self._sync_status_to_redis(platform_id, state)

            # Update health monitor
            if self._health_monitor:
                await self._health_monitor.update_platform_streaming_status(
                    platform_id=platform_id,
                    is_streaming=False,
                    uptime_seconds=0.0
                )

            self.logger.info(f"Stopped streaming to platform {platform_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop platform {platform_id}: {e}")
            state.status = PlatformStreamStatus.ERROR
            state.error_message = str(e)
            await self._sync_status_to_redis(platform_id, state)
            return False

    async def start_all_platforms(self, source_url: str) -> Dict[str, bool]:
        """
        Start streaming to all enabled platforms.

        Args:
            source_url: Source stream URL to broadcast

        Returns:
            Dictionary mapping platform_id to success status
        """
        results = {}
        for platform_id, state in self._platform_states.items():
            if state.is_enabled and state.status != PlatformStreamStatus.STREAMING:
                results[platform_id] = await self.start_platform(platform_id, source_url)
        return results

    async def stop_all_platforms(self) -> Dict[str, bool]:
        """
        Stop streaming to all platforms.

        Returns:
            Dictionary mapping platform_id to success status
        """
        results = {}
        for platform_id in list(self._platform_states.keys()):
            results[platform_id] = await self.stop_platform(platform_id)
        return results

    async def get_platform_status(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status for a platform.

        Args:
            platform_id: Platform identifier

        Returns:
            Status dictionary or None if not found
        """
        if platform_id not in self._platform_states:
            return None
        state = self._platform_states[platform_id]
        return state.to_dict()

    async def get_all_platform_statuses(self) -> List[Dict[str, Any]]:
        """
        Get status for all configured platforms.

        Returns:
            List of status dictionaries
        """
        return [state.to_dict() for state in self._platform_states.values()]

    async def enable_platform(self, platform_id: str) -> bool:
        """
        Enable a platform for streaming.

        Args:
            platform_id: Platform identifier

        Returns:
            True if enabled successfully
        """
        if platform_id not in self._platform_states:
            return False

        state = self._platform_states[platform_id]
        state.is_enabled = True
        state.last_updated = datetime.now(timezone.utc)

        await self._sync_status_to_redis(platform_id, state)
        self.logger.info(f"Enabled platform {platform_id}")
        return True

    async def disable_platform(self, platform_id: str) -> bool:
        """
        Disable a platform from streaming.

        Args:
            platform_id: Platform identifier

        Returns:
            True if disabled successfully
        """
        if platform_id not in self._platform_states:
            return False

        state = self._platform_states[platform_id]

        # Stop if currently streaming
        if state.status == PlatformStreamStatus.STREAMING:
            await self.stop_platform(platform_id)

        state.is_enabled = False
        state.last_updated = datetime.now(timezone.utc)

        await self._sync_status_to_redis(platform_id, state)
        self.logger.info(f"Disabled platform {platform_id}")
        return True

    async def _check_platform_health(self, platform_id: str) -> bool:
        """
        Check if a platform's stream is healthy.

        Args:
            platform_id: Platform identifier

        Returns:
            True if platform stream is healthy
        """
        if platform_id not in self._platform_states:
            return False

        state = self._platform_states[platform_id]

        # Only check streaming platforms
        if state.status != PlatformStreamStatus.STREAMING:
            return True

        # Check if streamer is still running
        if platform_id not in self._platform_streamers:
            return False

        streamer = self._platform_streamers[platform_id]

        try:
            # Check if process is still running
            if streamer.process is None:
                return False

            # Check if process has exited
            is_healthy = streamer.process.returncode is None

            # Update state health check time
            state.last_health_check = datetime.now(timezone.utc)

            # Update streaming uptime
            if is_healthy and state.stream_start_time:
                uptime = (datetime.now(timezone.utc) - state.stream_start_time).total_seconds()
                if self._health_monitor:
                    await self._health_monitor.update_platform_streaming_status(
                        platform_id=platform_id,
                        is_streaming=True,
                        uptime_seconds=uptime
                    )

            return is_healthy

        except Exception as e:
            self.logger.warning(f"Health check error for {platform_id}: {e}")
            return False

    async def _attempt_platform_recovery(self, platform_id: str) -> bool:
        """
        Attempt to recover a failed platform stream.

        Args:
            platform_id: Platform identifier

        Returns:
            True if recovery was successful
        """
        if platform_id not in self._platform_states:
            return False

        state = self._platform_states[platform_id]

        # Check if we can attempt recovery
        if state.restart_count >= self.MAX_RESTART_ATTEMPTS:
            self.logger.warning(
                f"Platform {platform_id} exceeded max restart attempts "
                f"({self.MAX_RESTART_ATTEMPTS})"
            )
            return False

        if not state.source_url:
            self.logger.warning(f"Platform {platform_id} has no source URL for recovery")
            return False

        try:
            self.logger.info(
                f"Attempting recovery for platform {platform_id} "
                f"(attempt {state.restart_count + 1}/{self.MAX_RESTART_ATTEMPTS})"
            )

            # Update status to reconnecting
            state.status = PlatformStreamStatus.RECONNECTING
            state.last_updated = datetime.now(timezone.utc)
            await self._sync_status_to_redis(platform_id, state)

            # Stop existing streamer
            if platform_id in self._platform_streamers:
                streamer = self._platform_streamers[platform_id]
                try:
                    await streamer.stop()
                except Exception as e:
                    self.logger.warning(f"Error stopping streamer during recovery: {e}")

            # Restart the platform
            success = await self.start_platform(platform_id, state.source_url)

            if success:
                state.restart_count += 1
                state.last_restart_time = datetime.now(timezone.utc)
                self.logger.info(f"Recovery successful for platform {platform_id}")
            else:
                state.restart_count += 1
                state.error_message = "Recovery attempt failed"
                self.logger.warning(f"Recovery failed for platform {platform_id}")

            return success

        except Exception as e:
            self.logger.error(f"Recovery error for platform {platform_id}: {e}")
            state.restart_count += 1
            state.error_message = f"Recovery error: {str(e)}"
            await self._sync_status_to_redis(platform_id, state)
            return False

    async def _sync_status_to_redis(
        self,
        platform_id: str,
        state: PlatformStreamState
    ) -> None:
        """
        Sync platform status to Redis.

        Args:
            platform_id: Platform identifier
            state: Platform state to sync
        """
        if not self._redis:
            return

        try:
            key = f"platform:status:{platform_id}"
            data = state.to_dict()

            # Flatten nested dicts for Redis HSET
            flat_data = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    flat_data[k] = str(v)  # Serialize as string
                elif v is not None:
                    flat_data[k] = str(v)

            await self._redis.hset(key, mapping=flat_data)
            await self._redis.expire(key, self.REDIS_STATUS_TTL)

        except Exception as e:
            self.logger.warning(f"Failed to sync status to Redis: {e}")


# Global instance
_platform_streamer: Optional[PlatformStreamer] = None


def get_platform_streamer() -> PlatformStreamer:
    """
    Get or create global PlatformStreamer instance.

    Returns:
        PlatformStreamer instance
    """
    global _platform_streamer
    if _platform_streamer is None:
        _platform_streamer = PlatformStreamer()
    return _platform_streamer


async def initialize_platform_streamer() -> PlatformStreamer:
    """
    Initialize and return the global PlatformStreamer.

    Returns:
        Initialized PlatformStreamer instance
    """
    streamer = get_platform_streamer()
    await streamer.initialize()
    return streamer


def reset_platform_streamer() -> None:
    """Reset global streamer instance (for testing)."""
    global _platform_streamer
    _platform_streamer = None
