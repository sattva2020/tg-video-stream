"""
AyuGram Python SDK

Async Python client for AyuGram JSON-RPC API with PyTgCalls-compatible interface.
Provides session management, voice/video call operations, and stream control.

Example:
    >>> from ayugram import AyuGramClient
    >>> from pyrogram import Client
    >>>
    >>> app = Client("my_account", api_id=123, api_hash="abc")
    >>> client = AyuGramClient(app)
    >>>
    >>> await client.start()
    >>> await client.join_group_call(chat_id, stream)
    >>> await client.idle()
"""

__version__ = "0.1.0"
__author__ = "Sattva Team"
__license__ = "MIT"

# Main exports
from .client import AyuGramClient
from .exceptions import (
    AuthenticationError,
    AyuGramError,
    CallError,
    ConnectionError,
    TimeoutError,
)
from .types import AudioPiped, AudioVideoPiped, HighQualityAudio, HighQualityVideo

__all__ = [
    "__version__",
    "AyuGramClient",
    "AudioPiped",
    "AudioVideoPiped",
    "HighQualityAudio",
    "HighQualityVideo",
    "AyuGramError",
    "ConnectionError",
    "AuthenticationError",
    "CallError",
    "TimeoutError",
]
