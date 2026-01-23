"""
Broadcast Destinations API Router
Feature: 021-social-media-integration-cross-platform-broadcasting

Provides CRUD operations for broadcast destinations (links channels to platforms).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import json

from src.database import get_db
from src.models.user import User
from src.models.broadcast_destination import BroadcastDestination
from src.models.telegram import Channel, TelegramAccount
from src.models.streaming_platform import StreamingPlatform
from src.api.auth.dependencies import get_current_user
from src.schemas.streaming_platforms import (
    BroadcastDestinationCreate,
    BroadcastDestinationUpdate,
    BroadcastDestinationResponse,
    BroadcastDestinationListResponse,
    DestinationStatus
)

router = APIRouter()


@router.get("/", response_model=BroadcastDestinationListResponse)
def list_broadcast_destinations(
    channel_id: uuid.UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all broadcast destinations for the current user.

    Can filter by channel_id to get destinations for a specific channel.
    """
    # Build query - only return destinations for channels owned by the user
    query = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        TelegramAccount.user_id == current_user.id
    )

    # Filter by channel if specified
    if channel_id:
        query = query.filter(BroadcastDestination.channel_id == channel_id)

    destinations = query.all()

    destination_responses = []
    for dest in destinations:
        # Parse platform_settings if it's a JSON string
        platform_settings = None
        if dest.platform_settings:
            try:
                platform_settings = json.loads(dest.platform_settings)
            except:
                platform_settings = dest.platform_settings

        destination_dict = {
            "id": str(dest.id),
            "channel_id": str(dest.channel_id),
            "platform_id": str(dest.platform_id),
            "enabled": dest.enabled,
            "status": dest.status or "idle",
            "last_error": dest.last_error,
            "platform_settings": platform_settings,
            "custom_title": dest.custom_title,
            "custom_description": dest.custom_description,
            "created_at": dest.created_at,
            "updated_at": dest.updated_at
        }
        destination_responses.append(BroadcastDestinationResponse(**destination_dict))

    return BroadcastDestinationListResponse(
        destinations=destination_responses,
        total=len(destination_responses)
    )


@router.post("/", response_model=BroadcastDestinationResponse, status_code=status.HTTP_201_CREATED)
def create_broadcast_destination(
    destination_in: BroadcastDestinationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new broadcast destination (link a channel to a platform).

    Verifies that:
    - The channel belongs to the user
    - The platform belongs to the user
    - The combination doesn't already exist
    """
    # Verify channel belongs to user
    channel = db.query(Channel).join(TelegramAccount).filter(
        Channel.id == destination_in.channel_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found or access denied"
        )

    # Verify platform belongs to user
    platform = db.query(StreamingPlatform).filter(
        StreamingPlatform.id == destination_in.platform_id,
        StreamingPlatform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming platform not found or access denied"
        )

    # Check if combination already exists
    existing = db.query(BroadcastDestination).filter(
        BroadcastDestination.channel_id == destination_in.channel_id,
        BroadcastDestination.platform_id == destination_in.platform_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broadcast destination for this channel and platform already exists"
        )

    # Convert platform_settings dict to JSON string if provided
    platform_settings_json = None
    if destination_in.platform_settings:
        platform_settings_json = json.dumps(destination_in.platform_settings)

    new_destination = BroadcastDestination(
        channel_id=destination_in.channel_id,
        platform_id=destination_in.platform_id,
        enabled=destination_in.enabled,
        platform_settings=platform_settings_json,
        custom_title=destination_in.custom_title,
        custom_description=destination_in.custom_description,
        status="idle"
    )

    db.add(new_destination)
    db.commit()
    db.refresh(new_destination)

    return BroadcastDestinationResponse(
        id=str(new_destination.id),
        channel_id=str(new_destination.channel_id),
        platform_id=str(new_destination.platform_id),
        enabled=new_destination.enabled,
        status=new_destination.status or "idle",
        last_error=new_destination.last_error,
        platform_settings=destination_in.platform_settings,
        custom_title=new_destination.custom_title,
        custom_description=new_destination.custom_description,
        created_at=new_destination.created_at,
        updated_at=new_destination.updated_at
    )


@router.get("/{destination_id}", response_model=BroadcastDestinationResponse)
def get_broadcast_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific broadcast destination by ID.
    """
    # Verify ownership - destination must be for a channel owned by the user
    destination = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        BroadcastDestination.id == destination_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast destination not found"
        )

    # Parse platform_settings if it's a JSON string
    platform_settings = None
    if destination.platform_settings:
        try:
            platform_settings = json.loads(destination.platform_settings)
        except:
            platform_settings = destination.platform_settings

    return BroadcastDestinationResponse(
        id=str(destination.id),
        channel_id=str(destination.channel_id),
        platform_id=str(destination.platform_id),
        enabled=destination.enabled,
        status=destination.status or "idle",
        last_error=destination.last_error,
        platform_settings=platform_settings,
        custom_title=destination.custom_title,
        custom_description=destination.custom_description,
        created_at=destination.created_at,
        updated_at=destination.updated_at
    )


@router.put("/{destination_id}", response_model=BroadcastDestinationResponse)
def update_broadcast_destination(
    destination_id: uuid.UUID,
    destination_in: BroadcastDestinationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a broadcast destination.
    """
    # Verify ownership
    destination = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        BroadcastDestination.id == destination_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast destination not found"
        )

    # Update fields
    if destination_in.enabled is not None:
        destination.enabled = destination_in.enabled

    if destination_in.platform_settings is not None:
        destination.platform_settings = json.dumps(destination_in.platform_settings)

    if destination_in.custom_title is not None:
        destination.custom_title = destination_in.custom_title

    if destination_in.custom_description is not None:
        destination.custom_description = destination_in.custom_description

    db.commit()
    db.refresh(destination)

    # Parse platform_settings for response
    platform_settings = None
    if destination.platform_settings:
        try:
            platform_settings = json.loads(destination.platform_settings)
        except:
            platform_settings = destination.platform_settings

    return BroadcastDestinationResponse(
        id=str(destination.id),
        channel_id=str(destination.channel_id),
        platform_id=str(destination.platform_id),
        enabled=destination.enabled,
        status=destination.status or "idle",
        last_error=destination.last_error,
        platform_settings=platform_settings,
        custom_title=destination.custom_title,
        custom_description=destination.custom_description,
        created_at=destination.created_at,
        updated_at=destination.updated_at
    )


@router.delete("/{destination_id}", status_code=status.HTTP_200_OK)
def delete_broadcast_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a broadcast destination.
    """
    # Verify ownership
    destination = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        BroadcastDestination.id == destination_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast destination not found"
        )

    # Check if destination is currently streaming
    if destination.status == "streaming":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete destination while streaming. Stop the broadcast first."
        )

    db.delete(destination)
    db.commit()

    return {"status": "success", "message": "Broadcast destination deleted"}


@router.post("/{destination_id}/enable", status_code=status.HTTP_200_OK)
def enable_broadcast_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enable a broadcast destination.
    """
    # Verify ownership
    destination = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        BroadcastDestination.id == destination_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast destination not found"
        )

    destination.enabled = True
    db.commit()

    return {"status": "success", "message": "Broadcast destination enabled", "enabled": True}


@router.post("/{destination_id}/disable", status_code=status.HTTP_200_OK)
def disable_broadcast_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Disable a broadcast destination.
    """
    # Verify ownership
    destination = db.query(BroadcastDestination).join(Channel).join(TelegramAccount).filter(
        BroadcastDestination.id == destination_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast destination not found"
        )

    # Check if destination is currently streaming
    if destination.status == "streaming":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable destination while streaming. Stop the broadcast first."
        )

    destination.enabled = False
    db.commit()

    return {"status": "success", "message": "Broadcast destination disabled", "enabled": False}
