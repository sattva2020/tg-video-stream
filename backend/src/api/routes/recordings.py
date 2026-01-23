"""
API routes for recording management.

Endpoints:
  GET /api/v1/recordings - List all recordings
  GET /api/v1/recordings/{recording_id} - Get recording details
  DELETE /api/v1/recordings/{recording_id} - Delete recording
  GET /api/v1/recordings/stream/{stream_id} - Get recordings for a specific stream
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ..dependencies import get_current_user, require_admin
from ...services.recording_service import RecordingService
from ...models.recording import Recording, RecordingStatus, RecordingFormat
from ...models.live_stream import LiveStream
from ...models.user import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])


# Request/Response Models
class RecordingResponse(BaseModel):
    """Response with recording information."""
    id: str
    live_stream_id: str
    file_path: str
    file_url: Optional[str]
    duration: Optional[int]
    file_size: Optional[int]
    status: str
    started_at: str
    ended_at: Optional[str]
    created_at: str
    updated_at: str
    format: Optional[str]
    bitrate: Optional[int]
    resolution: Optional[str]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    thumbnail_url: Optional[str]
    preview_url: Optional[str]
    error_message: Optional[str]


class RecordingListResponse(BaseModel):
    """Response with list of recordings."""
    total: int
    recordings: List[RecordingResponse]
    page: int
    page_size: int


# Helper function to convert Recording to response dict
def recording_to_dict(recording: Recording) -> dict:
    """Convert Recording ORM object to dictionary."""
    return {
        "id": str(recording.id),
        "live_stream_id": str(recording.live_stream_id),
        "file_path": recording.file_path,
        "file_url": recording.file_url,
        "duration": recording.duration,
        "file_size": recording.file_size,
        "status": recording.status.value,
        "started_at": recording.started_at.isoformat() if recording.started_at else None,
        "ended_at": recording.ended_at.isoformat() if recording.ended_at else None,
        "created_at": recording.created_at.isoformat() if recording.created_at else None,
        "updated_at": recording.updated_at.isoformat() if recording.updated_at else None,
        "format": recording.format.value if recording.format else None,
        "bitrate": recording.bitrate,
        "resolution": recording.resolution,
        "video_codec": recording.video_codec,
        "audio_codec": recording.audio_codec,
        "thumbnail_url": recording.thumbnail_url,
        "preview_url": recording.preview_url,
        "error_message": recording.error_message
    }


# Route Handlers

@router.get("", response_model=RecordingListResponse, status_code=200)
async def list_recordings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status (recording, processing, ready, error, deleted)"),
    live_stream_id: Optional[str] = Query(None, description="Filter by live stream ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: None)  # Placeholder, will be replaced in actual implementation
):
    """
    List all recordings.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 20, max 100)
    - `status_filter`: Filter by status (recording, processing, ready, error, deleted)
    - `live_stream_id`: Filter by live stream ID
    """
    try:
        # Import get_db locally to avoid circular dependency
        from src.database import get_db

        # Get database session
        db_gen = get_db()
        db_session = next(db_gen)

        try:
            # Create service instance
            recording_service = RecordingService(db_session)

            # Parse status filter
            status_enum = None
            if status_filter:
                try:
                    status_enum = RecordingStatus(status_filter)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {status_filter}. Valid values: recording, processing, ready, error, deleted"
                    )

            # Get recordings
            if live_stream_id:
                # Get recordings for specific stream
                recordings = recording_service.get_recordings_for_stream(
                    live_stream_id=live_stream_id,
                    status=status_enum
                )

                # Apply pagination
                total = len(recordings)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_recordings = recordings[start_idx:end_idx]
            else:
                # Get all recordings with pagination
                offset = (page - 1) * page_size
                paginated_recordings = recording_service.get_all_recordings(
                    status=status_enum,
                    limit=page_size,
                    offset=offset
                )
                total = len(paginated_recordings)  # Note: This might not be accurate total count

            recordings_list = [recording_to_dict(r) for r in paginated_recordings]

            return RecordingListResponse(
                total=total,
                recordings=recordings_list,
                page=page,
                page_size=page_size
            )
        finally:
            # Close database session
            db_gen.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing recordings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list recordings"
        )


@router.get("/stream/{stream_id}", response_model=RecordingListResponse, status_code=200)
async def get_recordings_for_stream(
    stream_id: str = Path(..., description="Live stream ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: None)  # Placeholder
):
    """
    Get all recordings for a specific live stream.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Query Parameters**:
    - `status_filter`: Filter by status (recording, processing, ready, error, deleted)
    """
    try:
        # Import get_db locally to avoid circular dependency
        from src.database import get_db

        # Get database session
        db_gen = get_db()
        db_session = next(db_gen)

        try:
            # Create service instance
            recording_service = RecordingService(db_session)

            # Parse status filter
            status_enum = None
            if status_filter:
                try:
                    status_enum = RecordingStatus(status_filter)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {status_filter}"
                    )

            # Get recordings for stream
            recordings = recording_service.get_recordings_for_stream(
                live_stream_id=stream_id,
                status=status_enum
            )

            recordings_list = [recording_to_dict(r) for r in recordings]

            return RecordingListResponse(
                total=len(recordings_list),
                recordings=recordings_list,
                page=1,
                page_size=len(recordings_list)
            )
        finally:
            # Close database session
            db_gen.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recordings for stream {stream_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recordings for stream"
        )


@router.get("/{recording_id}", response_model=RecordingResponse, status_code=200)
async def get_recording(
    recording_id: str = Path(..., description="Recording ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: None)  # Placeholder
):
    """
    Get details of a specific recording.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)
    """
    try:
        # Import get_db locally to avoid circular dependency
        from src.database import get_db

        # Get database session
        db_gen = get_db()
        db_session = next(db_gen)

        try:
            # Create service instance
            recording_service = RecordingService(db_session)

            # Get recording
            recording = recording_service.get_recording(recording_id=recording_id)

            if not recording:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recording not found"
                )

            return RecordingResponse(**recording_to_dict(recording))
        finally:
            # Close database session
            db_gen.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recording {recording_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recording"
        )


@router.delete("/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: str = Path(..., description="Recording ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: None)  # Placeholder
):
    """
    Delete a recording.

    **Permission**: Authenticated user only (recording owner check recommended)

    **Rate Limit**: 10 requests/minute per user (Strict)

    **Note**: This marks the recording as deleted and removes the file.
    The actual database record is retained for audit purposes.
    """
    try:
        # Import get_db locally to avoid circular dependency
        from src.database import get_db

        # Get database session
        db_gen = get_db()
        db_session = next(db_gen)

        try:
            # Create service instance
            recording_service = RecordingService(db_session)

            # Verify recording exists and user has permission
            recording = recording_service.get_recording(recording_id=recording_id)
            if not recording:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recording not found"
                )

            # TODO: Add ownership check if needed (verify user owns the live stream)
            # For now, any authenticated user can delete any recording
            # Consider adding:
            # live_stream = db_session.query(LiveStream).filter(LiveStream.id == recording.live_stream_id).first()
            # if live_stream and live_stream.owner_id != current_user.id:
            #     raise HTTPException(status_code=403, detail="You can only delete recordings from your own streams")

            # Delete recording
            success = recording_service.delete_recording(recording_id=recording_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recording not found"
                )

            logger.info(f"User {current_user.id} deleted recording {recording_id}")
        finally:
            # Close database session
            db_gen.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recording {recording_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete recording"
        )
