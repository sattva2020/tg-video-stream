"""
Internal API endpoints for streamer service.
These endpoints don't require authentication and are meant for internal use only.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.telegram import Channel, TelegramAccount
from src.services.encryption import encryption_service
from pydantic import BaseModel
from typing import Optional
import uuid
import os

router = APIRouter()


class StreamerChannelConfig(BaseModel):
    """Configuration data for streamer to start a channel."""
    channel_id: str
    chat_id: int
    name: str
    session_string: str
    api_id: int
    api_hash: str
    video_quality: str
    ffmpeg_args: Optional[str] = None
    chat_username: Optional[str] = None


@router.get("/internal/streamer/channels/{channel_id}/config", response_model=StreamerChannelConfig)
def get_channel_config_for_streamer(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get channel configuration for streamer.
    This endpoint is for internal use by the streamer service.
    No authentication required - should be protected by network-level security.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get associated telegram account
    account = db.query(TelegramAccount).filter(TelegramAccount.id == channel.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    
    # Decrypt session string
    try:
        session_string = encryption_service.decrypt(account.encrypted_session) if account.encrypted_session else ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt session: {e}")
    
    # Get API credentials from environment or account settings
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    return StreamerChannelConfig(
        channel_id=str(channel.id),
        chat_id=channel.chat_id,
        name=channel.name,
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        video_quality=channel.video_quality or "720p",
        ffmpeg_args=channel.ffmpeg_args,
        chat_username=channel.chat_username,
    )
