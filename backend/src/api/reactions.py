"""
Reactions API endpoints.

Provides REST API for managing emoji reactions on streams.
Created as part of Feature 020 (Viewer Interaction & Engagement Features).

Endpoints:
- POST /api/reactions - Create a new emoji reaction
- GET /api/reactions - List recent reactions for a stream
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
from src.models.interaction import EmojiReaction, ReactionDisplayStatus
from api.auth import get_current_user
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ReactionCreate(BaseModel):
    """Schema for creating a new emoji reaction."""
    stream_id: uuid.UUID = Field(..., description="ID of the stream to react to")
    emoji: str = Field(..., min_length=1, max_length=100, description="Emoji to display (Unicode or shortname)")
    position_x: Optional[int] = Field(default=50, ge=0, le=100, description="X position on overlay (0-100%)")
    position_y: Optional[int] = Field(default=50, ge=0, le=100, description="Y position on overlay (0-100%)")
    scale: Optional[int] = Field(default=100, ge=10, le=200, description="Emoji size in percentage")
    animation_type: Optional[str] = Field(default="fade", max_length=50, description="Animation type (fade, pop, bounce, etc.)")
    telegram_user_id: Optional[int] = Field(default=None, description="Telegram user ID (for anonymous users)")


class ReactionResponse(BaseModel):
    """Schema for reaction response."""
    id: uuid.UUID
    stream_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    telegram_user_id: Optional[int] = None
    emoji: str
    display_status: ReactionDisplayStatus
    position_x: int
    position_y: int
    scale: int
    animation_type: Optional[str] = None
    is_filtered: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/", response_model=ReactionResponse, status_code=status.HTTP_201_CREATED)
def create_reaction(
    reaction_in: ReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new emoji reaction on a stream.

    **Authentication**: Required

    **Parameters**:
    - stream_id: ID of the stream to react to
    - emoji: Emoji character to display (e.g., "❤️", "👍", "🔥")
    - position_x, position_y: Position on overlay (0-100%, default: 50, 50)
    - scale: Size in percentage (10-200%, default: 100)
    - animation_type: Animation style (default: "fade")
    - telegram_user_id: Optional Telegram ID for anonymous users

    **Returns**: Created reaction with ID and metadata

    **Example**:
    ```json
    {
      "stream_id": "123e4567-e89b-12d3-a456-426614174000",
      "emoji": "❤️",
      "position_x": 30,
      "position_y": 40,
      "scale": 120,
      "animation_type": "pop"
    }
    ```
    """
    # Verify stream exists
    stream = db.query(Stream).filter(Stream.id == reaction_in.stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Check if stream is active
    if stream.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot react to stream with status '{stream.status}'. Stream must be active."
        )

    # Create new reaction
    new_reaction = EmojiReaction(
        stream_id=reaction_in.stream_id,
        user_id=current_user.id,
        telegram_user_id=reaction_in.telegram_user_id,
        emoji=reaction_in.emoji,
        display_status=ReactionDisplayStatus.PENDING,
        position_x=reaction_in.position_x,
        position_y=reaction_in.position_y,
        scale=reaction_in.scale,
        animation_type=reaction_in.animation_type,
        # Set expiration to 5 minutes from now (default TTL for overlay)
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )

    try:
        db.add(new_reaction)
        db.commit()
        db.refresh(new_reaction)
        logger.info(
            f"Created reaction {new_reaction.id} by user {current_user.id} "
            f"on stream {reaction_in.stream_id}: {reaction_in.emoji}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create reaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reaction"
        )

    return new_reaction


@router.get("/", response_model=List[ReactionResponse])
def list_reactions(
    stream_id: Optional[uuid.UUID] = Query(None, description="Filter by stream ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reactions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List recent emoji reactions.

    **Authentication**: Required

    **Query Parameters**:
    - stream_id: Optional filter by stream ID
    - limit: Maximum number of reactions (1-100, default: 50)

    **Returns**: List of recent reactions ordered by creation time (newest first)

    **Example**:
    ```
    GET /api/reactions?stream_id=123e4567-e89b-12d3-a456-426614174000&limit=20
    ```
    """
    # Build query
    query = db.query(EmojiReaction)

    # Filter by stream if specified
    if stream_id:
        # Verify stream exists
        stream = db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )
        query = query.filter(EmojiReaction.stream_id == stream_id)

    # Exclude filtered reactions
    query = query.filter(EmojiReaction.is_filtered == False)

    # Exclude expired reactions
    now = datetime.now(timezone.utc)
    query = query.filter(
        (EmojiReaction.expires_at.is_(None)) | (EmojiReaction.expires_at > now)
    )

    # Order by creation time (newest first)
    query = query.order_by(EmojiReaction.created_at.desc())

    # Apply limit
    query = query.limit(limit)

    # Execute query
    reactions = query.all()

    logger.info(
        f"Listed {len(reactions)} reactions for user {current_user.id} "
        f"(stream_id={stream_id}, limit={limit})"
    )

    return reactions


@router.get("/stream/{stream_id}/recent", response_model=List[ReactionResponse])
def get_stream_recent_reactions(
    stream_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of reactions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent reactions for a specific stream.

    **Authentication**: Required

    **Path Parameters**:
    - stream_id: ID of the stream

    **Query Parameters**:
    - limit: Maximum number of reactions (1-100, default: 20)

    **Returns**: List of recent reactions for the stream

    **Example**:
    ```
    GET /api/reactions/stream/123e4567-e89b-12d3-a456-426614174000/recent?limit=20
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
    query = db.query(EmojiReaction).filter(
        EmojiReaction.stream_id == stream_id,
        EmojiReaction.is_filtered == False
    )

    # Exclude expired reactions
    now = datetime.now(timezone.utc)
    query = query.filter(
        (EmojiReaction.expires_at.is_(None)) | (EmojiReaction.expires_at > now)
    )

    # Order by creation time (newest first)
    query = query.order_by(EmojiReaction.created_at.desc())

    # Apply limit
    query = query.limit(limit)

    # Execute query
    reactions = query.all()

    logger.info(
        f"Retrieved {len(reactions)} recent reactions for stream {stream_id} "
        f"(limit={limit}, user={current_user.id})"
    )

    return reactions
