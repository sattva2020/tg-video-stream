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
from typing import Optional, List, Dict, Any
import uuid
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

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
    stream_type: str = "video"  # 'audio' or 'video'
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
        stream_type=channel.stream_type or "video",
        ffmpeg_args=channel.ffmpeg_args,
        chat_username=channel.chat_username,
    )


class DialogInfo(BaseModel):
    """Information about a Telegram dialog."""
    id: int
    title: str
    type: str  # 'private', 'bot', 'group', 'supergroup', 'channel'


class SessionInfoResponse(BaseModel):
    """Session diagnostic information."""
    channel_id: str
    session_valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone: Optional[str] = None
    dialogs_count: Optional[int] = None
    target_chat_found: bool = False
    target_chat_id: Optional[int] = None
    recent_dialogs: List[DialogInfo] = []
    error: Optional[str] = None


async def diagnose_session(session_string: str, api_id: int, api_hash: str, target_chat_id: int) -> Dict[str, Any]:
    """
    Create temporary Pyrogram client and diagnose session.
    Returns diagnostic information about the session.
    """
    try:
        from pyrogram import Client
        from pyrogram.errors import SessionExpired, AuthKeyInvalid, FloodWait
    except ImportError:
        return {
            "session_valid": False,
            "error": "Pyrogram not available"
        }

    client = None
    try:
        # Create temporary client
        client = Client(
            name=f"diagnostic_{target_chat_id}",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            in_memory=True
        )

        # Start client and get user info
        await client.start()
        me = await client.get_me()

        result = {
            "session_valid": True,
            "user_id": me.id,
            "username": getattr(me, 'username', None),
            "first_name": getattr(me, 'first_name', None),
            "phone": getattr(me, 'phone_number', None),
            "dialogs_count": 0,
            "target_chat_found": False,
            "recent_dialogs": [],
            "error": None
        }

        # Get dialogs
        try:
            dialogs = []
            async for dialog in client.get_dialogs(limit=200):
                chat = dialog.chat
                chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or f'User {chat.id}'
                dialogs.append({
                    "id": chat.id,
                    "title": chat_title,
                    "type": str(chat.type).split('.')[-1].lower() if hasattr(chat, 'type') else 'unknown'
                })

                # Check if target chat is in dialogs
                if chat.id == target_chat_id:
                    result["target_chat_found"] = True

            result["dialogs_count"] = len(dialogs)
            result["recent_dialogs"] = dialogs

        except FloodWait as e:
            logger.warning(f"FloodWait during get_dialogs: {e.value}s")
            await asyncio.sleep(e.value + 1)
            # Retry once after flood wait
            dialogs = []
            async for dialog in client.get_dialogs(limit=200):
                chat = dialog.chat
                chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or f'User {chat.id}'
                dialogs.append({
                    "id": chat.id,
                    "title": chat_title,
                    "type": str(chat.type).split('.')[-1].lower() if hasattr(chat, 'type') else 'unknown'
                })
                if chat.id == target_chat_id:
                    result["target_chat_found"] = True

            result["dialogs_count"] = len(dialogs)
            result["recent_dialogs"] = dialogs

        except Exception as e:
            logger.exception(f"Error getting dialogs: {e}")
            result["error"] = f"Failed to get dialogs: {str(e)}"

        return result

    except (SessionExpired, AuthKeyInvalid) as e:
        logger.error(f"Invalid session: {e}")
        return {
            "session_valid": False,
            "error": f"Invalid session: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error diagnosing session: {e}")
        return {
            "session_valid": False,
            "error": f"Diagnostic failed: {str(e)}"
        }
    finally:
        if client:
            try:
                await client.stop()
            except Exception:
                pass


@router.get("/internal/streamer/channels/{channel_id}/session-info", response_model=SessionInfoResponse)
async def get_channel_session_info(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Diagnostic endpoint to check Telegram session status and visibility.
    
    Returns information about:
    - Session validity (can login?)
    - User info (who is logged in?)
    - Dialogs list (what chats are visible?)
    - Target chat visibility (can the bot see the target chat?)
    
    This is useful for debugging "Peer id invalid" errors.
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
    
    if not session_string:
        return SessionInfoResponse(
            channel_id=str(channel_id),
            session_valid=False,
            target_chat_id=channel.chat_id,
            error="No session string available"
        )
    
    # Get API credentials
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    if not api_id or not api_hash:
        return SessionInfoResponse(
            channel_id=str(channel_id),
            session_valid=False,
            target_chat_id=channel.chat_id,
            error="API credentials not configured"
        )
    
    # Diagnose session
    diag_result = await diagnose_session(session_string, api_id, api_hash, channel.chat_id)
    
    return SessionInfoResponse(
        channel_id=str(channel_id),
        target_chat_id=channel.chat_id,
        **diag_result
    )
