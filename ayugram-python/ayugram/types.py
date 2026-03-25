"""
PyTgCalls-compatible type definitions for AyuGram SDK.

This module provides type definitions that mirror PyTgCalls types,
enabling drop-in compatibility with existing PyTgCalls-based code.

Types:
    AudioPiped: Audio-only stream configuration
    AudioVideoPiped: Audio+video stream configuration
    HighQualityAudio: High-quality audio parameters
    HighQualityVideo: High-quality video parameters
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class HighQualityAudio:
    """
    High-quality audio parameters for audio streams.

    This type mirrors PyTgCalls' HighQualityAudio type and is used
    to specify high-quality audio configuration for streams.

    Example:
        >>> from ayugram.types import HighQualityAudio
        >>> audio_params = HighQualityAudio()
    """

    pass  # Parameters may be added based on AyuGram API specification


@dataclass
class HighQualityVideo:
    """
    High-quality video parameters for video streams.

    This type mirrors PyTgCalls' HighQualityVideo type and is used
    to specify high-quality video configuration for streams.

    Example:
        >>> from ayugram.types import HighQualityVideo
        >>> video_params = HighQualityVideo()
    """

    pass  # Parameters may be added based on AyuGram API specification


@dataclass
class AudioPiped:
    """
    Audio-only stream configuration.

    This type mirrors PyTgCalls' AudioPiped type for audio-only streams.
    Used when you want to stream audio without video to a Telegram voice chat.

    Args:
        data_path: Path to audio file or URL (required)
        audio_parameters: Audio quality parameters (optional)
        additional_ffmpeg_parameters: Additional FFmpeg command-line arguments (optional)

    Example:
        >>> from ayugram.types import AudioPiped, HighQualityAudio
        >>>
        >>> # Basic audio stream
        >>> stream = AudioPiped("https://example.com/audio.mp3")
        >>>
        >>> # Audio stream with high quality
        >>> stream = AudioPiped(
        ...     "https://example.com/audio.mp3",
        ...     audio_parameters=HighQualityAudio()
        ... )
        >>>
        >>> # Audio stream with custom FFmpeg parameters
        >>> stream = AudioPiped(
        ...     "https://example.com/audio.mp3",
        ...     audio_parameters=HighQualityAudio(),
        ...     additional_ffmpeg_parameters=["-re", "-bufsize", "96000k"]
        ... )
    """

    data_path: str
    audio_parameters: Optional[HighQualityAudio] = None
    additional_ffmpeg_parameters: List[str] = field(default_factory=list)


@dataclass
class AudioVideoPiped:
    """
    Audio and video stream configuration.

    This type mirrors PyTgCalls' AudioVideoPiped type for audio+video streams.
    Used when you want to stream both audio and video to a Telegram voice chat.

    Args:
        data_path: Path to video file or URL (required)
        video_parameters: Video quality parameters (optional)
        audio_parameters: Audio quality parameters (optional)
        additional_ffmpeg_parameters: Additional FFmpeg command-line arguments (optional)

    Example:
        >>> from ayugram.types import AudioVideoPiped, HighQualityVideo, HighQualityAudio
        >>>
        >>> # Basic video stream
        >>> stream = AudioVideoPiped("https://example.com/video.mp4")
        >>>
        >>> # Video stream with high quality audio and video
        >>> stream = AudioVideoPiped(
        ...     "https://example.com/video.mp4",
        ...     video_parameters=HighQualityVideo(),
        ...     audio_parameters=HighQualityAudio()
        ... )
        >>>
        >>> # Video stream with custom FFmpeg parameters
        >>> stream = AudioVideoPiped(
        ...     "https://example.com/video.mp4",
        ...     video_parameters=HighQualityVideo(),
        ...     audio_parameters=HighQualityAudio(),
        ...     additional_ffmpeg_parameters=["-re", "-preset", "fast"]
        ... )
    """

    data_path: str
    video_parameters: Optional[HighQualityVideo] = None
    audio_parameters: Optional[HighQualityAudio] = None
    additional_ffmpeg_parameters: List[str] = field(default_factory=list)


# Type alias for convenience
StreamType = Union[AudioPiped, AudioVideoPiped]
