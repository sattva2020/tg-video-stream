"""
JSON-RPC methods package.

Contains RPC method classes for call control and media streaming operations:
- CallControlMethods: start/stop/restart calls, get stream logs
- MediaStreamingMethods: playback speed, pitch, equalizer control
"""

from .call_control import CallControlMethods
from .media_streaming import MediaStreamingMethods

__all__ = [
    "CallControlMethods",
    "MediaStreamingMethods",
]
