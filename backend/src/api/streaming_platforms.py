"""
Streaming Platforms API Router
Feature: 021-social-media-integration-cross-platform-broadcasting

Provides CRUD operations for streaming platforms with encrypted credentials.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from src.database import get_db
from src.models.user import User
from src.models.streaming_platform import StreamingPlatform
from src.api.auth.dependencies import get_current_user
from src.services.encryption import encryption_service
from src.schemas.streaming_platforms import (
    StreamingPlatformCreate,
    StreamingPlatformUpdate,
    StreamingPlatformResponse,
    StreamingPlatformListResponse,
    PlatformType,
    PlatformStatus
)

router = APIRouter()


@router.get("/", response_model=StreamingPlatformListResponse)
def list_streaming_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all streaming platforms for the current user.

    Returns platforms with decrypted credentials for display purposes.
    """
    platforms = db.query(StreamingPlatform).filter(
        StreamingPlatform.user_id == current_user.id
    ).all()

    platform_responses = []
    for platform in platforms:
        platform_dict = {
            "id": str(platform.id),
            "user_id": str(platform.user_id),
            "platform_type": platform.platform_type,
            "platform_name": platform.platform_name,
            "status": platform.status or "inactive",
            "last_error": platform.last_error,
            "created_at": platform.created_at,
            "updated_at": platform.updated_at
        }
        platform_responses.append(StreamingPlatformResponse(**platform_dict))

    return StreamingPlatformListResponse(
        platforms=platform_responses,
        total=len(platform_responses)
    )


@router.post("/", response_model=StreamingPlatformResponse, status_code=status.HTTP_201_CREATED)
def create_streaming_platform(
    platform_in: StreamingPlatformCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new streaming platform.

    Credentials are encrypted before storage.
    """
    # Validate platform_type
    valid_platforms = ["youtube", "twitch", "twitter", "discord", "custom_rtmp"]
    if platform_in.platform_type not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform_type. Must be one of: {', '.join(valid_platforms)}"
        )

    # Check if platform with same name already exists for user
    existing = db.query(StreamingPlatform).filter(
        StreamingPlatform.user_id == current_user.id,
        StreamingPlatform.platform_name == platform_in.platform_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform with this name already exists"
        )

    # Encrypt credentials if provided
    encrypted_creds = None
    if platform_in.encrypted_credentials:
        encrypted_creds = encryption_service.encrypt(platform_in.encrypted_credentials)

    # Encrypt stream_key if provided (separate from general credentials)
    encrypted_stream_key = None
    if platform_in.stream_key:
        encrypted_stream_key = encryption_service.encrypt(platform_in.stream_key)

    new_platform = StreamingPlatform(
        user_id=current_user.id,
        platform_type=platform_in.platform_type,
        platform_name=platform_in.platform_name,
        encrypted_credentials=encrypted_creds,
        stream_key=encrypted_stream_key,
        stream_url=platform_in.stream_url,
        status="inactive"
    )

    db.add(new_platform)
    db.commit()
    db.refresh(new_platform)

    return StreamingPlatformResponse(
        id=str(new_platform.id),
        user_id=str(new_platform.user_id),
        platform_type=new_platform.platform_type,
        platform_name=new_platform.platform_name,
        status=new_platform.status,
        last_error=new_platform.last_error,
        created_at=new_platform.created_at,
        updated_at=new_platform.updated_at
    )


@router.get("/{platform_id}", response_model=StreamingPlatformResponse)
def get_streaming_platform(
    platform_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific streaming platform by ID.

    Returns decrypted credentials for display.
    """
    platform = db.query(StreamingPlatform).filter(
        StreamingPlatform.id == platform_id,
        StreamingPlatform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming platform not found"
        )

    return StreamingPlatformResponse(
        id=str(platform.id),
        user_id=str(platform.user_id),
        platform_type=platform.platform_type,
        platform_name=platform.platform_name,
        status=platform.status,
        last_error=platform.last_error,
        created_at=platform.created_at,
        updated_at=platform.updated_at
    )


@router.put("/{platform_id}", response_model=StreamingPlatformResponse)
def update_streaming_platform(
    platform_id: uuid.UUID,
    platform_in: StreamingPlatformUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a streaming platform.

    Credentials are re-encrypted if provided.
    """
    platform = db.query(StreamingPlatform).filter(
        StreamingPlatform.id == platform_id,
        StreamingPlatform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming platform not found"
        )

    # Update fields
    if platform_in.platform_name is not None:
        # Check if new name conflicts with existing platforms
        existing = db.query(StreamingPlatform).filter(
            StreamingPlatform.user_id == current_user.id,
            StreamingPlatform.platform_name == platform_in.platform_name,
            StreamingPlatform.id != platform_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform with this name already exists"
            )

        platform.platform_name = platform_in.platform_name

    if platform_in.stream_key is not None:
        platform.stream_key = encryption_service.encrypt(platform_in.stream_key)

    if platform_in.stream_url is not None:
        platform.stream_url = platform_in.stream_url

    if platform_in.encrypted_credentials is not None:
        platform.encrypted_credentials = encryption_service.encrypt(platform_in.encrypted_credentials)

    if platform_in.status is not None:
        valid_statuses = ["inactive", "active", "error"]
        if platform_in.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        platform.status = platform_in.status

    db.commit()
    db.refresh(platform)

    return StreamingPlatformResponse(
        id=str(platform.id),
        user_id=str(platform.user_id),
        platform_type=platform.platform_type,
        platform_name=platform.platform_name,
        status=platform.status,
        last_error=platform.last_error,
        created_at=platform.created_at,
        updated_at=platform.updated_at
    )


@router.delete("/{platform_id}", status_code=status.HTTP_200_OK)
def delete_streaming_platform(
    platform_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a streaming platform.
    """
    platform = db.query(StreamingPlatform).filter(
        StreamingPlatform.id == platform_id,
        StreamingPlatform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming platform not found"
        )

    # Check if platform is in use
    from src.models.broadcast_destination import BroadcastDestination
    destinations_in_use = db.query(BroadcastDestination).filter(
        BroadcastDestination.platform_id == platform_id,
        BroadcastDestination.enabled == True
    ).count()

    if destinations_in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete platform. It is being used by {destinations_in_use} broadcast destination(s)"
        )

    db.delete(platform)
    db.commit()

    return {"status": "success", "message": "Streaming platform deleted"}


@router.post("/{platform_id}/test", status_code=status.HTTP_200_OK)
def test_streaming_platform(
    platform_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test streaming platform connection.

    This endpoint validates the credentials and connectivity for a platform.
    """
    platform = db.query(StreamingPlatform).filter(
        StreamingPlatform.id == platform_id,
        StreamingPlatform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming platform not found"
        )

    # Basic validation
    if not platform.stream_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream URL is not configured"
        )

    if not platform.stream_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream key is not configured"
        )

    # TODO: Implement actual platform-specific testing
    # For now, just return success if basic fields are present
    # This would be enhanced with platform-specific API calls

    return {
        "status": "success",
        "message": "Platform configuration is valid",
        "platform_type": platform.platform_type,
        "stream_url": platform.stream_url
    }
