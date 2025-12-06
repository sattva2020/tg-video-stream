from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.telegram import Channel, TelegramAccount
from api.auth import get_current_user
from src.services.redis_stream_controller import RedisStreamController
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import uuid

router = APIRouter()

class ChannelCreate(BaseModel):
    account_id: uuid.UUID
    chat_id: int
    name: str
    ffmpeg_args: Optional[str] = None
    video_quality: Optional[str] = "best"

class ChannelResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    chat_id: int
    name: str
    status: str
    ffmpeg_args: Optional[str]
    video_quality: str

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
    for channel in channels:
        channel_dict = {
            "id": channel.id,
            "account_id": channel.account_id,
            "chat_id": channel.chat_id,
            "name": channel.name,
            "ffmpeg_args": channel.ffmpeg_args,
            "video_quality": channel.video_quality,
            "status": channel.status,  # default from DB
        }
        
        # Get real-time status from Redis
        redis_status = controller.get_channel_status_sync(str(channel.id))
        if redis_status.get("status") != "unknown":
            channel_dict["status"] = redis_status.get("status", channel.status)
        
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
        name=channel_in.name,
        ffmpeg_args=channel_in.ffmpeg_args,
        video_quality=channel_in.video_quality,
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
