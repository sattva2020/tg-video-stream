from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.telegram import Channel, TelegramAccount
from api.auth import get_current_user
from src.services.redis_stream_controller import RedisStreamController
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import shutil
import os

router = APIRouter()

# Timeout for transitional states (stopping/starting)
TRANSITIONAL_STATE_TIMEOUT = timedelta(seconds=30)

class ChannelCreate(BaseModel):
    account_id: uuid.UUID
    chat_id: int
    name: str
    chat_username: Optional[str] = None  # Telegram username for reliable peer resolution
    ffmpeg_args: Optional[str] = None
    video_quality: Optional[str] = "best"
    stream_type: Optional[str] = "video"

class ChannelResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    chat_id: int
    chat_username: Optional[str] = None
    name: str
    status: str
    ffmpeg_args: Optional[str]
    video_quality: str
    stream_type: str
    placeholder_image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[ChannelResponse])
def list_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Return channels where the associated account belongs to the current user
    channels = db.query(Channel).join(TelegramAccount).filter(TelegramAccount.user_id == current_user.id).all()
    
    # Enrich with real-time status from Redis
    controller = RedisStreamController(db)
    result = []
    now = datetime.now(timezone.utc)
    
    for channel in channels:
        current_status = channel.status
        
        # Check for transitional state timeout
        # If stopping/starting for too long, reset to stopped
        if current_status in ("stopping", "starting"):
            if channel.updated_at:
                # Make updated_at timezone-aware if it's naive
                updated_at = channel.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                if now - updated_at > TRANSITIONAL_STATE_TIMEOUT:
                    # Timeout exceeded - reset to stopped
                    channel.status = "stopped"
                    db.commit()
                    current_status = "stopped"
        
        channel_dict = {
            "id": channel.id,
            "account_id": channel.account_id,
            "chat_id": channel.chat_id,
            "chat_username": channel.chat_username,
            "name": channel.name,
            "ffmpeg_args": channel.ffmpeg_args,
            "video_quality": channel.video_quality,
            "stream_type": channel.stream_type or "video",
            "placeholder_image": channel.placeholder_image,
            "status": current_status,
        }
        
        # Get real-time status from Redis
        redis_status = controller.get_channel_status_sync(str(channel.id))
        if redis_status.get("status") != "unknown":
            channel_dict["status"] = redis_status.get("status", current_status)
        
        result.append(ChannelResponse(**channel_dict))
    
    return result

@router.post("/", response_model=ChannelResponse)
def create_channel(
    channel_in: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify account belongs to user
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == channel_in.account_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found or access denied")
        
    # Check if channel already exists for this account and chat_id
    existing = db.query(Channel).filter(
        Channel.account_id == channel_in.account_id,
        Channel.chat_id == channel_in.chat_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")
        
    new_channel = Channel(
        account_id=channel_in.account_id,
        chat_id=channel_in.chat_id,
        chat_username=channel_in.chat_username,
        name=channel_in.name,
        ffmpeg_args=channel_in.ffmpeg_args,
        video_quality=channel_in.video_quality,
        stream_type=channel_in.stream_type,
        status="stopped"
    )
    
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)
    return new_channel

@router.post("/{channel_id}/start")
def start_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check ownership or admin
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # TODO: Check if current_user owns the channel's account
    
    controller = RedisStreamController(db)
    try:
        success = controller.start_channel(str(channel_id))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send start command")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "starting", "message": "Start command sent to streamer"}

@router.post("/{channel_id}/stop")
def stop_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    controller = RedisStreamController(db)
    try:
        success = controller.stop_channel(str(channel_id))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send stop command")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "stopping", "message": "Stop command sent to streamer"}

@router.get("/{channel_id}/status")
def get_channel_status(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get real-time status from Redis
    controller = RedisStreamController(db)
    redis_status = controller.get_channel_status_sync(str(channel_id))
    
    if redis_status.get("status") != "unknown":
        return redis_status
    
    return {"status": channel.status}

@router.delete("/{channel_id}")
def delete_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    channel = db.query(Channel).join(TelegramAccount).filter(
        Channel.id == channel_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # Stop channel if running
    if channel.status in ["running", "starting"]:
        controller = RedisStreamController(db)
        try:
            controller.stop_channel(str(channel_id))
        except Exception:
            # Ignore errors when stopping during deletion
            pass
            
    db.delete(channel)
    db.commit()
    
    return {"status": "success", "message": "Channel deleted"}

@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: uuid.UUID,
    channel_in: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    channel = db.query(Channel).join(TelegramAccount).filter(
        Channel.id == channel_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # Update fields
    channel.name = channel_in.name
    channel.ffmpeg_args = channel_in.ffmpeg_args
    channel.video_quality = channel_in.video_quality
    channel.stream_type = channel_in.stream_type
    
    # Note: We don't update account_id or chat_id usually, but if needed:
    # channel.chat_id = channel_in.chat_id
    
    db.commit()
    db.refresh(channel)
    
    return channel

@router.post("/{channel_id}/placeholder")
async def upload_placeholder(
    channel_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    channel = db.query(Channel).join(TelegramAccount).filter(
        Channel.id == channel_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # Ensure directory exists
    upload_dir = "data/placeholders"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate filename
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = ".png"
    filename = f"{channel_id}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update DB
    channel.placeholder_image = file_path
    db.commit()
    
    return {"status": "success", "path": file_path}
