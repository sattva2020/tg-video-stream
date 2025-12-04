"""
Telegram event handlers package.

Exports all handler registration functions for easy importing.
"""

from .audio_recognition import register_audio_handlers

__all__ = [
    "register_audio_handlers",
]
