"""
Application Layer Errors

Этот модуль определяет ошибки уровня Application (Use Cases).
Наследуются от доменных ошибок, но специфичны для Use Case операций.
"""

from .auth_errors import AuthenticationError, RegistrationError
from .streaming_errors import StreamCreationError, BroadcastError

__all__ = [
    "AuthenticationError",
    "RegistrationError", 
    "StreamCreationError",
    "BroadcastError",
]
