"""
Shoutouts API endpoints.

Provides REST API for managing viewer shoutouts on streams.
Created as part of Feature 020 (Viewer Interaction & Engagement Features).

Endpoints:
- POST /api/shoutouts - Trigger a new shoutout
- GET /api/shoutouts - List recent shoutouts for a stream
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid
import logging

from src.database import get_db
from src.models.user import User
from src.models.stream import Stream
from src.models.engagement import Shoutout, ShoutoutType, ShoutoutStatus
from api.auth import get_current_user
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ShoutoutCreate(BaseModel):
    """Schema for creating a new shoutout."""
    stream_id: uuid.UUID = Field(..., description="ID of the stream")
    shoutout_type: ShoutoutType = Field(..., description="Type of shoutout")
    recipient_name: str = Field(..., min_length=1, max_length=255, description="Name of the recipient")
    recipient_handle: Optional[str] = Field(None, max_length=255, description="Username/handle of recipient")
    recipient_avatar_url: Optional[str] = Field(None, max_length=500, description="URL of recipient avatar")
    title: Optional[str] = Field(None, max_length=255, description="Shoutout title")
    message: Optional[str] = Field(None, description="Shoutout message")
    display_duration: int = Field(default=10, ge=1, le=300, description="Display duration in seconds")
    priority: int = Field(default=0, ge=0, le=100, description="Display priority (higher = earlier)")
    is_pinned: bool = Field(default=False, description="Pin for display")
    trigger_type: str = Field(default="manual", max_length=50, description="Trigger type (manual, auto_follower, etc.)")
    trigger_metadata: Optional[str] = Field(None, description="Trigger metadata as JSON")


class ShoutoutResponse(BaseModel):
    """Schema for shoutout response."""
    id: uuid.UUID
    stream_id: uuid.UUID
    triggered_by_id: Optional[uuid.UUID] = None
    shoutout_type: ShoutoutType
    status: ShoutoutStatus
    recipient_name: str
    recipient_handle: Optional[str] = None
    recipient_avatar_url: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    display_duration: int
    priority: int
    is_pinned: bool
    trigger_type: str
    trigger_metadata: Optional[str] = None
    is_filtered: bool
    filter_reason: Optional[str] = None
    created_at: datetime
    displayed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/", response_model=ShoutoutResponse, status_code=status.HTTP_201_CREATED)
def trigger_shoutout(
    shoutout_in: ShoutoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger a new shoutout on a stream.

    **Authentication**: Required

    **Parameters**:
    - stream_id: ID of the stream
    - shoutout_type: Type of shoutout (new_follower, new_subscriber, donor, top_viewer, custom)
    - recipient_name: Name of the recipient being shouted out
    - recipient_handle: Username/handle (optional)
    - recipient_avatar_url: URL of avatar (optional)
    - title: Shoutout title (optional)
    - message: Shoutout message (optional)
    - display_duration: Display duration in seconds (1-300, default: 10)
    - priority: Display priority 0-100 (default: 0, higher = earlier)
    - is_pinned: Pin for display (default: false)
    - trigger_type: Trigger type (default: "manual")
    - trigger_metadata: Trigger metadata JSON (optional)

    **Returns**: Created shoutout with ID and metadata

    **Example**:
    ```json
    {
      "stream_id": "123e4567-e89b-12d3-a456-426614174000",
      "shoutout_type": "new_follower",
      "recipient_name": "John Doe",
      "recipient_handle": "@johndoe",
      "title": "Welcome new follower!",
      "message": "Thanks for following!",
      "display_duration": 15,
      "priority": 10
    }
    ```
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == shoutout_in.stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Check if stream is active
    if stream.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot trigger shoutout on stream with status '{stream.status}'. Stream must be active."
        )

    # Create new shoutout
    new_shoutout = Shoutout(
        stream_id=shoutout_in.stream_id,
        triggered_by_id=current_user.id,
        shoutout_type=shoutout_in.shoutout_type,
        status=ShoutoutStatus.PENDING,
        recipient_name=shoutout_in.recipient_name,
        recipient_handle=shoutout_in.recipient_handle,
        recipient_avatar_url=shoutout_in.recipient_avatar_url,
        title=shoutout_in.title,
        message=shoutout_in.message,
        display_duration=shoutout_in.display_duration,
        priority=shoutout_in.priority,
        is_pinned=shoutout_in.is_pinned,
        trigger_type=shoutout_in.trigger_type,
        trigger_metadata=shoutout_in.trigger_metadata,
        # Set expiration based on display duration
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=shoutout_in.display_duration)
    )

    try:
        db.add(new_shoutout)
        db.commit()
        db.refresh(new_shoutout)
        logger.info(
            f"Created shoutout {new_shoutout.id} by user {current_user.id} "
            f"on stream {shoutout_in.stream_id}: {shoutout_in.shoutout_type} for {shoutout_in.recipient_name}"
        )

        # Notify via WebSocket (async)
        import asyncio
        from src.api.websocket import notify_shoutout_triggered
        asyncio.create_task(notify_shoutout_triggered(new_shoutout))

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create shoutout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shoutout"
        )

    return new_shoutout


@router.get("/", response_model=List[ShoutoutResponse])
def list_shoutouts(
    stream_id: Optional[uuid.UUID] = Query(None, description="Filter by stream ID"),
    status_filter: Optional[ShoutoutStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of shoutouts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List recent shoutouts.

    **Authentication**: Required

    **Query Parameters**:
    - stream_id: Optional filter by stream ID
    - status_filter: Optional filter by status (pending, displayed, skipped, cancelled)
    - limit: Maximum number of shoutouts (1-100, default: 50)

    **Returns**: List of recent shoutouts ordered by priority (descending) and creation time (descending)

    **Example**:
    ```
    GET /api/shoutouts?stream_id=123e4567-e89b-12d3-a456-426614174000&limit=20
    ```
    """
    # Build query
    query = db.query(Shoutout)

    # Filter by stream if specified
    if stream_id:
        # Verify stream exists
        stream = db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )
        query = query.filter(Shoutout.stream_id == stream_id)

    # Filter by status if specified
    if status_filter:
        query = query.filter(Shoutout.status == status_filter)

    # Exclude filtered shoutouts
    query = query.filter(Shoutout.is_filtered == False)

    # Exclude expired shoutouts
    now = datetime.now(timezone.utc)
    query = query.filter(
        (Shoutout.expires_at.is_(None)) | (Shoutout.expires_at > now)
    )

    # Order by priority (higher first), then by creation time (newest first)
    query = query.order_by(Shoutout.priority.desc(), Shoutout.created_at.desc())

    # Apply limit
    query = query.limit(limit)

    # Execute query
    shoutouts = query.all()

    logger.info(
        f"Listed {len(shoutouts)} shoutouts for user {current_user.id} "
        f"(stream_id={stream_id}, status={status_filter}, limit={limit})"
    )

    return shoutouts


@router.get("/stream/{stream_id}/recent", response_model=List[ShoutoutResponse])
def get_stream_recent_shoutouts(
    stream_id: uuid.UUID,
    status_filter: Optional[ShoutoutStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of shoutouts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent shoutouts for a specific stream.

    **Authentication**: Required

    **Path Parameters**:
    - stream_id: ID of the stream

    **Query Parameters**:
    - status_filter: Optional filter by status
    - limit: Maximum number of shoutouts (1-100, default: 20)

    **Returns**: List of recent shoutouts for the stream

    **Example**:
    ```
    GET /api/shoutouts/stream/123e4567-e89b-12d3-a456-426614174000/recent?limit=20
    ```
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Build query
    query = db.query(Shoutout).filter(
        Shoutout.stream_id == stream_id,
        Shoutout.is_filtered == False
    )

    # Filter by status if specified
    if status_filter:
        query = query.filter(Shoutout.status == status_filter)

    # Exclude expired shoutouts
    now = datetime.now(timezone.utc)
    query = query.filter(
        (Shoutout.expires_at.is_(None)) | (Shoutout.expires_at > now)
    )

    # Order by priority (higher first), then by creation time (newest first)
    query = query.order_by(Shoutout.priority.desc(), Shoutout.created_at.desc())

    # Apply limit
    query = query.limit(limit)

    # Execute query
    shoutouts = query.all()

    logger.info(
        f"Retrieved {len(shoutouts)} recent shoutouts for stream {stream_id} "
        f"(status={status_filter}, limit={limit}, user={current_user.id})"
    )

    return shoutouts


@router.post("/{shoutout_id}/display", response_model=ShoutoutResponse)
def mark_shoutout_displayed(
    shoutout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a shoutout as displayed.

    **Authentication**: Required

    **Path Parameters**:
    - shoutout_id: ID of the shoutout

    **Returns**: Updated shoutout

    **Example**:
    ```
    POST /api/shoutouts/123e4567-e89b-12d3-a456-426614174000/display
    ```
    """
    shoutout = db.query(Shoutout).filter(Shoutout.id == shoutout_id).first()

    if not shoutout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoutout not found"
        )

    # Update status to displayed
    shoutout.status = ShoutoutStatus.DISPLAYED
    shoutout.displayed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(shoutout)

    logger.info(
        f"Marked shoutout {shoutout_id} as displayed by user {current_user.id}"
    )

    return shoutout


@router.post("/{shoutout_id}/skip", response_model=ShoutoutResponse)
def skip_shoutout(
    shoutout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Skip a shoutout (mark as skipped).

    **Authentication**: Required

    **Path Parameters**:
    - shoutout_id: ID of the shoutout

    **Returns**: Updated shoutout

    **Example**:
    ```
    POST /api/shoutouts/123e4567-e89b-12d3-a456-426614174000/skip
    ```
    """
    shoutout = db.query(Shoutout).filter(Shoutout.id == shoutout_id).first()

    if not shoutout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoutout not found"
        )

    # Update status to skipped
    shoutout.status = ShoutoutStatus.SKIPPED

    db.commit()
    db.refresh(shoutout)

    logger.info(
        f"Skipped shoutout {shoutout_id} by user {current_user.id}"
    )

    return shoutout


@router.delete("/{shoutout_id}", status_code=status.HTTP_200_OK)
def delete_shoutout(
    shoutout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a shoutout.

    **Authentication**: Required

    **Path Parameters**:
    - shoutout_id: ID of the shoutout

    **Returns**: Success message

    **Example**:
    ```
    DELETE /api/shoutouts/123e4567-e89b-12d3-a456-426614174000
    ```
    """
    shoutout = db.query(Shoutout).filter(Shoutout.id == shoutout_id).first()

    if not shoutout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shoutout not found"
        )

    # Verify stream ownership
    stream = db.query(Stream).filter(Stream.id == shoutout.stream_id).first()
    if stream and stream.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    db.delete(shoutout)
    db.commit()

    logger.info(
        f"Deleted shoutout {shoutout_id} by user {current_user.id}"
    )

    return {"status": "success", "message": "Shoutout deleted"}
