from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.telegram import Channel, TelegramAccount
from src.models.schedule import ScheduleSlot, RepeatType, Playlist
from api.auth import get_current_user
from src.services.redis_stream_controller import RedisStreamController
from src.services.video_validation_service import VideoValidationService
from pydantic import BaseModel, ConfigDict, Field, validator
from typing import List, Optional
from datetime import datetime, timezone, timedelta, time, date
import uuid
import shutil
import os
import re

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
    playlist_id: Optional[uuid.UUID] = None
    # Encoding profile settings
    video_codec: Optional[str] = "h264"
    audio_codec: Optional[str] = "aac"
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    resolution: Optional[str] = None

class ChannelResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    chat_id: int
    chat_username: Optional[str] = None
    name: str
    status: str
    error_message: Optional[str] = None
    ffmpeg_args: Optional[str]
    video_quality: str
    stream_type: str
    placeholder_image: Optional[str] = None
    # Encoding profile settings
    video_codec: Optional[str] = "h264"
    audio_codec: Optional[str] = "aac"
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    resolution: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CodecValidationRequest(BaseModel):
    """Request model for codec validation in channel context."""

    video_codec: Optional[str] = Field(None, description="Video codec name (e.g., 'h264', 'h265')")
    audio_codec: Optional[str] = Field(None, description="Audio codec name (e.g., 'aac', 'mp3', 'opus')")
    resolution: Optional[str] = Field(None, description="Resolution in format 'WIDTHxHEIGHT' (e.g., '1920x1080')")

    @validator('resolution')
    def validate_resolution(cls, v):
        """Validate resolution format."""
        if v is None:
            return v

        # Check resolution format (WIDTHxHEIGHT)
        pattern = r'^\d+x\d+$'
        if not re.match(pattern, v):
            raise ValueError(f'Resolution must be in format "WIDTHxHEIGHT" (e.g., "1920x1080"), got: {v}')

        # Extract dimensions
        try:
            width, height = map(int, v.split('x'))
            # Basic sanity checks
            if width < 1 or width > 7680:
                raise ValueError(f'Width must be between 1 and 7680, got: {width}')
            if height < 1 or height > 4320:
                raise ValueError(f'Height must be between 1 and 4320, got: {height}')
        except ValueError as e:
            raise ValueError(f'Invalid resolution format: {e}')

        return v


class CodecValidationResponse(BaseModel):
    """Response model for codec validation in channel context."""

    valid: bool = Field(..., description="Whether codecs and resolution are valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    video_codec_supported: Optional[bool] = Field(None, description="Whether video codec is supported")
    audio_codec_supported: Optional[bool] = Field(None, description="Whether audio codec is supported")
    resolution_valid: Optional[bool] = Field(None, description="Whether resolution format is valid")


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
        error_message = channel.error_message
        
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
            "video_quality": channel.video_quality or "best",
            "stream_type": channel.stream_type or "video",
            "placeholder_image": channel.placeholder_image,
            "status": current_status or "stopped",
            "error_message": error_message,
            "video_codec": channel.video_codec or "h264",
            "audio_codec": channel.audio_codec or "aac",
            "video_bitrate": channel.video_bitrate,
            "audio_bitrate": channel.audio_bitrate,
            "resolution": channel.resolution,
        }
        
        # Get real-time status from Redis
        redis_status = controller.get_channel_status_sync(str(channel.id))
        if redis_status.get("status") != "unknown":
            channel_dict["status"] = redis_status.get("status", current_status)
            # If Redis has an error message, use it
            if redis_status.get("error"):
                channel_dict["error_message"] = redis_status.get("error")
        
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
        video_codec=channel_in.video_codec,
        audio_codec=channel_in.audio_codec,
        video_bitrate=channel_in.video_bitrate,
        audio_bitrate=channel_in.audio_bitrate,
        resolution=channel_in.resolution,
        status="stopped"
    )
    
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    # If playlist_id is provided, create a default schedule slot
    if channel_in.playlist_id:
        # Verify playlist exists and belongs to user
        playlist = db.query(Playlist).filter(
            Playlist.id == channel_in.playlist_id,
            Playlist.user_id == current_user.id
        ).first()

        if playlist:
            default_slot = ScheduleSlot(
                channel_id=new_channel.id,
                playlist_id=playlist.id,
                start_date=datetime.now(timezone.utc).date(),
                start_time=time(0, 0),
                end_time=time(23, 59, 59),
                repeat_type=RepeatType.DAILY,
                title="Default Playlist",
                priority=0,
                is_active=True,
                created_by=current_user.id
            )
            db.add(default_slot)
            db.commit()

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
            
        # Deactivate currently running slots
        now = datetime.now(timezone.utc)
        current_date = now.date()
        current_time = now.time()
        
        active_slots = db.query(ScheduleSlot).filter(
            ScheduleSlot.channel_id == channel_id,
            ScheduleSlot.is_active == True,
            ScheduleSlot.start_date == current_date
        ).all()
        
        for slot in active_slots:
            # Check if slot is currently running
            if slot.start_time <= current_time <= slot.end_time:
                # Only deactivate non-recurring slots (like Play Now)
                if slot.repeat_type == RepeatType.NONE:
                    slot.is_active = False
                
        db.commit()
            
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
    channel.video_codec = channel_in.video_codec
    channel.audio_codec = channel_in.audio_codec
    channel.video_bitrate = channel_in.video_bitrate
    channel.audio_bitrate = channel_in.audio_bitrate
    channel.resolution = channel_in.resolution

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


@router.post("/validate-codec", response_model=CodecValidationResponse)
async def validate_codec(
    request: CodecValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate video and audio codecs for Telegram compatibility.

    Provides quick validation without downloading video files.
    Useful for validating codec settings before creating or updating channels.

    Checks:
    - Video codec compatibility (h264, h265)
    - Audio codec compatibility (aac, mp3, opus)
    - Resolution format validation

    Returns validation result with specific support information for each codec.
    """
    try:
        service = VideoValidationService(db_session=db)

        # Validate codecs using VideoValidationService
        codec_result = await service.validate_codecs(
            video_codec=request.video_codec,
            audio_codec=request.audio_codec
        )

        # Initialize response
        errors = codec_result.get("errors", []).copy()
        warnings = []
        valid = codec_result.get("valid", True)

        # Validate resolution if provided
        resolution_valid = True
        if request.resolution:
            try:
                # Resolution is already validated by the Pydantic validator
                # Add informational warning about very high resolutions
                width, height = map(int, request.resolution.split('x'))

                # Check for 4K+ resolutions (may require more bandwidth)
                if width >= 3840 or height >= 2160:
                    warnings.append(
                        f"High resolution {request.resolution} detected. "
                        "Ensure sufficient bandwidth is available."
                    )

                # Check for very low resolutions
                if width < 640 or height < 480:
                    warnings.append(
                        f"Low resolution {request.resolution} may result in poor quality."
                    )

            except Exception as e:
                resolution_valid = False
                errors.append(f"Resolution validation error: {str(e)}")
                valid = False

        # Determine codec support status
        video_codec_supported = None
        audio_codec_supported = None

        if request.video_codec:
            # Check if video codec error exists
            video_errors = [e for e in errors if "Video codec" in e]
            video_codec_supported = len(video_errors) == 0

        if request.audio_codec:
            # Check if audio codec error exists
            audio_errors = [e for e in errors if "Audio codec" in e]
            audio_codec_supported = len(audio_errors) == 0

        return CodecValidationResponse(
            valid=valid,
            errors=errors,
            warnings=warnings,
            video_codec_supported=video_codec_supported,
            audio_codec_supported=audio_codec_supported,
            resolution_valid=resolution_valid if request.resolution else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Codec validation failed: {str(e)}"
        )

