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
from src.schemas.analytics import (
    ListenerStatsResponse,
    ListenerHistoryPoint,
    ListenerHistoryResponse,
    TopTrackItem,
    TopTracksResponse,
    AnalyticsSummaryResponse,
    TrackPlayRequest,
    TrackPlayResponse,
)

__all__ = [
    "TelegramAuthRequest",
    "TelegramAuthResponse",
    "TelegramLinkRequest",
    "TelegramLinkResponse",
    "TelegramUnlinkResponse",
    "TelegramAuthError",
    "UserResponse",
    # Analytics schemas
    "ListenerStatsResponse",
    "ListenerHistoryPoint",
    "ListenerHistoryResponse",
    "TopTrackItem",
    "TopTracksResponse",
    "AnalyticsSummaryResponse",
    "TrackPlayRequest",
    "TrackPlayResponse",
]
