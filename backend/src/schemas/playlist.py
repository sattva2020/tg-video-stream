from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
import uuid
from enum import Enum

class PlaylistEntry(BaseModel):
    """Item inside a playlist (stored in JSON)."""
    url: str
    title: str
    duration: int = 0
    type: str = "youtube"
    file_id: Optional[str] = None  # Optional reference to uploaded file

class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    color: str = "#8B5CF6"
    icon: str = "folder"
    repeat_mode: RepeatMode = RepeatMode.NONE
    repeat_count: Optional[int] = None

class PlaylistCreate(PlaylistBase):
    items: List[PlaylistEntry] = []

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    items: Optional[List[PlaylistEntry]] = None
    repeat_mode: Optional[RepeatMode] = None
    repeat_count: Optional[int] = None

class PlaylistResponse(PlaylistBase):
    id: uuid.UUID
    user_id: uuid.UUID
    items: List[PlaylistEntry]
    items_count: int
    total_duration: int
    share_code: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Playlist Template Schemas
class PlaylistTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

class PlaylistTemplateCreate(PlaylistTemplateBase):
    items: List[PlaylistEntry] = []

class PlaylistTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    items: Optional[List[PlaylistEntry]] = None

class PlaylistTemplateResponse(PlaylistTemplateBase):
    id: uuid.UUID
    user_id: uuid.UUID
    items: List[PlaylistEntry]
    items_count: int
    total_duration: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ApplyTemplateRequest(BaseModel):
    playlist_name: str
    playlist_description: Optional[str] = None
    group_id: Optional[uuid.UUID] = None
    channel_id: Optional[uuid.UUID] = None

# Smart Playlist Schemas
class SmartPlaylistCriteria(BaseModel):
    """Criteria for filtering and ordering playlist items."""
    filters: Optional[dict] = None  # e.g., {"duration_min": 0, "type": "youtube"}
    order_by: Optional[str] = "date_added"  # "date_added", "duration", "name"
    order_direction: Optional[str] = "desc"  # "asc" or "desc"
    limit: Optional[int] = None
    shuffle: Optional[bool] = False

class SmartPlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    criteria: SmartPlaylistCriteria
    auto_update: Optional[bool] = False
    auto_update_interval: Optional[int] = 24  # hours
    group_id: Optional[uuid.UUID] = None

class SmartPlaylistCreate(SmartPlaylistBase):
    pass

class SmartPlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    criteria: Optional[SmartPlaylistCriteria] = None
    auto_update: Optional[bool] = None
    auto_update_interval: Optional[int] = None
    group_id: Optional[uuid.UUID] = None

class SmartPlaylistResponse(SmartPlaylistBase):
    id: uuid.UUID
    user_id: uuid.UUID
    items_count: int
    total_duration: int
    playlist_id: Optional[uuid.UUID] = None  # ID of the generated playlist
    last_refreshed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Playlist Group Schemas
class PlaylistGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#6366F1"
    icon: str = "folder"

class PlaylistGroupCreate(PlaylistGroupBase):
    parent_id: Optional[uuid.UUID] = None
    channel_id: Optional[uuid.UUID] = None
    position: Optional[int] = 0

class PlaylistGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    position: Optional[int] = None

class PlaylistGroupResponse(PlaylistGroupBase):
    id: uuid.UUID
    user_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    channel_id: Optional[uuid.UUID] = None
    position: int
    is_expanded: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Bulk Operation Schemas
class BulkDeleteRequest(BaseModel):
    """Request schema for bulk deleting playlists."""
    playlist_ids: List[uuid.UUID]

class BulkMoveRequest(BaseModel):
    """Request schema for bulk moving playlists to a group."""
    playlist_ids: List[uuid.UUID]
    group_id: Optional[uuid.UUID] = None  # None means move to root (no group)

class BulkCopyRequest(BaseModel):
    """Request schema for bulk copying playlists."""
    playlist_ids: List[uuid.UUID]

class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations."""
    success_count: int
    failed_count: int
    errors: List[str] = []

# Repeat Mode Schemas
class RepeatMode(str, Enum):
    """Repeat mode for playlist playback."""
    NONE = "none"
    ONE = "one"
    ALL = "all"

class PlaylistRepeatSettings(BaseModel):
    """Repeat settings for a playlist."""
    mode: RepeatMode = RepeatMode.NONE
    repeat_count: Optional[int] = None  # For limited repeats (None = infinite)

class PlaylistRepeatUpdate(BaseModel):
    """Request schema for updating playlist repeat settings."""
    mode: Optional[RepeatMode] = None
    repeat_count: Optional[int] = None
