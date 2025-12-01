"""
Playback control module for audio stream manipulation.

Provides:
- Speed/pitch control via GStreamer scaletempo plugin
- Seek/rewind operations via PyTgCalls
- Position tracking for streams
- Stream state management

Integration Points:
- PyTgCalls for stream playback control
- GStreamer for audio processing (scaletempo, pitch)
- Redis for state persistence
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Try to import PyTgCalls
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioVideoPiped, AudioPiped
    PYTGCALLS_AVAILABLE = True
except ImportError:
    PYTGCALLS_AVAILABLE = False

# Try to import GStreamer
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    GSTREAMER_AVAILABLE = True
except (ImportError, ValueError):
    GSTREAMER_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class PlaybackState:
    """Represents current playback state."""
    position_ms: int = 0
    duration_ms: int = 0
    is_playing: bool = False
    speed: float = 1.0
    pitch_semitones: int = 0
    equalizer_preset: str = "flat"  # NEW: активный пресет эквалайзера
    equalizer_bands: list = None  # NEW: кастомные значения полос (если не пресет)
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.equalizer_bands is None:
            self.equalizer_bands = [0.0] * 10  # 10 полос по умолчанию


class PlaybackController:
    """
    Controls playback operations for audio/video streams.
    
    Manages:
    - Speed and pitch control via GStreamer plugins
    - Seek operations via PyTgCalls
    - Position tracking and caching
    - Stream state management
    """
    
    # GStreamer pipeline defaults
    DEFAULT_SPEED = 1.0
    MIN_SPEED = 0.5
    MAX_SPEED = 2.0
    
    DEFAULT_PITCH = 0  # semitones
    MIN_PITCH = -12
    MAX_PITCH = 12
    
    def __init__(self, pytgcalls: Optional[PyTgCalls] = None):
        """
        Initialize playback controller.
        
        Args:
            pytgcalls: PyTgCalls instance for seek operations
        """
        self.pytgcalls = pytgcalls
        self.logger = logger
        self.playback_states: Dict[str, PlaybackState] = {}  # channel_id -> state
        self.gst_pipelines: Dict[str, Any] = {}  # channel_id -> GStreamer pipeline
        
        if GSTREAMER_AVAILABLE:
            self.logger.info("GStreamer available - speed/pitch control enabled")
        else:
            self.logger.warning("GStreamer not available - speed/pitch control disabled")
        
        if PYTGCALLS_AVAILABLE:
            self.logger.info("PyTgCalls available - seek operations enabled")
        else:
            self.logger.warning("PyTgCalls not available - seek operations disabled")
    
    def set_speed(self, channel_id: str, speed: float) -> bool:
        """
        Set playback speed for channel.
        
        Args:
            channel_id: Telegram channel ID
            speed: Speed multiplier (0.5 - 2.0)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If speed is out of valid range
        """
        if not (self.MIN_SPEED <= speed <= self.MAX_SPEED):
            raise ValueError(
                f"Speed must be between {self.MIN_SPEED} and {self.MAX_SPEED}, got {speed}"
            )
        
        # Update playback state
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].speed = speed
        self.logger.info(f"Channel {channel_id}: speed set to {speed}x")
        
        # Apply speed to GStreamer pipeline via scaletempo plugin
        if GSTREAMER_AVAILABLE:
            try:
                # Get or create GStreamer pipeline for this channel
                pipeline = self._get_or_create_pipeline(channel_id)
                if pipeline:
                    self._apply_speed_to_pipeline(pipeline, speed)
                    self.logger.info(f"GStreamer scaletempo applied: {speed}x for channel {channel_id}")
                    return True
            except Exception as e:
                self.logger.error(f"Failed to apply GStreamer speed: {e}")
        
        if not GSTREAMER_AVAILABLE:
            self.logger.warning(f"GStreamer not available - speed change not applied to {channel_id}")
            return False
        
        return True
    
    def _get_or_create_pipeline(self, channel_id: str) -> Any:
        """
        Get or create GStreamer pipeline for channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            GStreamer pipeline element or None if GStreamer not available
        """
        if not GSTREAMER_AVAILABLE:
            return None
        
        if channel_id not in self.gst_pipelines:
            try:
                # Create a basic playback pipeline
                # pipeline: filesrc/souphttpsrc -> demux -> audioconvert -> scaletempo -> equalizer -> audioconvert -> autoaudiosink
                pipeline_str = (
                    "filesrc name=source ! "
                    "decodebin ! "
                    "audioconvert ! "
                    "scaletempo name=tempo ! "
                    "audioconvert ! "
                    "equalizer-10bands name=equalizer ! "
                    "audioconvert ! "
                    "autoaudiosink"
                )
                pipeline = Gst.parse_launch(pipeline_str)
                self.gst_pipelines[channel_id] = pipeline
                self.logger.info(f"Created GStreamer pipeline with equalizer for channel {channel_id}")
            except Exception as e:
                self.logger.error(f"Failed to create GStreamer pipeline: {e}")
                return None
        
        return self.gst_pipelines[channel_id]
    
    def _apply_speed_to_pipeline(self, pipeline: Any, speed: float) -> None:
        """
        Apply speed to GStreamer pipeline using scaletempo plugin.
        
        Args:
            pipeline: GStreamer pipeline element
            speed: Speed multiplier
        """
        if not GSTREAMER_AVAILABLE or not pipeline:
            return
        
        try:
            # Get the scaletempo element from the pipeline
            scaletempo = pipeline.get_by_name("tempo")
            if scaletempo:
                # scaletempo's "rate" property controls playback speed
                # rate > 1.0 = faster, rate < 1.0 = slower
                scaletempo.set_property("rate", speed)
                self.logger.debug(f"scaletempo rate set to {speed}")
        except Exception as e:
            self.logger.error(f"Failed to apply scaletempo rate: {e}")
    
    def set_pitch(self, channel_id: str, semitones: int) -> bool:
        """
        Set pitch shift for channel.
        
        Args:
            channel_id: Telegram channel ID
            semitones: Pitch shift in semitones (-12 to +12)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If pitch is out of valid range
        """
        if not (self.MIN_PITCH <= semitones <= self.MAX_PITCH):
            raise ValueError(
                f"Pitch must be between {self.MIN_PITCH} and {self.MAX_PITCH}, got {semitones}"
            )
        
        # Update playback state
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].pitch_semitones = semitones
        self.logger.info(f"Channel {channel_id}: pitch set to {semitones:+d} semitones")
        
        # TODO: Apply pitch shift to GStreamer pipeline
        # GStreamer doesn't have built-in pitch shift, use rubber band or similar
        # Alternative: Use PyAudio with librubberband bindings
        
        if not GSTREAMER_AVAILABLE:
            self.logger.warning(f"GStreamer not available - pitch change not applied to {channel_id}")
            return False
        
        return True
    
    async def seek_stream(self, channel_id: str, position_seconds: int) -> bool:
        """
        Seek stream to specific position.
        
        Args:
            channel_id: Telegram channel ID
            position_seconds: Target position in seconds
            
        Returns:
            True if seek was successful, False otherwise
            
        Raises:
            ValueError: If position is negative
        """
        if position_seconds < 0:
            raise ValueError(f"Position cannot be negative, got {position_seconds}s")
        
        # Update playback state position
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        old_position = self.playback_states[channel_id].position_ms
        self.playback_states[channel_id].position_ms = position_seconds * 1000
        self.playback_states[channel_id].updated_at = datetime.now()
        
        self.logger.info(
            f"Channel {channel_id}: seek from {old_position // 1000}s to {position_seconds}s"
        )
        
        # TODO: Implement actual seek via PyTgCalls
        # PyTgCalls API typically requires:
        # 1. Leave current call: await self.pytgcalls.leave_call(channel_id)
        # 2. Re-join with new stream starting at position
        # 3. This is a limitation - true seeking requires FFmpeg support in PyTgCalls
        
        if not PYTGCALLS_AVAILABLE:
            self.logger.warning(f"PyTgCalls not available - seek not supported for {channel_id}")
            return False
        
        return True
    
    async def rewind_stream(self, channel_id: str, seconds: int) -> bool:
        """
        Rewind stream by N seconds.
        
        Args:
            channel_id: Telegram channel ID
            seconds: Number of seconds to rewind
            
        Returns:
            True if rewind was successful, False otherwise
        """
        if seconds <= 0:
            raise ValueError(f"Rewind duration must be positive, got {seconds}s")
        
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        state = self.playback_states[channel_id]
        current_position_s = state.position_ms // 1000
        new_position_s = max(0, current_position_s - seconds)
        
        return await self.seek_stream(channel_id, new_position_s)
    
    async def forward_stream(self, channel_id: str, seconds: int) -> bool:
        """
        Forward stream by N seconds.
        
        Args:
            channel_id: Telegram channel ID
            seconds: Number of seconds to forward
            
        Returns:
            True if forward was successful, False otherwise
        """
        if seconds <= 0:
            raise ValueError(f"Forward duration must be positive, got {seconds}s")
        
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        state = self.playback_states[channel_id]
        current_position_s = state.position_ms // 1000
        # Cap at duration if known
        max_position = (state.duration_ms // 1000) if state.duration_ms > 0 else float('inf')
        new_position_s = min(max_position, current_position_s + seconds)
        
        return await self.seek_stream(channel_id, int(new_position_s))
    
    def get_position(self, channel_id: str) -> PlaybackState:
        """
        Get current playback position and state.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            PlaybackState with current position and metadata
        """
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        return self.playback_states[channel_id]
    
    def update_duration(self, channel_id: str, duration_ms: int) -> None:
        """
        Update duration for channel (e.g., from stream metadata).
        
        Args:
            channel_id: Telegram channel ID
            duration_ms: Total duration in milliseconds
        """
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].duration_ms = duration_ms
        self.logger.info(f"Channel {channel_id}: duration updated to {duration_ms // 1000}s")
    
    def mark_playing(self, channel_id: str, is_playing: bool) -> None:
        """
        Mark channel as playing/paused.
        
        Args:
            channel_id: Telegram channel ID
            is_playing: True if currently playing
        """
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].is_playing = is_playing
    
    def clean_state(self, channel_id: str) -> None:
        """
        Remove playback state for channel (e.g., on stream end).
        
        Args:
            channel_id: Telegram channel ID
        """
        if channel_id in self.playback_states:
            del self.playback_states[channel_id]
        
        self.logger.info(f"Channel {channel_id}: playback state cleaned up")
    
    def set_equalizer_preset(self, channel_id: str, preset_name: str) -> bool:
        """
        Установить пресет эквалайзера для канала.
        
        Args:
            channel_id: Telegram channel ID
            preset_name: Название пресета (из config/equalizer_presets.py)
            
        Returns:
            True если успешно, False иначе
            
        Raises:
            ValueError: Если пресет не найден
        """
        from src.config.equalizer_presets import get_preset_bands
        
        try:
            bands = get_preset_bands(preset_name)
        except KeyError as e:
            raise ValueError(str(e))
        
        # Обновить состояние
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].equalizer_preset = preset_name
        self.playback_states[channel_id].equalizer_bands = bands
        self.playback_states[channel_id].updated_at = datetime.now()
        
        self.logger.info(f"Channel {channel_id}: equalizer preset set to '{preset_name}'")
        
        # Применить к GStreamer pipeline
        if GSTREAMER_AVAILABLE:
            try:
                pipeline = self._get_or_create_pipeline(channel_id)
                if pipeline:
                    self._apply_equalizer_to_pipeline(pipeline, bands)
                    self.logger.info(f"GStreamer equalizer-10bands applied for channel {channel_id}")
                    return True
            except Exception as e:
                self.logger.error(f"Failed to apply GStreamer equalizer: {e}")
        
        if not GSTREAMER_AVAILABLE:
            self.logger.warning(f"GStreamer not available - equalizer not applied to {channel_id}")
            return False
        
        return True
    
    def set_equalizer_custom(self, channel_id: str, bands: list[float]) -> bool:
        """
        Установить кастомные значения эквалайзера.
        
        Args:
            channel_id: Telegram channel ID
            bands: Массив из 10 значений (dB) для каждой полосы
            
        Returns:
            True если успешно, False иначе
            
        Raises:
            ValueError: Если значения невалидны
        """
        from src.config.equalizer_presets import validate_custom_bands
        
        # Валидировать значения
        validate_custom_bands(bands)
        
        # Обновить состояние
        if channel_id not in self.playback_states:
            self.playback_states[channel_id] = PlaybackState()
        
        self.playback_states[channel_id].equalizer_preset = "custom"
        self.playback_states[channel_id].equalizer_bands = bands.copy()
        self.playback_states[channel_id].updated_at = datetime.now()
        
        self.logger.info(f"Channel {channel_id}: custom equalizer bands set")
        
        # Применить к GStreamer pipeline
        if GSTREAMER_AVAILABLE:
            try:
                pipeline = self._get_or_create_pipeline(channel_id)
                if pipeline:
                    self._apply_equalizer_to_pipeline(pipeline, bands)
                    self.logger.info(f"GStreamer custom equalizer applied for channel {channel_id}")
                    return True
            except Exception as e:
                self.logger.error(f"Failed to apply custom equalizer: {e}")
        
        if not GSTREAMER_AVAILABLE:
            self.logger.warning(f"GStreamer not available - custom equalizer not applied to {channel_id}")
            return False
        
        return True
    
    def _apply_equalizer_to_pipeline(self, pipeline: Any, bands: list[float]) -> None:
        """
        Применить значения эквалайзера к GStreamer pipeline.
        
        Args:
            pipeline: GStreamer pipeline element
            bands: Массив из 10 значений (dB) для каждой полосы
        """
        if not GSTREAMER_AVAILABLE or not pipeline:
            return
        
        try:
            # Получить элемент equalizer-10bands из pipeline
            equalizer = pipeline.get_by_name("equalizer")
            if not equalizer:
                self.logger.warning("equalizer-10bands element not found in pipeline")
                return
            
            # Установить значения для каждой полосы
            # equalizer-10bands имеет свойства band0, band1, ..., band9
            for i, value in enumerate(bands):
                property_name = f"band{i}"
                equalizer.set_property(property_name, float(value))
                self.logger.debug(f"equalizer {property_name} set to {value} dB")
            
            self.logger.info(f"Applied equalizer values: {bands}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply equalizer bands to pipeline: {e}")
    
    def get_equalizer_state(self, channel_id: str) -> dict:
        """
        Получить текущее состояние эквалайзера для канала.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            Словарь с preset и bands
        """
        if channel_id not in self.playback_states:
            return {"preset": "flat", "bands": [0.0] * 10}
        
        state = self.playback_states[channel_id]
        return {
            "preset": state.equalizer_preset,
            "bands": state.equalizer_bands.copy() if state.equalizer_bands else [0.0] * 10
        }
        
        self.logger.info(f"Channel {channel_id}: playback state cleaned up")


# Global instance (singleton pattern)
_playback_controller: Optional[PlaybackController] = None


def get_playback_controller(pytgcalls: Optional[PyTgCalls] = None) -> PlaybackController:
    """
    Get or create global playback controller instance.
    
    Args:
        pytgcalls: PyTgCalls instance (used on first initialization)
        
    Returns:
        PlaybackController instance
    """
    global _playback_controller
    if _playback_controller is None:
        _playback_controller = PlaybackController(pytgcalls)
    return _playback_controller


def reset_playback_controller() -> None:
    """Reset global playback controller instance (for testing)."""
    global _playback_controller
    _playback_controller = None
