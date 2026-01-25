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

# Main exports (will be implemented in subsequent subtasks)
# These imports are commented out until the modules are created
# from .client import AyuGramClient
from .types import AudioPiped, AudioVideoPiped, HighQualityAudio, HighQualityVideo
from .exceptions import (
    AyuGramError,
    ConnectionError,
    AuthenticationError,
    CallError,
    TimeoutError,
)

__all__ = [
    "__version__",
    # "AyuGramClient",  # Uncomment when implemented
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
