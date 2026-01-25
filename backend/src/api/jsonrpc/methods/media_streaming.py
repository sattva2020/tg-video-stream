"""
Media streaming RPC methods for controlling playback parameters.

Provides JSON-RPC methods to control playback speed, pitch correction,
and equalizer settings using the PlaybackService.
"""
import logging
from typing import Optional

from fastapi_websocket_rpc import RpcMethodsBase

from src.services.playback_service import PlaybackService


logger = logging.getLogger(__name__)


class MediaStreamingMethods(RpcMethodsBase):
    """
    JSON-RPC methods for media streaming operations.

    This class provides methods to control audio playback parameters
    including speed, pitch correction, and equalizer settings. All
    operations are performed through the PlaybackService which manages
    user-specific playback settings with multi-channel isolation.

    All methods require user_id from JWT payload for authorization
    and data isolation.
    """

    def __init__(self, playback_service: PlaybackService, user_id: Optional[str] = None):
        """
        Initialize MediaStreamingMethods with required dependencies.

        Args:
            playback_service: PlaybackService instance for playback operations
            user_id: Optional user identifier from JWT payload for logging and service calls
        """
        super().__init__()
        self.playback_service = playback_service
        self.user_id = user_id
        self.logger = logger

    def _validate_channel_id(self, channel_id: int) -> None:
        """
        Validate channel_id parameter.

        Args:
            channel_id: Channel identifier to validate

        Raises:
            ValueError: If channel_id is not a positive integer
        """
        if not isinstance(channel_id, int) or channel_id <= 0:
            raise ValueError(f"channel_id must be a positive integer, got {channel_id}")

    def _validate_speed(self, speed: float) -> None:
        """
        Validate speed parameter.

        Args:
            speed: Speed value to validate

        Raises:
            ValueError: If speed is outside valid range
        """
        if not isinstance(speed, (int, float)):
            raise ValueError(f"speed must be numeric, got {type(speed)}")

        speed = float(speed)
        if not (0.5 <= speed <= 2.0):
            raise ValueError(
                f"Speed must be between 0.5 and 2.0, got {speed}"
            )

    def _validate_pitch(self, semitones: int) -> None:
        """
        Validate pitch semitones parameter.

        Args:
            semitones: Pitch shift in semitones to validate

        Raises:
            ValueError: If pitch is outside valid range
        """
        if not isinstance(semitones, int):
            raise ValueError(f"semitones must be integer, got {type(semitones)}")

        if not (-12 <= semitones <= 12):
            raise ValueError(
                f"Pitch must be between -12 and +12 semitones, got {semitones}"
            )

    def _validate_bands(self, bands: list) -> None:
        """
        Validate equalizer bands array.

        Args:
            bands: List of band values to validate

        Raises:
            ValueError: If bands array is invalid
        """
        if not isinstance(bands, list):
            raise ValueError(f"bands must be a list, got {type(bands)}")

        if len(bands) != 10:
            raise ValueError(f"bands must contain exactly 10 values, got {len(bands)}")

        for i, value in enumerate(bands):
            if not isinstance(value, (int, float)):
                raise ValueError(f"Band {i} must be numeric, got {type(value)}")

            if not -24 <= value <= 12:
                raise ValueError(
                    f"Band {i} value {value} out of range [-24, 12]. "
                    f"Recommended range: [-6, 6]"
                )

    async def set_playback_speed(self, channel_id: int, speed: float) -> dict:
        """
        Set playback speed for the stream.

        Adjusts the playback speed without changing pitch (using scaletempo).
        Speed values range from 0.5x (half speed) to 2.0x (double speed).

        Args:
            channel_id: Positive integer channel identifier
            speed: Playback speed multiplier (0.5 - 2.0)

        Returns:
            Dict with operation result:
                - user_id (int): User identifier
                - channel_id (int): The channel ID from request
                - speed (float): New speed value
                - pitch_correction (bool): Whether pitch correction is enabled
                - message (str): Success message

        Raises:
            ValueError: If channel_id or speed parameters are invalid
        """
        self._validate_channel_id(channel_id)
        self._validate_speed(speed)

        # Validate user_id is available
        if not self.user_id:
            raise ValueError("user_id is required for playback operations")

        self.logger.info(
            "Setting playback speed for user=%s channel=%s speed=%s",
            self.user_id,
            channel_id,
            speed,
        )

        # Call PlaybackService with user_id as first parameter
        result = self.playback_service.set_speed(
            user_id=int(self.user_id),
            speed=float(speed),
            channel_id=channel_id,
        )

        self.logger.info(
            "Playback speed set for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            result.get("message"),
        )

        return result

    async def set_pitch(self, channel_id: int, semitones: int) -> dict:
        """
        Set pitch correction for playback.

        Adjusts the pitch by a specified number of semitones without changing speed.
        Pitch range is -12 to +12 semitones (one octave down or up).

        Args:
            channel_id: Positive integer channel identifier
            semitones: Pitch shift in semitones (-12 to +12)

        Returns:
            Dict with operation result:
                - user_id (int): User identifier
                - channel_id (int): The channel ID from request
                - pitch_semitones (int): Applied pitch shift
                - pitch_correction (bool): Whether pitch correction is enabled
                - message (str): Success message

        Raises:
            ValueError: If channel_id or semitones parameters are invalid
        """
        self._validate_channel_id(channel_id)
        self._validate_pitch(semitones)

        # Validate user_id is available
        if not self.user_id:
            raise ValueError("user_id is required for playback operations")

        self.logger.info(
            "Setting pitch for user=%s channel=%s semitones=%s",
            self.user_id,
            channel_id,
            semitones,
        )

        # Call PlaybackService with user_id as first parameter
        result = self.playback_service.set_pitch(
            user_id=int(self.user_id),
            semitones=semitones,
            channel_id=channel_id,
        )

        self.logger.info(
            "Pitch set for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            result.get("message"),
        )

        return result

    async def set_equalizer_preset(self, channel_id: int, preset_name: str) -> dict:
        """
        Set equalizer preset for the stream.

        Applies a predefined equalizer preset to adjust audio frequency response.
        Available presets include: flat, rock, jazz, classical, voice, bass_boost,
        meditation, relax, new_age, ambient, sleep, nature.

        Args:
            channel_id: Positive integer channel identifier
            preset_name: Name of the preset to apply

        Returns:
            Dict with operation result:
                - success (bool): True if preset applied successfully
                - user_id (int): User identifier
                - channel_id (int): The channel ID from request
                - preset (str): Applied preset name
                - display_name (str): Human-readable preset name
                - description (str): Preset description
                - bands (list[float]): Array of 10 band values in dB

        Raises:
            ValueError: If channel_id is invalid or preset_name is unknown
            RuntimeError: If equalizer functionality is not available
        """
        self._validate_channel_id(channel_id)

        if not isinstance(preset_name, str):
            raise ValueError(f"preset_name must be a string, got {type(preset_name)}")

        # Validate user_id is available
        if not self.user_id:
            raise ValueError("user_id is required for playback operations")

        self.logger.info(
            "Setting equalizer preset for user=%s channel=%s preset=%s",
            self.user_id,
            channel_id,
            preset_name,
        )

        # Call PlaybackService with user_id as first parameter
        # This may raise ValueError for unknown preset or RuntimeError if streamer.playback_control is unavailable
        result = self.playback_service.set_equalizer_preset(
            user_id=int(self.user_id),
            preset_name=preset_name,
            channel_id=channel_id,
        )

        self.logger.info(
            "Equalizer preset '%s' applied for user=%s channel=%s",
            preset_name,
            self.user_id,
            channel_id,
        )

        return result

    async def set_equalizer_custom(self, channel_id: int, bands: list[float]) -> dict:
        """
        Set custom equalizer bands for the stream.

        Applies custom equalizer band values to adjust audio frequency response.
        Requires exactly 10 values (one per frequency band) in the range [-24, 12] dB.

        Frequency bands (Hz): 29, 59, 119, 237, 474, 947, 1889, 3770, 7523, 15011

        Args:
            channel_id: Positive integer channel identifier
            bands: Array of 10 dB values for each frequency band

        Returns:
            Dict with operation result:
                - success (bool): True if bands applied successfully
                - user_id (int): User identifier
                - channel_id (int): The channel ID from request
                - preset (str): Will be "custom"
                - bands (list[float]): Applied band values

        Raises:
            ValueError: If channel_id is invalid or bands array is malformed
            RuntimeError: If equalizer functionality is not available
        """
        self._validate_channel_id(channel_id)
        self._validate_bands(bands)

        # Validate user_id is available
        if not self.user_id:
            raise ValueError("user_id is required for playback operations")

        self.logger.info(
            "Setting custom equalizer bands for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        # Call PlaybackService with user_id as first parameter
        # This may raise RuntimeError if streamer.playback_control is unavailable
        result = self.playback_service.set_equalizer_custom(
            user_id=int(self.user_id),
            bands=[float(b) for b in bands],
            channel_id=channel_id,
        )

        self.logger.info(
            "Custom equalizer bands applied for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        return result

    async def get_stream_status(self, channel_id: int) -> dict:
        """
        Get current stream status and playback settings.

        Retrieves the current playback parameters including speed, pitch,
        equalizer settings, and other stream metadata for the channel.

        Args:
            channel_id: Positive integer channel identifier

        Returns:
            Dict with current stream status:
                - user_id (int): User identifier
                - channel_id (int): The channel ID from request
                - speed (float): Current playback speed
                - pitch_correction (bool): Whether pitch correction is enabled
                - equalizer_preset (str): Current equalizer preset name
                - equalizer_custom (list[float]|None): Custom bands if preset is "custom"
                - language (str): Audio language setting
                - auto_play (bool): Auto-play setting
                - shuffle (bool): Shuffle setting
                - repeat_mode (str): Repeat mode setting

        Raises:
            ValueError: If channel_id parameter is invalid
        """
        self._validate_channel_id(channel_id)

        # Validate user_id is available
        if not self.user_id:
            raise ValueError("user_id is required for playback operations")

        self.logger.info(
            "Fetching stream status for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        # Call PlaybackService with user_id as first parameter
        result = self.playback_service.get_settings(
            user_id=int(self.user_id),
            channel_id=channel_id,
        )

        self.logger.info(
            "Stream status retrieved for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        return result
