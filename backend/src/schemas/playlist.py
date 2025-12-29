from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
import uuid

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

class PlaylistCreate(PlaylistBase):
    items: List[PlaylistEntry] = []

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    items: Optional[List[PlaylistEntry]] = None

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
