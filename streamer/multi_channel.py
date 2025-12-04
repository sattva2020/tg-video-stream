"""
Multi-channel stream management module.

Manages concurrent streams across multiple Telegram channels with:
- Independent playback state per channel
- Channel-specific settings (speed, EQ, etc.)
- Automatic reconnection handling
- Status broadcasting

User Story 11 (Multi-channel Support):
Администратор может управлять несколькими Telegram каналами
одновременно с независимыми настройками воспроизведения.

Technical Implementation:
- Each channel has isolated StreamQueue and PlaybackController state
- Redis for cross-process status synchronization
- Graceful shutdown with channel state preservation
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
    from streamer.queue_manager import StreamQueue, QueueManager
    from streamer.playback_control import PlaybackController, get_playback_controller
    from streamer.radio_handler import RadioHandler
except ImportError:
    from queue_manager import StreamQueue, QueueManager
    from playback_control import PlaybackController, get_playback_controller
    from radio_handler import RadioHandler


logger = logging.getLogger(__name__)


class ChannelStatus(Enum):
    """Channel playback status states."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ChannelState:
    """
    State for a single channel's playback.
    
    Maintains:
    - Current playback status
    - Track information
    - Position tracking
    - Error state
    """
    channel_id: int
    status: ChannelStatus = ChannelStatus.IDLE
    current_track: Optional[Dict[str, Any]] = None
    position_seconds: int = 0
    duration_seconds: int = 0
    speed: float = 1.0
    equalizer_preset: str = "flat"
    queue_length: int = 0
    is_radio: bool = False
    radio_url: Optional[str] = None
    error_message: Optional[str] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for Redis/API."""
        return {
            "channel_id": self.channel_id,
            "status": self.status.value,
            "is_playing": self.status == ChannelStatus.PLAYING,
            "current_track": self.current_track,
            "position": self.position_seconds,
            "duration": self.duration_seconds,
            "position_formatted": f"{self.position_seconds // 60}:{self.position_seconds % 60:02d}",
            "duration_formatted": f"{self.duration_seconds // 60}:{self.duration_seconds % 60:02d}",
            "speed": self.speed,
            "equalizer_preset": self.equalizer_preset,
            "queue_length": self.queue_length,
            "is_radio": self.is_radio,
            "radio_url": self.radio_url,
            "error": self.error_message,
            "updated_at": self.last_updated.isoformat(),
        }


class MultiChannelManager:
    """
    Manages concurrent streams for multiple Telegram channels.
    
    Provides:
    - Channel isolation (independent settings per channel)
    - Concurrent playback support
    - Centralized status monitoring
    - Redis state synchronization
    """
    
    # Limits
    MAX_CONCURRENT_CHANNELS = 10  # Maximum channels playing simultaneously
    REDIS_STATUS_TTL = 120  # seconds
    
    def __init__(self, queue_manager: Optional[QueueManager] = None):
        """
        Initialize multi-channel manager.
        
        Args:
            queue_manager: QueueManager instance for queue operations
        """
        self.queue_manager = queue_manager or QueueManager()
        self.playback_controller = get_playback_controller()
        
        # Channel states (in-memory)
        self._channel_states: Dict[int, ChannelState] = {}
        self._channel_queues: Dict[int, StreamQueue] = {}
        self._channel_tasks: Dict[int, asyncio.Task] = {}
        
        # Redis for cross-process sync
        self._redis: Optional[Any] = None
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Locks for thread safety
        self._lock = asyncio.Lock()
        
        self.logger = logger
    
    async def initialize(self) -> bool:
        """
        Initialize manager and connect to Redis.
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize queue manager
            await self.queue_manager.init(self._redis_url)
            
            # Connect to Redis
            if aioredis:
                try:
                    self._redis = aioredis.from_url(
                        self._redis_url, 
                        decode_responses=True
                    )
                    await self._redis.ping()
                    self.logger.info("MultiChannelManager: Redis connected")
                except Exception as e:
                    self.logger.warning(f"Redis connection failed: {e}")
                    self._redis = None
            
            self.logger.info("MultiChannelManager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MultiChannelManager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all channels."""
        self.logger.info("Shutting down MultiChannelManager...")
        
        # Stop all channels
        for channel_id in list(self._channel_states.keys()):
            await self.stop_channel(channel_id)
        
        # Close Redis
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        self.logger.info("MultiChannelManager shutdown complete")
    
    def get_active_channels_count(self) -> int:
        """Get number of currently active (playing) channels."""
        return sum(
            1 for state in self._channel_states.values() 
            if state.status == ChannelStatus.PLAYING
        )
    
    async def can_start_channel(self) -> bool:
        """Check if we can start another channel."""
        return self.get_active_channels_count() < self.MAX_CONCURRENT_CHANNELS
    
    async def get_or_create_state(self, channel_id: int) -> ChannelState:
        """
        Get or create state for channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            ChannelState instance
        """
        async with self._lock:
            if channel_id not in self._channel_states:
                self._channel_states[channel_id] = ChannelState(channel_id=channel_id)
            return self._channel_states[channel_id]
    
    async def get_channel_status(self, channel_id: int) -> Dict[str, Any]:
        """
        Get current status for channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            Status dictionary
        """
        state = await self.get_or_create_state(channel_id)
        return state.to_dict()
    
    async def get_all_channel_statuses(self) -> List[Dict[str, Any]]:
        """
        Get status for all known channels.
        
        Returns:
            List of status dictionaries
        """
        return [state.to_dict() for state in self._channel_states.values()]
    
    async def start_playback(
        self,
        channel_id: int,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Start playback on channel.
        
        Args:
            channel_id: Telegram channel ID
            items: Optional list of tracks to add to queue
            
        Returns:
            True if playback started successfully
        """
        # Check concurrent limit
        if not await self.can_start_channel():
            self.logger.warning(
                f"Cannot start channel {channel_id}: max concurrent limit reached"
            )
            return False
        
        state = await self.get_or_create_state(channel_id)
        
        # Get or create queue
        if channel_id not in self._channel_queues:
            queue = StreamQueue(channel_id=channel_id)
            await queue.init_redis(self._redis_url)
            self._channel_queues[channel_id] = queue
        
        queue = self._channel_queues[channel_id]
        
        # Add items to queue if provided
        if items:
            await queue.add_items(items)
            state.queue_length = len(queue.playlist_items)
        
        # Update status
        state.status = ChannelStatus.PLAYING
        state.last_updated = datetime.now(timezone.utc)
        
        # Sync to Redis
        await self._sync_status_to_redis(channel_id, state)
        
        self.logger.info(f"Started playback on channel {channel_id}")
        return True
    
    async def stop_channel(self, channel_id: int) -> bool:
        """
        Stop playback on channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            True if stopped successfully
        """
        state = await self.get_or_create_state(channel_id)
        
        # Stop queue
        if channel_id in self._channel_queues:
            queue = self._channel_queues[channel_id]
            await queue.stop()
        
        # Cancel any running tasks
        if channel_id in self._channel_tasks:
            task = self._channel_tasks[channel_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._channel_tasks[channel_id]
        
        # Update status
        state.status = ChannelStatus.STOPPED
        state.current_track = None
        state.position_seconds = 0
        state.last_updated = datetime.now(timezone.utc)
        
        # Sync to Redis
        await self._sync_status_to_redis(channel_id, state)
        
        # Clean up playback controller state
        self.playback_controller.clean_state(str(channel_id))
        
        self.logger.info(f"Stopped playback on channel {channel_id}")
        return True
    
    async def pause_channel(self, channel_id: int) -> bool:
        """
        Pause playback on channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            True if paused successfully
        """
        state = await self.get_or_create_state(channel_id)
        
        if state.status != ChannelStatus.PLAYING:
            return False
        
        state.status = ChannelStatus.PAUSED
        state.last_updated = datetime.now(timezone.utc)
        
        # Sync to Redis
        await self._sync_status_to_redis(channel_id, state)
        
        self.playback_controller.mark_playing(str(channel_id), False)
        
        self.logger.info(f"Paused playback on channel {channel_id}")
        return True
    
    async def resume_channel(self, channel_id: int) -> bool:
        """
        Resume playback on channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            True if resumed successfully
        """
        state = await self.get_or_create_state(channel_id)
        
        if state.status != ChannelStatus.PAUSED:
            return False
        
        state.status = ChannelStatus.PLAYING
        state.last_updated = datetime.now(timezone.utc)
        
        # Sync to Redis
        await self._sync_status_to_redis(channel_id, state)
        
        self.playback_controller.mark_playing(str(channel_id), True)
        
        self.logger.info(f"Resumed playback on channel {channel_id}")
        return True
    
    async def set_channel_speed(self, channel_id: int, speed: float) -> bool:
        """
        Set playback speed for channel.
        
        Args:
            channel_id: Telegram channel ID
            speed: Speed multiplier (0.5 - 2.0)
            
        Returns:
            True if speed set successfully
        """
        try:
            self.playback_controller.set_speed(str(channel_id), speed)
            
            state = await self.get_or_create_state(channel_id)
            state.speed = speed
            state.last_updated = datetime.now(timezone.utc)
            
            await self._sync_status_to_redis(channel_id, state)
            
            self.logger.info(f"Set speed {speed}x for channel {channel_id}")
            return True
            
        except ValueError as e:
            self.logger.error(f"Invalid speed for channel {channel_id}: {e}")
            return False
    
    async def set_channel_equalizer(
        self, 
        channel_id: int, 
        preset: str
    ) -> bool:
        """
        Set equalizer preset for channel.
        
        Args:
            channel_id: Telegram channel ID
            preset: Equalizer preset name
            
        Returns:
            True if preset set successfully
        """
        try:
            self.playback_controller.set_equalizer_preset(str(channel_id), preset)
            
            state = await self.get_or_create_state(channel_id)
            state.equalizer_preset = preset
            state.last_updated = datetime.now(timezone.utc)
            
            await self._sync_status_to_redis(channel_id, state)
            
            self.logger.info(f"Set equalizer {preset} for channel {channel_id}")
            return True
            
        except ValueError as e:
            self.logger.error(f"Invalid preset for channel {channel_id}: {e}")
            return False
    
    async def update_track_info(
        self,
        channel_id: int,
        track: Dict[str, Any],
        duration_seconds: int = 0
    ) -> None:
        """
        Update current track information for channel.
        
        Args:
            channel_id: Telegram channel ID
            track: Track metadata dict
            duration_seconds: Track duration
        """
        state = await self.get_or_create_state(channel_id)
        state.current_track = track
        state.duration_seconds = duration_seconds
        state.position_seconds = 0
        state.last_updated = datetime.now(timezone.utc)
        
        # Update playback controller
        self.playback_controller.update_duration(
            str(channel_id), 
            duration_seconds * 1000
        )
        
        await self._sync_status_to_redis(channel_id, state)
    
    async def update_position(
        self, 
        channel_id: int, 
        position_seconds: int
    ) -> None:
        """
        Update current playback position.
        
        Args:
            channel_id: Telegram channel ID
            position_seconds: Current position in seconds
        """
        if channel_id in self._channel_states:
            state = self._channel_states[channel_id]
            state.position_seconds = position_seconds
            state.last_updated = datetime.now(timezone.utc)
            
            # Sync to Redis (throttled - not every update)
            # Only sync every 5 seconds to reduce Redis load
            if position_seconds % 5 == 0:
                await self._sync_status_to_redis(channel_id, state)
    
    async def start_radio(
        self,
        channel_id: int,
        stream_url: str,
        stream_name: str = "Radio"
    ) -> bool:
        """
        Start radio stream on channel.
        
        Args:
            channel_id: Telegram channel ID
            stream_url: HTTP/HTTPS stream URL
            stream_name: Display name for stream
            
        Returns:
            True if radio started successfully
        """
        if not await self.can_start_channel():
            return False
        
        state = await self.get_or_create_state(channel_id)
        state.status = ChannelStatus.BUFFERING
        state.is_radio = True
        state.radio_url = stream_url
        state.current_track = {
            "title": stream_name,
            "artist": "Live Radio",
            "is_radio": True,
        }
        state.last_updated = datetime.now(timezone.utc)
        
        await self._sync_status_to_redis(channel_id, state)
        
        self.logger.info(f"Started radio on channel {channel_id}: {stream_name}")
        return True
    
    async def on_track_end(
        self, 
        channel_id: int, 
        reason: str = "completed"
    ) -> None:
        """
        Handle track end event.
        
        Args:
            channel_id: Telegram channel ID
            reason: End reason (completed, skipped, error)
        """
        state = await self.get_or_create_state(channel_id)
        
        # Get queue for next track
        if channel_id in self._channel_queues:
            queue = self._channel_queues[channel_id]
            state.queue_length = len(queue.playlist_items)
            
            if queue.empty():
                # No more tracks
                state.status = ChannelStatus.IDLE
                state.current_track = None
            else:
                # More tracks available - will be handled by queue processing
                state.status = ChannelStatus.BUFFERING
        
        state.position_seconds = 0
        state.last_updated = datetime.now(timezone.utc)
        
        await self._sync_status_to_redis(channel_id, state)
        
        self.logger.info(f"Track ended on channel {channel_id}: {reason}")
    
    async def on_error(
        self, 
        channel_id: int, 
        error_message: str
    ) -> None:
        """
        Handle playback error.
        
        Args:
            channel_id: Telegram channel ID
            error_message: Error description
        """
        state = await self.get_or_create_state(channel_id)
        state.status = ChannelStatus.ERROR
        state.error_message = error_message
        state.last_updated = datetime.now(timezone.utc)
        
        await self._sync_status_to_redis(channel_id, state)
        
        self.logger.error(f"Playback error on channel {channel_id}: {error_message}")
    
    async def _sync_status_to_redis(
        self, 
        channel_id: int, 
        state: ChannelState
    ) -> None:
        """
        Sync channel status to Redis.
        
        Args:
            channel_id: Telegram channel ID
            state: Channel state to sync
        """
        if not self._redis:
            return
        
        try:
            key = f"channel:status:{channel_id}"
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
_multi_channel_manager: Optional[MultiChannelManager] = None


def get_multi_channel_manager() -> MultiChannelManager:
    """
    Get or create global MultiChannelManager instance.
    
    Returns:
        MultiChannelManager instance
    """
    global _multi_channel_manager
    if _multi_channel_manager is None:
        _multi_channel_manager = MultiChannelManager()
    return _multi_channel_manager


async def initialize_multi_channel_manager() -> MultiChannelManager:
    """
    Initialize and return the global MultiChannelManager.
    
    Returns:
        Initialized MultiChannelManager instance
    """
    manager = get_multi_channel_manager()
    await manager.initialize()
    return manager


def reset_multi_channel_manager() -> None:
    """Reset global manager instance (for testing)."""
    global _multi_channel_manager
    _multi_channel_manager = None
