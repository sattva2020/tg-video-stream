"""
Schemas for API key management (create, read, list, revoke).
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class APIKeyBase(BaseModel):
    """Base schema for API key fields."""
    name: str = Field(..., max_length=255, description="Human-readable name for the API key")
    scopes: List[str] = Field(
        ...,
        description="List of granted scopes (e.g., read:streams, write:playlists)",
        min_items=1
    )
    rate_limit: Optional[dict] = Field(
        None,
        description="Rate limit configuration (e.g., {\"requests\": 100, \"window\": 60})"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration date for the API key"
    )


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""
    pass


class APIKeyUpdate(BaseModel):
    """Schema for updating an existing API key."""
    name: Optional[str] = Field(None, max_length=255)
    scopes: Optional[List[str]] = Field(None, min_items=1)
    rate_limit: Optional[dict] = None
    is_active: Optional[bool] = Field(None, description="Enable or disable the API key")
    expires_at: Optional[datetime] = None


class APIKeyResponse(APIKeyBase):
    """Schema for API key response (includes metadata and the actual key on creation)."""
    id: UUID
    owner_id: UUID
    is_active: bool
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # The actual API key value is only included in the response after creation
    key: Optional[str] = Field(
        None,
        description="The actual API key value (only returned on creation)"
    )

    class Config:
        orm_mode = True


class APIKeyListResponse(BaseModel):
    """Schema for paginated list of API keys."""
    items: List[APIKeyResponse]
    total: int
    page: int
    page_size: int
