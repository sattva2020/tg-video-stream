"""
API routes for music recognition (Shazam-like functionality).

Endpoints:
  POST /api/v1/recognition/identify - Identify a track from audio data
  GET /api/v1/recognition/history - Get user's recognition history
  DELETE /api/v1/recognition/history/{history_id} - Delete recognition from history
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Path
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import io

from ..dependencies import get_current_user
from ...services.shazam_service import ShazamService
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recognition", tags=["recognition"])


# Request/Response Models
class RecognitionResult(BaseModel):
    """Recognition result from Shazam."""
    track_id: str = Field(description="Shazam track ID")
    artist: str = Field(description="Artist name")
    title: str = Field(description="Song title")
    album: Optional[str] = Field(None, description="Album name")
    cover_url: Optional[str] = Field(None, description="Album cover URL")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence (0.0-1.0)")
    duration_seconds: Optional[int] = Field(None, description="Track duration in seconds")


class IdentificationResponse(BaseModel):
    """Response from audio identification."""
    success: bool
    result: Optional[RecognitionResult] = None
    message: str
    rate_limited: bool = False


class RecognitionHistoryEntry(BaseModel):
    """Entry in recognition history."""
    id: int
    track_id: str
    artist: str
    title: str
    identified_at: str
    confidence: float


class RecognitionHistoryResponse(BaseModel):
    """Response with recognition history."""
    total: int
    entries: List[RecognitionHistoryEntry]
    page: int
    page_size: int


# Route Handlers

@router.post("/identify", response_model=IdentificationResponse, status_code=200)
async def identify_track(
    audio_file: UploadFile = File(description="Audio file (MP3, WAV, OGG, M4A)"),
    current_user: User = Depends(get_current_user),
    shazam_service: ShazamService = Depends(lambda: ShazamService())
):
    """
    Identify a track from uploaded audio file.
    
    **Supported Formats**: MP3, WAV, OGG, M4A
    
    **Max File Size**: 10 MB
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 10 requests/minute per user (Strict) - Shazam API limit
    
    **Returns**:
    - `success`: Whether identification was successful
    - `result`: Track information if found
    - `message`: Human-readable status message
    - `rate_limited`: Whether rate limit was hit
    
    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/recognition/identify \
      -H "Authorization: Bearer TOKEN" \
      -F "audio_file=@song.mp3"
    ```
    """
    try:
        # Validate file type
        allowed_types = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/x-m4a"}
        if audio_file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Supported: MP3, WAV, OGG, M4A. Got: {audio_file.content_type}"
            )
        
        # Validate file size (max 10 MB)
        audio_data = await audio_file.read()
        if len(audio_data) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large (max 10 MB)"
            )
        
        # Atomically consume per-user rate limit
        allowed, retry_after = await shazam_service.consume_rate_limit(
            user_id=current_user.id,
            user_role=current_user.role,
        )
        if not allowed:
            logger.warning(
                "User %s hit Shazam rate limit, retry_after=%ss",
                current_user.id,
                retry_after,
            )
            wait_msg = (
                f"Rate limit exceeded. Retry after {retry_after} seconds"
                if retry_after
                else "Rate limit exceeded (10 recognitions per minute)"
            )
            return IdentificationResponse(
                success=False,
                message=wait_msg,
                rate_limited=True,
            )
        
        # Identify track
        result = await shazam_service.recognize_track(
            audio_data=io.BytesIO(audio_data),
            user_id=current_user.id,
            mime_type=audio_file.content_type,
        )
        
        if result:
            # Log recognition to user's history
            await shazam_service.add_to_history(
                user_id=current_user.id,
                track_id=result.get("track_id"),
                artist=result.get("artist"),
                title=result.get("title"),
                confidence=result.get("confidence", 0.0)
            )
            
            logger.info(
                f"User {current_user.id} identified track: {result.get('artist')} - {result.get('title')}"
            )
            
            return IdentificationResponse(
                success=True,
                result=RecognitionResult(**result),
                message=f"Track identified: {result.get('artist')} - {result.get('title')}"
            )
        else:
            logger.info(f"User {current_user.id} sent audio but no match found")
            
            return IdentificationResponse(
                success=False,
                message="No matching track found in database"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error identifying track: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to identify track"
        )


@router.get("/history", response_model=RecognitionHistoryResponse, status_code=200)
async def get_recognition_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    shazam_service: ShazamService = Depends(lambda: ShazamService())
):
    """
    Get user's music recognition history.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 20, max 100)
    
    **Returns**:
    - `total`: Total number of recognitions
    - `entries`: List of recognition entries
    - `page`: Current page number
    - `page_size`: Results per page
    """
    try:
        if page_size > 100:
            page_size = 100
        
        history = await shazam_service.get_history(
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        entries = [RecognitionHistoryEntry(**e) for e in history.get("entries", [])]
        
        logger.info(f"User {current_user.id} retrieved recognition history page {page}")
        
        return RecognitionHistoryResponse(
            total=history.get("total", 0),
            entries=entries,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error retrieving recognition history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recognition history"
        )


@router.delete("/history/{history_id}", status_code=204)
async def delete_history_entry(
    history_id: int = Path(gt=0, description="History entry ID"),
    current_user: User = Depends(get_current_user),
    shazam_service: ShazamService = Depends(lambda: ShazamService())
):
    """
    Remove a track from recognition history.
    
    **Permission**: User can only delete own history entries
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    """
    try:
        # Verify ownership
        entry = await shazam_service.get_history_entry(entry_id=history_id)
        if not entry or str(entry.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete this history entry"
            )
        
        # Delete entry
        success = await shazam_service.delete_from_history(entry_id=history_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="History entry not found"
            )
        
        logger.info(f"User {current_user.id} deleted recognition history entry {history_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete history entry"
        )
