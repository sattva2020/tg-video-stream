"""
PlaybackService for audio stream management.

Manages:
- Speed/pitch control (0.5x - 2.0x)
- Seek/rewind operations
- Stream position tracking
- Multi-channel playback isolation

Integrates with:
- GStreamer scaletempo plugin (speed without pitch change)
- PyTgCalls for actual playback control
- Redis for state persistence
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.models import PlaybackSettings


logger = logging.getLogger(__name__)


class PlaybackService:
    """Manages audio playback operations."""
    
    # Valid speed range (0.5x to 2.0x)
    MIN_SPEED = 0.5
    MAX_SPEED = 2.0
    DEFAULT_SPEED = 1.0
    
    # Valid pitch range (-12 to +12 semitones)
    MIN_PITCH = -12
    MAX_PITCH = 12
    DEFAULT_PITCH = 0
    
    def __init__(self, db_session: Session):
        """Initialize playback service."""
        self.db = db_session
        self.logger = logger
    
    @staticmethod
    def _channel_scope(channel_id: Optional[int], fallback: int) -> int:
        """Return a deterministic channel identifier for multi-channel isolation."""

        if channel_id is None:
            return int(fallback)
        return int(channel_id)

    def get_or_create_settings(self, user_id: int, channel_id: Optional[int] = None) -> PlaybackSettings:
        """
        Get existing playback settings or create new ones.
        
        Args:
            user_id: User identifier
            channel_id: Optional channel identifier (for multi-channel support)
            
        Returns:
            PlaybackSettings object
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        settings = self.db.query(PlaybackSettings).filter(
            PlaybackSettings.user_id == user_id,
            PlaybackSettings.channel_id == channel_scope,
        ).first()
        
        if not settings:
            settings = PlaybackSettings(user_id=user_id, channel_id=channel_scope)
            self.db.add(settings)
            self.db.commit()
            self.logger.info(
                "Created playback settings for user=%s, channel=%s",
                user_id,
                channel_scope,
            )
        
        return settings
    
    def set_speed(self, user_id: int, speed: float, channel_id: Optional[int] = None) -> dict:
        """
        Set playback speed for user.
        
        Args:
            user_id: User identifier
            speed: Desired speed (0.5 - 2.0)
            channel_id: Optional channel identifier
            
        Returns:
            Dict with current speed and validation info
            
        Raises:
            ValueError: If speed is outside valid range
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        # Validate speed
        if not (self.MIN_SPEED <= speed <= self.MAX_SPEED):
            raise ValueError(
                f"Speed must be between {self.MIN_SPEED} and {self.MAX_SPEED}, got {speed}"
            )
        
        # Get or create settings
        settings = self.get_or_create_settings(user_id, channel_scope)
        old_speed = settings.speed
        settings.speed = speed
        self.db.commit()
        
        self.logger.info(
            "Speed changed for user=%s channel=%s: %sx → %sx",
            user_id,
            channel_scope,
            old_speed,
            speed,
        )
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            "speed": speed,
            "pitch_correction": settings.pitch_correction,
            "message": f"Speed changed to {speed}x"
        }
    
    def set_pitch(self, user_id: int, semitones: int, channel_id: Optional[int] = None) -> dict:
        """
        Set pitch correction for playback.
        
        Args:
            user_id: User identifier
            semitones: Pitch shift in semitones (-12 to +12)
            channel_id: Optional channel identifier
            
        Returns:
            Dict with current pitch and validation info
            
        Raises:
            ValueError: If pitch is outside valid range
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        # Validate pitch
        if not (self.MIN_PITCH <= semitones <= self.MAX_PITCH):
            raise ValueError(
                f"Pitch must be between {self.MIN_PITCH} and {self.MAX_PITCH}, got {semitones}"
            )
        
        # Get or create settings
        settings = self.get_or_create_settings(user_id, channel_scope)
        settings.pitch_correction = True  # Enable pitch correction
        self.db.commit()
        
        self.logger.info(
            "Pitch set for user=%s channel=%s: %s semitones",
            user_id,
            channel_scope,
            semitones,
        )
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            "pitch_semitones": semitones,
            "pitch_correction": True,
            "message": f"Pitch shifted {semitones:+d} semitones"
        }
    
    def reset_speed(self, user_id: int, channel_id: Optional[int] = None) -> dict:
        """
        Reset playback speed to normal (1.0x).
        
        Args:
            user_id: User identifier
            channel_id: Optional channel identifier
            
        Returns:
            Dict with reset status
        """
        channel_scope = self._channel_scope(channel_id, user_id)
        settings = self.get_or_create_settings(user_id, channel_scope)
        settings.speed = self.DEFAULT_SPEED
        self.db.commit()
        
        self.logger.info("Speed reset for user=%s channel=%s", user_id, channel_scope)
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            "speed": self.DEFAULT_SPEED,
            "message": "Speed reset to 1.0x"
        }
    
    def seek(self, user_id: int, position_ms: int, channel_id: Optional[int] = None) -> dict:
        """
        Seek to specific position in track.
        
        Args:
            user_id: User identifier
            position_ms: Target position in milliseconds
            channel_id: Optional channel identifier
            
        Returns:
            Dict with seek operation details
            
        Raises:
            ValueError: If position is negative
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        if position_ms < 0:
            raise ValueError(f"Position cannot be negative, got {position_ms}ms")
        
        self.logger.info(
            "Seek requested for user=%s channel=%s to position=%sms",
            user_id,
            channel_scope,
            position_ms,
        )
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            "position_ms": position_ms,
            "message": f"Seeking to {position_ms}ms ({position_ms // 1000}s)"
        }
    
    def seek_to(self, user_id: int, position_seconds: int, channel_id: Optional[int] = None) -> int:
        """
        Seek to specific position in track (in seconds).
        
        Args:
            user_id: User identifier
            position_seconds: Target position in seconds
            channel_id: Optional channel identifier
            
        Returns:
            New position in seconds
            
        Raises:
            ValueError: If position is negative
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        if position_seconds < 0:
            raise ValueError(f"Position cannot be negative, got {position_seconds}s")
        
        self.logger.info(
            "Seek to %ss for user=%s channel=%s",
            position_seconds,
            user_id,
            channel_scope,
        )
        
        # TODO: Integration with PyTgCalls seek_stream API
        # This will be implemented in T021 (streamer/playback_control.py)
        
        return position_seconds
    
    def rewind(self, user_id: int, seconds: int, channel_id: Optional[int] = None) -> int:
        """
        Rewind track by N seconds from current position.
        
        Args:
            user_id: User identifier
            seconds: Number of seconds to rewind
            channel_id: Optional channel identifier
            
        Returns:
            New position in seconds
            
        Raises:
            ValueError: If seconds is not positive
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        if seconds <= 0:
            raise ValueError(f"Rewind duration must be positive, got {seconds}s")
        
        # Get current position (default to 0 if unknown)
        current_position = 0  # TODO: Get from stream state
        new_position = max(0, current_position - seconds)
        
        self.logger.info(
            "Rewind %ss for user=%s channel=%s: %ss → %ss",
            seconds,
            user_id,
            channel_scope,
            current_position,
            new_position,
        )
        
        return new_position
    
    def get_position(self, user_id: int, channel_id: Optional[int] = None) -> dict:
        """
        Get current playback position and duration.
        
        Args:
            user_id: User identifier
            channel_id: Optional channel identifier
            
        Returns:
            Dict with position data:
            - current_position_seconds: Current playback position
            - total_duration_seconds: Total track duration
            - is_playing: Whether stream is currently playing
        """
        channel_scope = self._channel_scope(channel_id, user_id)

        # TODO: Get actual position from PyTgCalls/GStreamer
        # For now, return placeholder data
        return {
            "channel_id": channel_scope,
            "current_position_seconds": 0,
            "total_duration_seconds": 0,
            "is_playing": False
        }
    
    def get_settings(self, user_id: int, channel_id: Optional[int] = None) -> dict:
        """
        Get current playback settings for user.
        
        Args:
            user_id: User identifier
            channel_id: Optional channel identifier
            
        Returns:
            Dict with all playback settings
        """
        channel_scope = self._channel_scope(channel_id, user_id)
        settings = self.get_or_create_settings(user_id, channel_scope)
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            "speed": settings.speed,
            "pitch_correction": settings.pitch_correction,
            "equalizer_preset": settings.equalizer_preset,
            "equalizer_custom": settings.equalizer_custom,
            "language": settings.language,
            "auto_play": settings.auto_play,
            "shuffle": settings.shuffle,
            "repeat_mode": settings.repeat_mode,
        }
    
    def get_equalizer_state(self, user_id: int, channel_id: Optional[int] = None) -> dict:
        """
        Get current equalizer settings for user.
        
        Args:
            user_id: User identifier
            channel_id: Optional channel identifier
            
        Returns:
            Dict with equalizer state:
            - preset: Current preset name (or "custom")
            - bands: Array of 10 band values in dB
        """
        from streamer.playback_control import get_playback_controller
        
        channel_scope = self._channel_scope(channel_id, user_id)
        settings = self.get_or_create_settings(user_id, channel_scope)
        controller = get_playback_controller()
        channel_id_str = str(channel_scope)
        
        # Get live state from playback controller
        live_state = controller.get_equalizer_state(channel_id_str)
        
        # Update DB settings if different
        if settings.equalizer_preset != live_state["preset"]:
            settings.equalizer_preset = live_state["preset"]
            if live_state["preset"] == "custom":
                settings.equalizer_custom = live_state["bands"]
            self.db.commit()
        
        return {
            "user_id": user_id,
            "channel_id": channel_scope,
            **live_state,
        }
    
    def set_equalizer_preset(
        self, user_id: int, preset_name: str, channel_id: Optional[int] = None
    ) -> dict:
        """
        Set equalizer preset for user.
        
        Args:
            user_id: User identifier
            preset_name: Name of preset (flat, rock, jazz, etc.)
            channel_id: Optional channel identifier
            
        Returns:
            Dict with preset info and success status
            
        Raises:
            ValueError: If preset name is invalid
        """
        from streamer.playback_control import get_playback_controller
        from src.config.equalizer_presets import EQUALIZER_PRESETS, get_preset
        
        # Validate preset
        if preset_name not in EQUALIZER_PRESETS:
            raise ValueError(
                f"Unknown preset: {preset_name}. "
                f"Available: {', '.join(EQUALIZER_PRESETS.keys())}"
            )
        
        # Apply to playback controller
        channel_scope = self._channel_scope(channel_id, user_id)

        controller = get_playback_controller()
        channel_id_str = str(channel_scope)
        success = controller.set_equalizer_preset(channel_id_str, preset_name)
        
        if not success:
            raise RuntimeError("Failed to apply equalizer preset. GStreamer may not be available.")
        
        # Update DB settings
        settings = self.get_or_create_settings(user_id, channel_scope)
        settings.equalizer_preset = preset_name
        settings.equalizer_custom = None  # Clear custom bands
        self.db.commit()
        
        preset = get_preset(preset_name)
        self.logger.info(
            "Equalizer preset '%s' set for user=%s channel=%s",
            preset_name,
            user_id,
            channel_scope,
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "channel_id": channel_scope,
            "preset": preset_name,
            "display_name": preset.display_name,
            "description": preset.description,
            "bands": preset.bands,
        }
    
    def set_equalizer_custom(
        self, user_id: int, bands: list[float], channel_id: Optional[int] = None
    ) -> dict:
        """
        Set custom equalizer bands for user.
        
        Args:
            user_id: User identifier
            bands: Array of 10 dB values for each frequency band
            channel_id: Optional channel identifier
            
        Returns:
            Dict with custom bands and success status
            
        Raises:
            ValueError: If bands array is invalid
        """
        from streamer.playback_control import get_playback_controller
        from src.config.equalizer_presets import validate_custom_bands
        
        # Validate bands
        validate_custom_bands(bands)
        
        # Apply to playback controller
        channel_scope = self._channel_scope(channel_id, user_id)

        controller = get_playback_controller()
        channel_id_str = str(channel_scope)
        success = controller.set_equalizer_custom(channel_id_str, bands)
        
        if not success:
            raise RuntimeError("Failed to apply custom equalizer. GStreamer may not be available.")
        
        # Update DB settings
        settings = self.get_or_create_settings(user_id, channel_scope)
        settings.equalizer_preset = "custom"
        settings.equalizer_custom = bands
        self.db.commit()
        
        self.logger.info(
            "Custom equalizer bands set for user=%s channel=%s",
            user_id,
            channel_scope,
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "channel_id": channel_scope,
            "preset": "custom",
            "bands": bands,
        }

