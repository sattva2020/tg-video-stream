"""
Telegram command handlers package.

Exports all command registration functions for easy importing.
"""

from .playback import register_playback_commands
from .radio import register_radio_commands
from .scheduler import register_scheduler_commands
from .lyrics import register_lyrics_commands
from .queue import register_queue_commands
from .equalizer import register_equalizer_commands
from .channel import register_channel_commands

__all__ = [
    "register_playback_commands",
    "register_radio_commands",
    "register_scheduler_commands",
    "register_lyrics_commands",
    "register_queue_commands",
    "register_equalizer_commands",
    "register_channel_commands",
]
