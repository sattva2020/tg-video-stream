# -*- coding: utf-8 -*-
"""
Модуль исключений приложения.
"""

from .audio import (
    AudioServiceError,
    StreamNotFoundError,
    ChannelNotFoundError,
    ChannelAccessDeniedError,
    RateLimitExceededError,
    PlaybackError,
    SeekError,
    RadioStreamError,
    QueueError,
    QueueFullError,
    EqualizerError,
    LyricsNotFoundError,
    ShazamRecognitionError,
    SchedulerError,
    GStreamerError,
    ConfigurationError,
    audio_exception_handler,
)

__all__ = [
    "AudioServiceError",
    "StreamNotFoundError",
    "ChannelNotFoundError",
    "ChannelAccessDeniedError",
    "RateLimitExceededError",
    "PlaybackError",
    "SeekError",
    "RadioStreamError",
    "QueueError",
    "QueueFullError",
    "EqualizerError",
    "LyricsNotFoundError",
    "ShazamRecognitionError",
    "SchedulerError",
    "GStreamerError",
    "ConfigurationError",
    "audio_exception_handler",
]
