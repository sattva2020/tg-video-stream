"""Audio filter helpers for the Telegram streamer.

This module owns the GStreamer-specific logic for configuring scaletempo and
10-band equalizer filters. It exposes a single AudioFilterManager instance that
can be reused by playback controllers without duplicating pipeline state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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


class AudioFilterManager:
    """Manage per-channel GStreamer pipelines for speed/EQ controls."""

    PIPELINE_TEMPLATE = (
        "filesrc name=source ! "
        "decodebin ! "
        "audioconvert ! "
        "scaletempo name=tempo ! "
        "audioconvert ! "
        "equalizer-10bands name=equalizer ! "
        "audioconvert ! "
        "autoaudiosink"
    )

    def __init__(self) -> None:
        self.logger = logging.getLogger("audio_filters")
        self._pipelines: Dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return GSTREAMER_AVAILABLE

    def get_or_create_pipeline(self, channel_id: str) -> Optional[Any]:
        """Return a cached pipeline for channel or create a new one."""

        if not self.available or Gst is None:
            return None

        if channel_id not in self._pipelines:
            try:
                pipeline = Gst.parse_launch(self.PIPELINE_TEMPLATE)
                self._pipelines[channel_id] = pipeline
                self.logger.debug("Created GStreamer pipeline for channel %s", channel_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.error("Failed to create GStreamer pipeline: %s", exc)
                return None

        return self._pipelines[channel_id]

    def apply_speed(self, channel_id: str, speed: float) -> bool:
        """Apply scaletempo rate to the channel pipeline."""

        pipeline = self.get_or_create_pipeline(channel_id)
        if not pipeline:
            return False

        try:
            scaletempo = pipeline.get_by_name("tempo")
            if not scaletempo:
                self.logger.warning("scaletempo element not found for channel %s", channel_id)
                return False

            scaletempo.set_property("rate", speed)
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

        try:
            equalizer = pipeline.get_by_name("equalizer")
            if not equalizer:
                self.logger.warning("equalizer element missing for channel %s", channel_id)
                return False

            for index, value in enumerate(bands):
                equalizer.set_property(f"band{index}", float(value))
            self.logger.debug("Applied equalizer bands %s to channel %s", bands, channel_id)
            return True
        except Exception as exc:  # pragma: no cover - GStreamer runtime errors
            self.logger.error("Failed to apply equalizer: %s", exc)
            return False

    def reset_channel(self, channel_id: str) -> None:
        """Destroy pipeline for channel to free resources."""

        if channel_id not in self._pipelines or not self.available or Gst is None:
            return

        pipeline = self._pipelines.pop(channel_id, None)
        if not pipeline:
            return

        try:
            pipeline.set_state(Gst.State.NULL)
            self.logger.debug("Released GStreamer pipeline for channel %s", channel_id)
        except Exception as exc:  # pragma: no cover - cleanup best-effort
            self.logger.warning("Failed to release pipeline for channel %s: %s", channel_id, exc)


audio_filters = AudioFilterManager()


def is_gstreamer_available() -> bool:
    """Helper for callers that only need the availability flag."""

    return audio_filters.available
