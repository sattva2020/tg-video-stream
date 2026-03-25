"""
Stream control module for AyuGram audio/video stream manipulation.

Provides:
- Seek operations (absolute position, rewind, forward)
- Volume control
- Stream state management (position, duration, playing state)
- Playback state tracking

Integration Points:
- AyuGramClient for stream operations
- Internal state tracking for active calls
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamState:
    """Represents current stream state for a chat.

    Attributes:
        position_ms: Current playback position in milliseconds
        duration_ms: Total stream duration in milliseconds (0 if unknown)
        is_playing: Whether the stream is currently playing
        is_paused: Whether the stream is currently paused
        volume: Volume level (0.0 to 1.0)
        speed: Playback speed multiplier (0.5 to 2.0)
        updated_at: Timestamp of last state update
    """

    position_ms: int = 0
    duration_ms: int = 0
    is_playing: bool = False
    is_paused: bool = False
    volume: float = 1.0
    speed: float = 1.0
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate state values after initialization."""
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {self.volume}")
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError(f"Speed must be between 0.5 and 2.0, got {self.speed}")
        if self.position_ms < 0:
            raise ValueError(f"Position cannot be negative, got {self.position_ms}ms")
        if self.duration_ms < 0:
            raise ValueError(f"Duration cannot be negative, got {self.duration_ms}ms")


class StreamControl:
    """
    Controls stream operations for AyuGram voice/video calls.

    Manages:
    - Seek operations (absolute position, rewind, forward)
    - Volume control
    - Stream state tracking and persistence
    - Playback state management

    This class provides a simplified interface for controlling streams
    without requiring GStreamer or PyTgCalls dependencies.

    Example:
        >>> from ayugram.stream import StreamControl
        >>>
        >>> control = StreamControl()
        >>> control.seek_stream("chat_id", 30)  # Seek to 30 seconds
        >>> control.set_volume("chat_id", 0.5)  # Set volume to 50%
        >>> state = control.get_state("chat_id")
    """

    # Default constraints
    DEFAULT_VOLUME = 1.0
    MIN_VOLUME = 0.0
    MAX_VOLUME = 1.0

    DEFAULT_SPEED = 1.0
    MIN_SPEED = 0.5
    MAX_SPEED = 2.0

    def __init__(self):
        """Initialize stream control manager."""
        self.states: Dict[str, StreamState] = {}
        self.logger = logger
        self.logger.info("StreamControl initialized")

    def _ensure_state(self, chat_id: str) -> StreamState:
        """
        Ensure a state exists for the given chat_id.

        Args:
            chat_id: Chat identifier

        Returns:
            StreamState instance for the chat
        """
        if chat_id not in self.states:
            self.states[chat_id] = StreamState()
            self.logger.debug(f"Created new stream state for chat_id={chat_id}")
        return self.states[chat_id]

    def seek_stream(self, chat_id: str, position_seconds: int) -> bool:
        """
        Seek stream to specific position.

        Args:
            chat_id: Chat ID where the stream is active
            position_seconds: Target position in seconds

        Returns:
            True if seek was successful, False otherwise

        Raises:
            ValueError: If position is negative

        Example:
            >>> control.seek_stream("chat_id", 60)  # Seek to 1 minute
        """
        if position_seconds < 0:
            raise ValueError(f"Position cannot be negative, got {position_seconds}s")

        state = self._ensure_state(chat_id)
        old_position = state.position_ms
        state.position_ms = position_seconds * 1000
        state.updated_at = datetime.now()

        self.logger.info(
            f"chat_id={chat_id}: seek from {old_position // 1000}s to {position_seconds}s"
        )

        # TODO: Implement actual seek via AyuGram RPC in subsequent subtasks
        # For now, just update the state
        return True

    def rewind_stream(self, chat_id: str, seconds: int) -> bool:
        """
        Rewind stream by N seconds.

        Args:
            chat_id: Chat ID where the stream is active
            seconds: Number of seconds to rewind (must be positive)

        Returns:
            True if rewind was successful, False otherwise

        Raises:
            ValueError: If seconds is not positive

        Example:
            >>> control.rewind_stream("chat_id", 10)  # Rewind 10 seconds
        """
        if seconds <= 0:
            raise ValueError(f"Rewind duration must be positive, got {seconds}s")

        state = self._ensure_state(chat_id)
        current_position_s = state.position_ms // 1000
        new_position_s = max(0, current_position_s - seconds)

        return self.seek_stream(chat_id, new_position_s)

    def forward_stream(self, chat_id: str, seconds: int) -> bool:
        """
        Forward stream by N seconds.

        Args:
            chat_id: Chat ID where the stream is active
            seconds: Number of seconds to forward (must be positive)

        Returns:
            True if forward was successful, False otherwise

        Raises:
            ValueError: If seconds is not positive

        Example:
            >>> control.forward_stream("chat_id", 30)  # Forward 30 seconds
        """
        if seconds <= 0:
            raise ValueError(f"Forward duration must be positive, got {seconds}s")

        state = self._ensure_state(chat_id)
        current_position_s = state.position_ms // 1000
        # Cap at duration if known
        max_position = (
            (state.duration_ms // 1000) if state.duration_ms > 0 else float("inf")
        )
        new_position_s = min(max_position, current_position_s + seconds)

        return self.seek_stream(chat_id, int(new_position_s))

    def set_volume(self, chat_id: str, volume: float) -> bool:
        """
        Set volume level for stream.

        Accepts volume in two formats:
        - 0-100 range: User-friendly percentage (e.g., 50 for 50%)
        - 0.0-1.0 range: Normalized value (e.g., 0.5 for 50%)

        Args:
            chat_id: Chat ID where the stream is active
            volume: Volume level (0-100 or 0.0-1.0)

        Returns:
            True if volume was set successfully, False otherwise

        Raises:
            ValueError: If volume is out of valid range

        Example:
            >>> control.set_volume("chat_id", 50)  # Set volume to 50%
            >>> control.set_volume("chat_id", 75)  # Set volume to 75%
            >>> control.set_volume("chat_id", 0.5)  # Also works (0.0-1.0 range)
        """
        # Convert 0-100 range to 0.0-1.0 range if needed
        # Values >= 5.0 are assumed to be in 0-100 range (avoid ambiguity with 1.0-5.0)
        # Values < 5.0 are treated as 0.0-1.0 range
        if volume >= 5.0:
            # User passed 0-100 range
            if volume > 100:
                raise ValueError(
                    f"Volume must be between 0 and 100 (or 0.0 and 1.0), got {volume}"
                )
            if volume < 0:
                raise ValueError(
                    f"Volume must be between 0 and 100 (or 0.0 and 1.0), got {volume}"
                )
            volume_normalized = volume / 100.0
            volume_percent = volume
        else:
            # User passed 0.0-1.0 range
            if volume < 0:
                raise ValueError(
                    f"Volume must be between {self.MIN_VOLUME} and {self.MAX_VOLUME} (or 0-100), got {volume}"
                )
            if volume > 1.0:
                raise ValueError(
                    f"Ambiguous volume value {volume}. Use 0.0-1.0 range or >= 5 for 0-100 range"
                )
            volume_normalized = volume
            volume_percent = volume * 100

        state = self._ensure_state(chat_id)
        state.volume = volume_normalized
        state.updated_at = datetime.now()

        self.logger.info(f"chat_id={chat_id}: volume set to {volume_percent:.0f}%")

        # TODO: Implement actual volume control via AyuGram RPC in subsequent subtasks
        # For now, just update the state
        return True

    def set_speed(self, chat_id: str, speed: float) -> bool:
        """
        Set playback speed for stream.

        Args:
            chat_id: Chat ID where the stream is active
            speed: Speed multiplier (0.5 to 2.0, where 1.0 is normal speed)

        Returns:
            True if speed was set successfully, False otherwise

        Raises:
            ValueError: If speed is out of valid range

        Example:
            >>> control.set_speed("chat_id", 1.5)  # Set speed to 1.5x
        """
        if not (self.MIN_SPEED <= speed <= self.MAX_SPEED):
            raise ValueError(
                f"Speed must be between {self.MIN_SPEED} and {self.MAX_SPEED}, got {speed}"
            )

        state = self._ensure_state(chat_id)
        state.speed = speed
        state.updated_at = datetime.now()

        self.logger.info(f"chat_id={chat_id}: speed set to {speed}x")

        # TODO: Implement actual speed control via AyuGram RPC in subsequent subtasks
        # For now, just update the state
        return True

    def get_state(self, chat_id: str) -> Optional[StreamState]:
        """
        Get current stream state for chat.

        Args:
            chat_id: Chat ID to get state for

        Returns:
            StreamState if exists, None otherwise

        Example:
            >>> state = control.get_state("chat_id")
            >>> if state:
            ...     print(f"Position: {state.position_ms // 1000}s")
            ...     print(f"Volume: {state.volume * 100}%")
        """
        return self.states.get(chat_id)

    def get_position(self, chat_id: str) -> int:
        """
        Get current playback position in seconds.

        Args:
            chat_id: Chat ID to get position for

        Returns:
            Current position in seconds, 0 if no state exists

        Example:
            >>> position = control.get_position("chat_id")
            >>> print(f"Current position: {position}s")
        """
        state = self.states.get(chat_id)
        return (state.position_ms // 1000) if state else 0

    def get_volume(self, chat_id: str) -> float:
        """
        Get current volume level.

        Args:
            chat_id: Chat ID to get volume for

        Returns:
            Volume level (0.0 to 1.0), 1.0 if no state exists

        Example:
            >>> volume = control.get_volume("chat_id")
            >>> print(f"Volume: {volume * 100:.0f}%")
        """
        state = self.states.get(chat_id)
        return state.volume if state else self.DEFAULT_VOLUME

    def update_duration(self, chat_id: str, duration_ms: int) -> None:
        """
        Update duration for stream (e.g., from metadata).

        Args:
            chat_id: Chat ID to update duration for
            duration_ms: Total duration in milliseconds

        Raises:
            ValueError: If duration is negative

        Example:
            >>> control.update_duration("chat_id", 180000)  # 3 minutes
        """
        if duration_ms < 0:
            raise ValueError(f"Duration cannot be negative, got {duration_ms}ms")

        state = self._ensure_state(chat_id)
        state.duration_ms = duration_ms
        state.updated_at = datetime.now()

        self.logger.info(
            f"chat_id={chat_id}: duration updated to {duration_ms // 1000}s"
        )

    def mark_playing(self, chat_id: str, is_playing: bool = True) -> None:
        """
        Mark stream as playing or not playing.

        Args:
            chat_id: Chat ID to update state for
            is_playing: True if currently playing, False otherwise

        Example:
            >>> control.mark_playing("chat_id", True)  # Mark as playing
            >>> control.mark_playing("chat_id", False)  # Mark as stopped
        """
        state = self._ensure_state(chat_id)
        state.is_playing = is_playing
        state.is_paused = False
        state.updated_at = datetime.now()

        status = "playing" if is_playing else "stopped"
        self.logger.debug(f"chat_id={chat_id}: marked as {status}")

    def mark_paused(self, chat_id: str, is_paused: bool = True) -> None:
        """
        Mark stream as paused or not paused.

        Args:
            chat_id: Chat ID to update state for
            is_paused: True if currently paused, False otherwise

        Example:
            >>> control.mark_paused("chat_id", True)  # Mark as paused
            >>> control.mark_paused("chat_id", False)  # Mark as resumed
        """
        state = self._ensure_state(chat_id)
        state.is_paused = is_paused
        if is_paused:
            state.is_playing = False
        state.updated_at = datetime.now()

        status = "paused" if is_paused else "resumed"
        self.logger.debug(f"chat_id={chat_id}: marked as {status}")

    def clean_state(self, chat_id: str) -> None:
        """
        Remove stream state for chat (e.g., on stream end or call leave).

        Args:
            chat_id: Chat ID to clean up state for

        Example:
            >>> control.clean_state("chat_id")
        """
        if chat_id in self.states:
            del self.states[chat_id]
            self.logger.info(f"chat_id={chat_id}: stream state cleaned up")

    def has_state(self, chat_id: str) -> bool:
        """
        Check if stream state exists for chat.

        Args:
            chat_id: Chat ID to check

        Returns:
            True if state exists, False otherwise

        Example:
            >>> if control.has_state("chat_id"):
            ...     print("Stream state exists")
        """
        return chat_id in self.states

    def get_all_states(self) -> Dict[str, StreamState]:
        """
        Get all stream states.

        Returns:
            Dictionary mapping chat IDs to their StreamState

        Example:
            >>> states = control.get_all_states()
            >>> print(f"Active streams: {len(states)}")
        """
        return self.states.copy()


# Global instance (singleton pattern)
_stream_control: Optional[StreamControl] = None


def get_stream_control() -> StreamControl:
    """
    Get or create global stream control instance.

    Returns:
        StreamControl instance

    Example:
        >>> from ayugram.stream import get_stream_control
        >>>
        >>> control = get_stream_control()
        >>> control.seek_stream("chat_id", 30)
    """
    global _stream_control
    if _stream_control is None:
        _stream_control = StreamControl()
    return _stream_control


def reset_stream_control() -> None:
    """
    Reset global stream control instance (for testing).

    Example:
        >>> from ayugram.stream import reset_stream_control
        >>>
        >>> reset_stream_control()  # Clear all states
    """
    global _stream_control
    _stream_control = None


__all__ = [
    "StreamControl",
    "StreamState",
    "get_stream_control",
    "reset_stream_control",
]
