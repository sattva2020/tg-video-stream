"""
Application DTOs (Data Transfer Objects)

DTOs используются для передачи данных через границы слоев:
- Между Frameworks и Application
- Для изоляции внутренних структур от внешних контрактов
- Для версионирования API без изменения доменной модели

DTOs НЕ являются доменными объектами и содержат только данные.

**Phase 7**: Clean Architecture - DTO для границ слоёв
**Reference**: specs/025-clean-architecture-rules/tasks.md T067-T070
"""

# Common DTOs
from .common import (
    PaginationRequest,
    PaginationMeta,
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
    IdResponse,
    SortOrder,
)

# Auth DTOs
from .auth import (
    AuthenticateUserRequest,
    AuthenticateUserResponse,
    RegisterUserRequest,
    RegisterUserResponse,
)

# User DTOs
from .user import (
    UserDTO,
    UserSummaryDTO,
    UserRole,
    UserStatus,
    GetUserRequest,
    ListUsersRequest,
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest,
    DeleteUserRequest,
    CreateUserResponse,
    UpdateUserResponse,
    ListUsersResponse,
    ChangePasswordResponse,
)

# Stream DTOs
from .stream import (
    CreateStreamRequest,
    CreateStreamResponse,
    GetStreamStatusRequest,
)

# Playlist DTOs
from .playlist import (
    PlaylistDTO,
    PlaylistSummaryDTO,
    PlaylistStatus,
    RepeatMode,
    TrackDTO,
    TrackSummaryDTO,
    GetPlaylistRequest,
    ListPlaylistsRequest,
    CreatePlaylistRequest,
    UpdatePlaylistRequest,
    AddTracksRequest,
    RemoveTracksRequest,
    ReorderTracksRequest,
    DeletePlaylistRequest,
    CreatePlaylistResponse,
    UpdatePlaylistResponse,
    ListPlaylistsResponse,
    AddTracksResponse,
    RemoveTracksResponse,
)

__all__ = [
    # Common
    "PaginationRequest",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
    "IdResponse",
    "SortOrder",
    # Auth
    "AuthenticateUserRequest",
    "AuthenticateUserResponse",
    "RegisterUserRequest",
    "RegisterUserResponse",
    # User
    "UserDTO",
    "UserSummaryDTO",
    "UserRole",
    "UserStatus",
    "GetUserRequest",
    "ListUsersRequest",
    "CreateUserRequest",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    "DeleteUserRequest",
    "CreateUserResponse",
    "UpdateUserResponse",
    "ListUsersResponse",
    "ChangePasswordResponse",
    # Stream
    "CreateStreamRequest",
    "CreateStreamResponse",
    "GetStreamStatusRequest",
    # Playlist
    "PlaylistDTO",
    "PlaylistSummaryDTO",
    "PlaylistStatus",
    "RepeatMode",
    "TrackDTO",
    "TrackSummaryDTO",
    "GetPlaylistRequest",
    "ListPlaylistsRequest",
    "CreatePlaylistRequest",
    "UpdatePlaylistRequest",
    "AddTracksRequest",
    "RemoveTracksRequest",
    "ReorderTracksRequest",
    "DeletePlaylistRequest",
    "CreatePlaylistResponse",
    "UpdatePlaylistResponse",
    "ListPlaylistsResponse",
    "AddTracksResponse",
    "RemoveTracksResponse",
]
