"""
Pydantic схемы для API.
"""
from src.schemas.telegram_auth import (
    TelegramAuthRequest,
    TelegramAuthResponse,
    TelegramLinkRequest,
    TelegramLinkResponse,
    TelegramUnlinkResponse,
    TelegramAuthError,
    UserResponse,
)

__all__ = [
    "TelegramAuthRequest",
    "TelegramAuthResponse",
    "TelegramLinkRequest",
    "TelegramLinkResponse",
    "TelegramUnlinkResponse",
    "TelegramAuthError",
    "UserResponse",
]
