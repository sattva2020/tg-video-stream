"""
API routes for live stream management.

Endpoints:
  POST /api/v1/live/streams - Create new live stream
  GET /api/v1/live/streams - List all live streams
  GET /api/v1/live/streams/{stream_id} - Get live stream details
  PUT /api/v1/live/streams/{stream_id} - Update live stream
  DELETE /api/v1/live/streams/{stream_id} - Delete live stream
  POST /api/v1/live/streams/{stream_id}/start - Start live stream
  POST /api/v1/live/streams/{stream_id}/stop - Stop live stream
  POST /api/v1/live/streams/{stream_id}/switch - Switch to live stream
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
import logging
from datetime import datetime

from ..dependencies import get_current_user, require_admin
from ...services.rtmp_ingest_service import RTMPIngestService
from ...services.stream_switching_service import StreamSwitchingService
from ...services.recording_service import RecordingService
from ...services.latency_monitor_service import LatencyMonitorService
from ...models.live_stream import LiveStream, LiveStreamStatus, IngestionType
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/live", tags=["live-streams"])


# Request/Response Models
class CreateLiveStreamRequest(BaseModel):
    """Request to create a new live stream."""
    title: str = Field(min_length=1, max_length=200, description="Live stream title")
    chat_id: int = Field(description="Telegram chat ID for broadcast")
    ingestion_type: IngestionType = Field(description="Type of stream ingestion (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)")
    quality_preset: Optional[str] = Field("720p", max_length=20, description="Quality preset (1080p, 720p, 480p, 360p)")
    max_guests: Optional[int] = Field(5, ge=0, le=50, description="Maximum number of guest co-hosts")
    recording_enabled: Optional[bool] = Field(True, description="Enable automatic recording")
    is_chat_enabled: Optional[bool] = Field(True, description="Enable chat during stream")


class UpdateLiveStreamRequest(BaseModel):
    """Request to update a live stream."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Live stream title")
    quality_preset: Optional[str] = Field(None, max_length=20, description="Quality preset")
    max_guests: Optional[int] = Field(None, ge=0, le=50, description="Maximum number of guest co-hosts")
    recording_enabled: Optional[bool] = Field(None, description="Enable automatic recording")
    is_chat_enabled: Optional[bool] = Field(None, description="Enable chat during stream")


class LiveStreamResponse(BaseModel):
    """Response with live stream information."""
    id: int
    owner_id: int
    chat_id: int
    title: str
    status: str
    ingestion_type: str
    ingestion_url: Optional[str]
    stream_key: Optional[str]
    viewer_count: int
    latency_ms: Optional[int]
    preview_url: Optional[str]
    recording_enabled: bool
    active_recording_id: Optional[int]
    max_guests: int
    current_guest_count: int
    quality_preset: str
    is_chat_enabled: bool
    last_error: Optional[str]
    error_count: int
    created_at: str
    started_at: Optional[str]
    went_live_at: Optional[str]
    stopped_at: Optional[str]


class LiveStreamListResponse(BaseModel):
    """Response with list of live streams."""
    total: int
    streams: List[LiveStreamResponse]
    page: int
    page_size: int


class StartLiveStreamResponse(BaseModel):
    """Response after starting a live stream."""
    stream_id: int
    title: str
    status: str
    ingestion_url: Optional[str]
    stream_key: Optional[str]
    preview_url: Optional[str]
    message: str


class StopLiveStreamResponse(BaseModel):
    """Response after stopping a live stream."""
    stream_id: int
    title: str
    status: str
    message: str


class SwitchToLiveStreamResponse(BaseModel):
    """Response after switching to live stream."""
    stream_id: int
    title: str
    status: str
    message: str
    transition_type: str


# Route Handlers

@router.post("/streams", response_model=LiveStreamResponse, status_code=201)
async def create_live_stream(
    request: CreateLiveStreamRequest,
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Create a new live stream.

    **Permission**: Authenticated user only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Example**:
    ```json
    {
      "title": " Evening Live Stream",
      "chat_id": -1001234567890,
      "ingestion_type": "rtmp",
      "quality_preset": "720p",
      "max_guests": 5,
      "recording_enabled": true,
      "is_chat_enabled": true
    }
    ```
    """
    try:
        # Create live stream via service
        stream = await rtmp_service.create_live_stream(
            owner_id=current_user.id,
            chat_id=request.chat_id,
            title=request.title,
            ingestion_type=request.ingestion_type.value,
            quality_preset=request.quality_preset,
            max_guests=request.max_guests,
            recording_enabled=request.recording_enabled,
            is_chat_enabled=request.is_chat_enabled
        )

        logger.info(f"User {current_user.id} created live stream: {request.title}")

        return LiveStreamResponse(**stream)
    except Exception as e:
        logger.error(f"Error creating live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create live stream"
        )


@router.get("/streams", response_model=LiveStreamListResponse, status_code=200)
async def list_live_streams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    List all live streams.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 20, max 100)
    - `status_filter`: Filter by status (idle, active, paused, stopped, error)
    - `owner_id`: Filter by owner ID
    """
    try:
        result = await rtmp_service.list_streams(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            owner_id=owner_id
        )

        streams = [LiveStreamResponse(**s) for s in result["streams"]]

        return LiveStreamListResponse(
            total=result["total"],
            streams=streams,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing live streams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list live streams"
        )


@router.get("/streams/{stream_id}", response_model=LiveStreamResponse, status_code=200)
async def get_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Get details of a specific live stream.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)
    """
    try:
        stream = await rtmp_service.get_stream(stream_id=stream_id)

        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        return LiveStreamResponse(**stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get live stream"
        )


@router.put("/streams/{stream_id}", response_model=LiveStreamResponse, status_code=200)
async def update_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    request: UpdateLiveStreamRequest = None,
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Update a live stream.

    **Permission**: Owner only

    **Rate Limit**: 50 requests/minute per user (Standard)

    **Example**:
    ```json
    {
      "title": "Updated Title",
      "max_guests": 10
    }
    ```
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own streams"
            )

        # Update stream via service
        update_data = request.dict(exclude_unset=True)
        updated_stream = await rtmp_service.update_stream(
            stream_id=stream_id,
            **update_data
        )

        logger.info(f"User {current_user.id} updated live stream {stream_id}")

        return LiveStreamResponse(**updated_stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update live stream"
        )


@router.delete("/streams/{stream_id}", status_code=204)
async def delete_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Delete a live stream.

    **Permission**: Owner only

    **Rate Limit**: 10 requests/minute per user (Strict)
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own streams"
            )

        # Check if stream is active
        if stream["status"] == LiveStreamStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete active stream. Stop it first."
            )

        # Delete stream via service
        success = await rtmp_service.delete_stream(stream_id=stream_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        logger.info(f"User {current_user.id} deleted live stream {stream_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete live stream"
        )


@router.post("/streams/{stream_id}/start", response_model=StartLiveStreamResponse, status_code=200)
async def start_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService()),
    recording_service: RecordingService = Depends(lambda: RecordingService()),
    latency_service: LatencyMonitorService = Depends(lambda: LatencyMonitorService())
):
    """
    Start a live stream.

    **Permission**: Owner only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Notes**:
    - Validates ingestion URL for RTMP/SRT streams
    - Starts automatic recording if enabled
    - Initializes latency monitoring
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only start your own streams"
            )

        # Check if stream can be started
        if stream["status"] not in [LiveStreamStatus.IDLE.value, LiveStreamStatus.STOPPED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start stream with status: {stream['status']}"
            )

        # Validate ingestion URL for RTMP/SRT
        if stream["ingestion_type"] in ["rtmp", "srt"] and stream["ingestion_url"]:
            is_valid = await rtmp_service.validate_ingestion_url(stream["ingestion_url"])
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or unreachable ingestion URL"
                )

        # Start stream via service
        started_stream = await rtmp_service.start_stream(stream_id=stream_id)

        # Start recording if enabled
        if started_stream["recording_enabled"]:
            await recording_service.start_recording(stream_id=stream_id)

        # Initialize latency monitoring
        await latency_service.record_latency_measurement(
            stream_id=stream_id,
            latency_ms=0,
            viewer_count=0,
            source="initialization"
        )

        logger.info(f"User {current_user.id} started live stream {stream_id}")

        return StartLiveStreamResponse(
            stream_id=started_stream["id"],
            title=started_stream["title"],
            status=started_stream["status"],
            ingestion_url=started_stream.get("ingestion_url"),
            stream_key=started_stream.get("stream_key"),
            preview_url=started_stream.get("preview_url"),
            message=f"Live stream '{started_stream['title']}' started successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start live stream"
        )


@router.post("/streams/{stream_id}/stop", response_model=StopLiveStreamResponse, status_code=200)
async def stop_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService()),
    recording_service: RecordingService = Depends(lambda: RecordingService())
):
    """
    Stop a live stream.

    **Permission**: Owner only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Notes**:
    - Stops automatic recording if active
    - Updates stream status to STOPPED
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only stop your own streams"
            )

        # Check if stream is active
        if stream["status"] != LiveStreamStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop stream with status: {stream['status']}"
            )

        # Stop recording if active
        if stream["active_recording_id"]:
            await recording_service.stop_recording(
                recording_id=stream["active_recording_id"]
            )

        # Stop stream via service
        stopped_stream = await rtmp_service.stop_stream(stream_id=stream_id)

        logger.info(f"User {current_user.id} stopped live stream {stream_id}")

        return StopLiveStreamResponse(
            stream_id=stopped_stream["id"],
            title=stopped_stream["title"],
            status=stopped_stream["status"],
            message=f"Live stream '{stopped_stream['title']}' stopped successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop live stream"
        )


@router.post("/streams/{stream_id}/switch", response_model=SwitchToLiveStreamResponse, status_code=200)
async def switch_to_live_stream(
    stream_id: int = Path(gt=0, description="Live stream ID"),
    current_user: User = Depends(get_current_user),
    switching_service: StreamSwitchingService = Depends(lambda: StreamSwitchingService()),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Switch from pre-recorded content to live stream.

    **Permission**: Owner only

    **Rate Limit**: 10 requests/minute per user (Strict)

    **Notes**:
    - Validates stream is ready for live switching
    - Executes seamless transition from scheduled to live content
    - Maintains viewer experience during switch
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only switch to your own streams"
            )

        # Validate transition is possible
        can_switch, issues = await switching_service.can_switch_to_live(
            chat_id=stream["chat_id"],
            live_stream_id=stream_id
        )

        if not can_switch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot switch to live stream: {', '.join(issues)}"
            )

        # Execute switch
        result = await switching_service.execute_switch_to_live(
            chat_id=stream["chat_id"],
            live_stream_id=stream_id
        )

        logger.info(f"User {current_user.id} switched to live stream {stream_id}")

        return SwitchToLiveStreamResponse(
            stream_id=stream_id,
            title=stream["title"],
            status=stream["status"],
            message="Successfully switched to live stream",
            transition_type=result["transition_type"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching to live stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to switch to live stream"
        )
