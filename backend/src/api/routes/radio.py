"""
API routes for internet radio stream management.

Endpoints:
  POST /api/v1/radio/streams - Add new radio stream
  GET /api/v1/radio/streams - List all available radio streams
  DELETE /api/v1/radio/streams/{stream_id} - Remove radio stream
  GET /api/v1/radio/streams/{stream_id} - Get radio stream details
  POST /api/v1/radio/play - Start playing a radio stream
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
import logging

from ..dependencies import get_current_user, require_admin
from ...services.radio_service import RadioService
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/radio", tags=["radio"])


# Request/Response Models
class AddRadioStreamRequest(BaseModel):
    """Request to add a new radio stream."""
    url: HttpUrl = Field(description="Radio stream URL (HTTP/HTTPS)")
    name: str = Field(min_length=1, max_length=100, description="Friendly name of the radio station")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    genre: Optional[str] = Field(None, max_length=50, description="Music genre (e.g., 'Pop', 'Jazz')")
    country: Optional[str] = Field(None, max_length=50, description="Country of origin")


class PlayRadioRequest(BaseModel):
    """Request to play a radio stream."""
    stream_id: int = Field(description="ID of the radio stream to play")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class RadioStreamResponse(BaseModel):
    """Response with radio stream information."""
    id: int
    name: str
    url: str
    description: Optional[str]
    genre: Optional[str]
    country: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class RadioStreamListResponse(BaseModel):
    """Response with list of radio streams."""
    total: int
    streams: List[RadioStreamResponse]
    page: int
    page_size: int


class PlayRadioResponse(BaseModel):
    """Response after starting radio playback."""
    stream_id: int
    stream_name: str
    message: str


# Route Handlers

@router.post("/streams", response_model=RadioStreamResponse, status_code=201)
async def add_radio_stream(
    request: AddRadioStreamRequest,
    current_user: User = Depends(require_admin),
    radio_service: RadioService = Depends(lambda: RadioService())
):
    """
    Add a new internet radio stream to the system.
    
    **Permission**: Admin only
    
    **Rate Limit**: 10 requests/minute per admin (Strict)
    
    **Example**:
    ```json
    {
      "url": "https://stream.example.com/radio.m3u8",
      "name": "BBC Radio 1",
      "description": "Live music from BBC",
      "genre": "Pop",
      "country": "UK"
    }
    ```
    """
    try:
        # Validate URL
        is_valid = await radio_service.validate_url(str(request.url))
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or unreachable radio stream URL"
            )
        
        # Add stream via service
        stream = await radio_service.add_stream(
            url=str(request.url),
            name=request.name,
            description=request.description,
            genre=request.genre,
            country=request.country
        )
        
        logger.info(f"Admin {current_user.id} added radio stream: {request.name}")
        
        return RadioStreamResponse(**stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding radio stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add radio stream")


@router.get("/streams", response_model=RadioStreamListResponse, status_code=200)
async def list_radio_streams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    active_only: bool = Query(True, description="Show only active streams"),
    current_user: User = Depends(get_current_user),
    radio_service: RadioService = Depends(lambda: RadioService())
):
    """
    List all available radio streams.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 200 requests/minute per user (Elevated)
    
    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 20, max 100)
    - `genre`: Filter by music genre
    - `active_only`: Show only active streams (default true)
    """
    try:
        result = await radio_service.list_streams(
            page=page,
            page_size=page_size,
            genre=genre,
            active_only=active_only
        )
        
        streams = [RadioStreamResponse(**s) for s in result["streams"]]
        
        return RadioStreamListResponse(
            total=result["total"],
            streams=streams,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing radio streams: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list radio streams")


@router.get("/streams/{stream_id}", response_model=RadioStreamResponse, status_code=200)
async def get_radio_stream(
    stream_id: int = Path(gt=0, description="Radio stream ID"),
    current_user: User = Depends(get_current_user),
    radio_service: RadioService = Depends(lambda: RadioService())
):
    """
    Get details of a specific radio stream.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 200 requests/minute per user (Elevated)
    """
    try:
        stream = await radio_service.get_stream(stream_id=stream_id)
        
        if not stream:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Radio stream not found")
        
        return RadioStreamResponse(**stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting radio stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get radio stream")


@router.delete("/streams/{stream_id}", status_code=204)
async def delete_radio_stream(
    stream_id: int = Path(gt=0, description="Radio stream ID"),
    current_user: User = Depends(require_admin),
    radio_service: RadioService = Depends(lambda: RadioService())
):
    """
    Remove a radio stream from the system.
    
    **Permission**: Admin only
    
    **Rate Limit**: 10 requests/minute per admin (Strict)
    """
    try:
        success = await radio_service.remove_stream(stream_id=stream_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Radio stream not found")
        
        logger.info(f"Admin {current_user.id} deleted radio stream {stream_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting radio stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete radio stream")


@router.post("/play", response_model=PlayRadioResponse, status_code=200)
async def play_radio_stream(
    request: PlayRadioRequest,
    current_user: User = Depends(get_current_user),
    radio_service: RadioService = Depends(lambda: RadioService())
):
    """
    Start playing a radio stream.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 50 requests/minute per user (Standard)
    
    **Example**:
    ```json
    {
      "stream_id": 1,
      "channel_id": 12345
    }
    ```
    """
    try:
        channel_id = request.channel_id or current_user.id
        
        # Get stream and verify it exists
        stream = await radio_service.get_stream(stream_id=request.stream_id)
        if not stream:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Radio stream not found")
        
        # Start playback via service
        await radio_service.start_playback(
            stream_id=request.stream_id,
            user_id=current_user.id,
            channel_id=channel_id
        )
        
        logger.info(f"User {current_user.id} started playing radio stream {request.stream_id} on channel {channel_id}")
        
        return PlayRadioResponse(
            stream_id=request.stream_id,
            stream_name=stream["name"],
            message=f"Now playing: {stream['name']}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error playing radio stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to play radio stream")
