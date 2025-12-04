"""Audio filter helpers for the Telegram streamer.

This module owns the GStreamer-specific logic for configuring scaletempo and
10-band equalizer filters. It exposes a single AudioFilterManager instance that
can be reused by playback controllers without duplicating pipeline state.

Performance optimizations (T077):
- Pipeline pooling and reuse
- Lazy element lookup caching
- Batch property updates
- State transition optimization
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from time import monotonic

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    if not Gst.is_initialized():
        Gst.init(None)
    GSTREAMER_AVAILABLE = True
except (ImportError, ValueError, AttributeError):
    Gst = None  # type: ignore
    GSTREAMER_AVAILABLE = False


@dataclass
class PipelineState:
    """Cached state for a GStreamer pipeline."""
    
    pipeline: Any
    scaletempo: Any = None
    equalizer: Any = None
    created_at: float = field(default_factory=monotonic)
    last_used: float = field(default_factory=monotonic)
    current_speed: float = 1.0
    current_bands: List[float] = field(default_factory=lambda: [0.0] * 10)
    
    def touch(self) -> None:
        """Update last used timestamp."""
        self.last_used = monotonic()


class AudioFilterManager:
    """Manage per-channel GStreamer pipelines for speed/EQ controls.
    
    Performance features:
    - LRU cache for pipeline elements
    - Lazy element resolution
    - Skip redundant property updates
    - Configurable pool size
    """

    # Optimized pipeline template with performance hints
    PIPELINE_TEMPLATE = (
        "filesrc name=source ! "
        "decodebin ! "
        "audioconvert dithering=0 ! "  # Disable dithering for speed
        "scaletempo name=tempo stride=30 overlap=0.2 search=14 ! "  # Optimized params
        "audioconvert dithering=0 ! "
        "equalizer-10bands name=equalizer ! "
        "audioconvert dithering=0 ! "
        "autoaudiosink"
    )
    
    # Pool configuration
    MAX_PIPELINES = 10  # Maximum concurrent pipelines
    PIPELINE_TTL = 300  # Seconds before idle pipeline cleanup

    def __init__(self) -> None:
        self.logger = logging.getLogger("audio_filters")
        self._states: OrderedDict[str, PipelineState] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "pipelines_created": 0,
            "pipelines_reused": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "property_skipped": 0,  # Updates skipped due to no change
        }

    @property
    def available(self) -> bool:
        return GSTREAMER_AVAILABLE

    @property
    def stats(self) -> Dict[str, int]:
        """Return performance statistics."""
        with self._lock:
            return dict(self._stats)

    def _cleanup_stale_pipelines(self) -> None:
        """Remove pipelines that haven't been used for TTL seconds."""
        if not self.available or Gst is None:
            return
        
        now = monotonic()
        stale = []
        
        for channel_id, state in self._states.items():
            if now - state.last_used > self.PIPELINE_TTL:
                stale.append(channel_id)
        
        for channel_id in stale:
            self._release_pipeline(channel_id)
            self.logger.debug("Cleaned up stale pipeline for channel %s", channel_id)

    def _ensure_pool_capacity(self) -> None:
        """Ensure we don't exceed MAX_PIPELINES by removing LRU entries."""
        while len(self._states) >= self.MAX_PIPELINES:
            # Remove oldest (first) item from OrderedDict
            oldest_channel = next(iter(self._states))
            self._release_pipeline(oldest_channel)
            self.logger.debug("Evicted LRU pipeline for channel %s", oldest_channel)

    def _release_pipeline(self, channel_id: str) -> None:
        """Internal: release a single pipeline."""
        state = self._states.pop(channel_id, None)
        if state and state.pipeline:
            try:
                state.pipeline.set_state(Gst.State.NULL)
            except Exception:
                pass

    def get_or_create_pipeline(self, channel_id: str) -> Optional[Any]:
        """Return a cached pipeline for channel or create a new one."""

        if not self.available or Gst is None:
            return None

        with self._lock:
            if channel_id in self._states:
                state = self._states[channel_id]
                state.touch()
                # Move to end for LRU
                self._states.move_to_end(channel_id)
                self._stats["pipelines_reused"] += 1
                self._stats["cache_hits"] += 1
                return state.pipeline

            self._stats["cache_misses"] += 1
            
            # Cleanup and ensure capacity
            self._cleanup_stale_pipelines()
            self._ensure_pool_capacity()

            try:
                pipeline = Gst.parse_launch(self.PIPELINE_TEMPLATE)
                state = PipelineState(pipeline=pipeline)
                self._states[channel_id] = state
                self._stats["pipelines_created"] += 1
                self.logger.debug("Created GStreamer pipeline for channel %s", channel_id)
                return pipeline
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.error("Failed to create GStreamer pipeline: %s", exc)
                return None

    def _get_cached_elements(self, channel_id: str) -> Tuple[Optional[Any], Optional[Any]]:
        """Get cached scaletempo and equalizer elements."""
        state = self._states.get(channel_id)
        if not state:
            return None, None
        
        # Lazy resolution with caching
        if state.scaletempo is None:
            state.scaletempo = state.pipeline.get_by_name("tempo")
        
        if state.equalizer is None:
            state.equalizer = state.pipeline.get_by_name("equalizer")
        
        return state.scaletempo, state.equalizer

    def apply_speed(self, channel_id: str, speed: float) -> bool:
        """Apply scaletempo rate to the channel pipeline."""

        pipeline = self.get_or_create_pipeline(channel_id)
        if not pipeline:
            return False

        with self._lock:
            state = self._states.get(channel_id)
            if not state:
                return False
            
            # Skip if no change (optimization)
            if abs(state.current_speed - speed) < 0.001:
                self._stats["property_skipped"] += 1
                return True

            scaletempo, _ = self._get_cached_elements(channel_id)
            if not scaletempo:
                self.logger.warning("scaletempo element not found for channel %s", channel_id)
                return False

            try:
                scaletempo.set_property("rate", speed)
                state.current_speed = speed
                state.touch()
                self.logger.debug("scaletempo rate set to %sx for channel %s", speed, channel_id)
                return True
            except Exception as exc:  # pragma: no cover - GStreamer runtime errors
                self.logger.error("Failed to apply scaletempo: %s", exc)
                return False

    def apply_equalizer(self, channel_id: str, bands: List[float]) -> bool:
        """Apply equalizer band values to the pipeline."""

        pipeline = self.get_or_create_pipeline(channel_id)
        if not pipeline:
            return False

        with self._lock:
            state = self._states.get(channel_id)
            if not state:
                return False
            
            # Check if bands have changed (optimization)
            if len(bands) == len(state.current_bands):
                if all(abs(a - b) < 0.01 for a, b in zip(bands, state.current_bands)):
                    self._stats["property_skipped"] += 1
                    return True

            _, equalizer = self._get_cached_elements(channel_id)
            if not equalizer:
                self.logger.warning("equalizer element missing for channel %s", channel_id)
                return False

            try:
                # Batch update: only update changed bands
                for index, value in enumerate(bands):
                    if index < len(state.current_bands) and abs(state.current_bands[index] - value) < 0.01:
                        continue  # Skip unchanged band
                    equalizer.set_property(f"band{index}", float(value))
                
                state.current_bands = list(bands)
                state.touch()
                self.logger.debug("Applied equalizer bands to channel %s", channel_id)
                return True
            except Exception as exc:  # pragma: no cover - GStreamer runtime errors
                self.logger.error("Failed to apply equalizer: %s", exc)
                return False

    def reset_channel(self, channel_id: str) -> None:
        """Destroy pipeline for channel to free resources."""

        if not self.available or Gst is None:
            return

        with self._lock:
            if channel_id not in self._states:
                return
            
            self._release_pipeline(channel_id)
            self.logger.debug("Released GStreamer pipeline for channel %s", channel_id)

    def cleanup_all(self) -> None:
        """Release all pipelines (for shutdown)."""
        if not self.available or Gst is None:
            return
        
        with self._lock:
            channels = list(self._states.keys())
            for channel_id in channels:
                self._release_pipeline(channel_id)
            self.logger.info("Released all %d GStreamer pipelines", len(channels))

    def get_pipeline_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a channel's pipeline state."""
        with self._lock:
            state = self._states.get(channel_id)
            if not state:
                return None
            
            return {
                "channel_id": channel_id,
                "speed": state.current_speed,
                "bands": list(state.current_bands),
                "created_at": state.created_at,
                "last_used": state.last_used,
                "age_seconds": monotonic() - state.created_at,
                "idle_seconds": monotonic() - state.last_used,
            }


audio_filters = AudioFilterManager()


def is_gstreamer_available() -> bool:
    """Helper for callers that only need the availability flag."""

    return audio_filters.available
