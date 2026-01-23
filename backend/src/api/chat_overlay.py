"""
Chat Overlay API Endpoints

API endpoints for fetching and managing chat messages displayed on stream overlay.
Part of Feature 020 (Viewer Interaction & Engagement Features).

**Purpose**: Provide REST API for chat overlay functionality
**Layer**: Interface Layer (API)
**Pattern**: Following channels.py structure
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from src.database import get_db
from src.models.user import User
from src.models.interaction import ChatMessage, ChatMessageStatus
from src.models.stream import Stream
from api.auth import get_current_user
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatMessageResponse(BaseModel):
    """Response model for chat messages."""
    id: uuid.UUID
    stream_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    telegram_user_id: Optional[int] = None
    author_name: str
    author_avatar_url: Optional[str] = None
    content: str
    message_status: str
    telegram_message_id: Optional[int] = None
    original_timestamp: Optional[datetime] = None
    is_filtered: bool
    filter_reason: Optional[str] = None
    is_flagged: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatOverlayConfig(BaseModel):
    """Configuration for chat overlay display."""
    enabled: bool = True
    max_messages: int = Field(default=50, ge=1, le=200, description="Maximum messages to display")
    display_duration_seconds: int = Field(default=30, ge=5, le=300, description="How long messages stay visible")
    font_size: int = Field(default=16, ge=10, le=32, description="Font size in pixels")
    position: str = Field(default="bottom-left", description="Position on overlay (bottom-left, bottom-right, top-left, top-right)")
    show_avatars: bool = True
    show_timestamps: bool = False
    background_opacity: float = Field(default=0.8, ge=0.0, le=1.0, description="Background opacity (0-1)")
    auto_hide: bool = Field(default=False, description="Automatically hide messages after display duration")
    filter_profanity: bool = True


class ChatMessageUpdate(BaseModel):
    """Update model for chat message status."""
    message_status: Optional[ChatMessageStatus] = None
    is_filtered: Optional[bool] = None
    filter_reason: Optional[str] = None
    is_flagged: Optional[bool] = None


# =============================================================================
# Chat Overlay Endpoints
# =============================================================================

@router.get("/messages", response_model=List[ChatMessageResponse])
def list_chat_messages(
    stream_id: Optional[uuid.UUID] = None,
    status: Optional[ChatMessageStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List chat messages for overlay display.

    **Query Parameters**:
    - stream_id: Filter by stream (optional)
    - status: Filter by status (pending, visible, hidden, flagged)
    - limit: Maximum number of messages to return (default: 50, max: 200)
    - offset: Pagination offset (default: 0)

    **Returns**: List of chat messages ordered by creation time (newest first)
    """
    # Enforce limits
    limit = min(limit, 200)

    # Build query
    query = db.query(ChatMessage)

    # Filter by stream if specified
    if stream_id:
        # Verify user has access to this stream
        stream = db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")

        # TODO: Add ownership check once Stream has user relationship

        query = query.filter(ChatMessage.stream_id == stream_id)

    # Filter by status if specified
    if status:
        query = query.filter(ChatMessage.message_status == status)

    # Exclude filtered messages unless explicitly requested
    if status != ChatMessageStatus.FLAGGED:
        query = query.filter(ChatMessage.is_filtered == False)

    # Order by creation time (newest first)
    query = query.order_by(ChatMessage.created_at.desc())

    # Apply pagination
    messages = query.offset(offset).limit(limit).all()

    return messages


@router.get("/messages/{message_id}", response_model=ChatMessageResponse)
def get_chat_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific chat message by ID.
    """
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")

    return message


@router.put("/messages/{message_id}", response_model=ChatMessageResponse)
def update_chat_message(
    message_id: uuid.UUID,
    update_data: ChatMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a chat message (status, filter, flag).

    **Use Cases**:
    - Hide inappropriate messages: set is_filtered=True
    - Mark for moderation: set is_flagged=True
    - Change display status: set message_status
    """
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")

    # Update fields if provided
    if update_data.message_status is not None:
        message.message_status = update_data.message_status

    if update_data.is_filtered is not None:
        message.is_filtered = update_data.is_filtered
        # Auto-set status to hidden if filtered
        if update_data.is_filtered and message.message_status not in (ChatMessageStatus.HIDDEN, ChatMessageStatus.FLAGGED):
            message.message_status = ChatMessageStatus.HIDDEN

    if update_data.filter_reason is not None:
        message.filter_reason = update_data.filter_reason

    if update_data.is_flagged is not None:
        message.is_flagged = update_data.is_flagged
        # Auto-set status to flagged if flagged
        if update_data.is_flagged:
            message.message_status = ChatMessageStatus.FLAGGED

    db.commit()
    db.refresh(message)

    return message


@router.delete("/messages/{message_id}")
def delete_chat_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete a chat message.
    """
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")

    db.delete(message)
    db.commit()

    return {"status": "success", "message": "Chat message deleted"}


@router.post("/messages/batch-hide")
def batch_hide_messages(
    message_ids: List[uuid.UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Hide multiple chat messages at once.

    **Use Case**: Bulk moderation - hide all messages from a specific time range or user
    """
    if not message_ids:
        raise HTTPException(status_code=400, detail="No message IDs provided")

    # Update all messages
    updated_count = db.query(ChatMessage).filter(
        ChatMessage.id.in_(message_ids)
    ).update({
        "message_status": ChatMessageStatus.HIDDEN,
        "is_filtered": True
    }, synchronize_session=False)

    db.commit()

    return {
        "status": "success",
        "updated_count": updated_count,
        "message": f"Hidden {updated_count} messages"
    }


@router.get("/config/{stream_id}")
def get_chat_overlay_config(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chat overlay configuration for a stream.

    **Note**: Currently returns default configuration.
    Future enhancement: Store per-stream configuration in database.
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # TODO: Load from database once configuration storage is implemented
    # For now, return default configuration
    return ChatOverlayConfig()


@router.put("/config/{stream_id}")
def update_chat_overlay_config(
    stream_id: uuid.UUID,
    config: ChatOverlayConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update chat overlay configuration for a stream.

    **Note**: Currently validates configuration but doesn't persist.
    Future enhancement: Store per-stream configuration in database.
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # TODO: Store configuration in database once schema is implemented
    # For now, just return the config to acknowledge receipt
    return {
        "status": "success",
        "message": "Configuration validated (not persisted yet)",
        "config": config
    }


@router.post("/messages/cleanup")
def cleanup_old_messages(
    days: int = 7,
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clean up old chat messages.

    **Query Parameters**:
    - days: Delete messages older than this many days (default: 7)
    - dry_run: If true, only count messages without deleting (default: false)

    **Returns**: Count of messages deleted (or to be deleted if dry_run)
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="Days must be at least 1")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Count messages to delete
    messages_to_delete = db.query(ChatMessage).filter(
        ChatMessage.created_at < cutoff_date
    )
    count = messages_to_delete.count()

    if dry_run:
        return {
            "status": "dry_run",
            "would_delete_count": count,
            "cutoff_date": cutoff_date
        }

    # Delete messages
    messages_to_delete.delete()
    db.commit()

    return {
        "status": "success",
        "deleted_count": count,
        "cutoff_date": cutoff_date
    }


@router.get("/stats/{stream_id}")
def get_chat_stats(
    stream_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about chat messages for a stream.
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Count total messages
    total_messages = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id
    ).count()

    # Count by status
    pending_count = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id,
        ChatMessage.message_status == ChatMessageStatus.PENDING
    ).count()

    visible_count = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id,
        ChatMessage.message_status == ChatMessageStatus.VISIBLE
    ).count()

    hidden_count = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id,
        ChatMessage.message_status == ChatMessageStatus.HIDDEN
    ).count()

    flagged_count = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id,
        ChatMessage.message_status == ChatMessageStatus.FLAGGED
    ).count()

    # Count filtered messages
    filtered_count = db.query(ChatMessage).filter(
        ChatMessage.stream_id == stream_id,
        ChatMessage.is_filtered == True
    ).count()

    return {
        "stream_id": str(stream_id),
        "total_messages": total_messages,
        "by_status": {
            "pending": pending_count,
            "visible": visible_count,
            "hidden": hidden_count,
            "flagged": flagged_count
        },
        "filtered_count": filtered_count,
        "active_messages": total_messages - filtered_count
    }
