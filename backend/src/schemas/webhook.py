"""
Schemas for webhook subscription and event management (create, read, list, delete).
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookBase(BaseModel):
    """Base schema for webhook subscription fields."""
    url: str = Field(
        ...,
        max_length=2048,
        description="Webhook endpoint URL that will receive POST requests for events"
    )
    event_types: List[str] = Field(
        ...,
        description="List of event types to subscribe to (e.g., stream.started, viewer.milestone)",
        min_items=1
    )


class WebhookCreate(WebhookBase):
    """Schema for creating a new webhook subscription."""
    pass


class WebhookUpdate(BaseModel):
    """Schema for updating an existing webhook subscription."""
    url: Optional[str] = Field(None, max_length=2048)
    event_types: Optional[List[str]] = Field(None, min_items=1)
    is_active: Optional[bool] = Field(None, description="Enable or disable the webhook subscription")


class WebhookResponse(WebhookBase):
    """Schema for webhook response (includes metadata and the secret on creation)."""
    id: UUID
    owner_id: UUID
    is_active: bool
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    failure_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    # The secret is only included in the response after creation
    secret: Optional[str] = Field(
        None,
        description="The webhook secret for HMAC-SHA256 signature verification (only returned on creation)"
    )

    class Config:
        orm_mode = True


class WebhookListResponse(BaseModel):
    """Schema for paginated list of webhook subscriptions."""
    items: List[WebhookResponse]
    total: int
    page: int
    page_size: int


class WebhookEventResponse(BaseModel):
    """Schema for webhook event delivery record."""
    id: int
    webhook_id: UUID
    event_type: str
    event_id: Optional[str]
    status: str = Field(..., description="Delivery status: pending, success, failed, or retrying")
    attempt_number: int
    attempted_at: datetime
    response_status_code: Optional[int]
    response_body: Optional[str]
    response_headers: Optional[dict]
    should_retry: bool
    next_retry_at: Optional[datetime]
    duration_ms: Optional[int]

    class Config:
        orm_mode = True


class WebhookEventListResponse(BaseModel):
    """Schema for paginated list of webhook event delivery records."""
    items: List[WebhookEventResponse]
    total: int
    page: int
    page_size: int
