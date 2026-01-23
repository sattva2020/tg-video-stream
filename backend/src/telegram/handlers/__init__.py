"""
Telegram event handlers package.

Exports all handler registration functions for easy importing.
"""

from .audio_recognition import register_audio_handlers
from .message_capture import register_message_handlers

__all__ = [
    "register_audio_handlers",
    "register_message_handlers",
]
