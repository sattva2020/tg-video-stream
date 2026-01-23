"""
API routes for stream preview management.

Endpoints:
  GET /api/v1/live/preview/{stream_id} - Get stream preview URL and metadata
  POST /api/v1/live/preview/{stream_id}/generate - Generate new preview URL
  GET /api/v1/live/preview/{stream_id}/health - Get stream health status for preview
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from ..dependencies import get_current_user
from ...services.rtmp_ingest_service import RTMPIngestService
from ...services.latency_monitor_service import LatencyMonitorService
from ...models.live_stream import LiveStream, LiveStreamStatus
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/live/preview", tags=["stream-preview"])


# Request/Response Models

class StreamPreviewResponse(BaseModel):
    """Response with stream preview information."""
    stream_id: int
    title: str
    status: str
    preview_url: Optional[str]
    thumbnail_url: Optional[str]
    is_preview_available: bool
    ingestion_type: str
    viewer_count: int
    latency_ms: Optional[int]
    quality_preset: str
    can_start: bool
    message: Optional[str]


class GeneratePreviewResponse(BaseModel):
    """Response after generating a new preview URL."""
    stream_id: int
    preview_url: str
    expires_at: Optional[str]
    message: str


class StreamHealthResponse(BaseModel):
    """Response with stream health status for preview."""
    stream_id: int
    status: str
    is_healthy: bool
    health_score: int  # 0-100
    issues: list[str]
    warnings: list[str]
    latency_ms: Optional[int]
    viewer_count: int
    bitrate: Optional[int]
    packet_loss: Optional[float]
    last_checked: str


# Route Handlers

@router.get("/{stream_id}", response_model=StreamPreviewResponse, status_code=200)
async def get_stream_preview(
    stream_id: str = Path(..., description="Stream ID or identifier"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService()),
    latency_service: LatencyMonitorService = Depends(lambda: LatencyMonitorService())
):
    """
    Get stream preview URL and metadata.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Notes**:
    - Returns preview URL for the stream
    - Includes stream health and quality information
    - Shows whether stream is ready to start
    """
    try:
        # Try to parse as integer, otherwise use as string identifier
        try:
            stream_id_int = int(stream_id)
            stream = await rtmp_service.get_stream(stream_id=stream_id_int)
        except (ValueError, HTTPException):
            # If not found by ID, try to search by title or other identifier
            # For now, return 404 for non-integer IDs
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream '{stream_id}' not found"
            )

        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )

        # Get current latency
        latency = await latency_service.get_current_latency(stream_id=stream["id"])

        # Determine if preview is available and stream can start
        preview_available = bool(stream.get("preview_url"))
        can_start = stream["status"] in [
            LiveStreamStatus.IDLE.value,
            LiveStreamStatus.STOPPED.value
        ]

        # Generate message
        if preview_available:
            message = "Preview available"
        elif stream["status"] == LiveStreamStatus.ACTIVE.value:
            message = "Stream is currently live"
        else:
            message = "Preview not available - stream may not be configured"

        return StreamPreviewResponse(
            stream_id=stream["id"],
            title=stream["title"],
            status=stream["status"],
            preview_url=stream.get("preview_url"),
            thumbnail_url=stream.get("thumbnail_url"),
            is_preview_available=preview_available,
            ingestion_type=stream["ingestion_type"],
            viewer_count=stream.get("viewer_count", 0),
            latency_ms=latency,
            quality_preset=stream.get("quality_preset", "720p"),
            can_start=can_start,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stream preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stream preview"
        )


@router.post("/{stream_id}/generate", response_model=GeneratePreviewResponse, status_code=200)
async def generate_stream_preview(
    stream_id: int = Path(gt=0, description="Stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService())
):
    """
    Generate a new preview URL for a stream.

    **Permission**: Owner only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Notes**:
    - Generates a new preview URL with expiration
    - Useful for refreshing preview access
    - Preview URLs typically expire after 24 hours
    """
    try:
        # Get stream and verify ownership
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )

        if stream["owner_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only generate previews for your own streams"
            )

        # Generate preview URL based on ingestion type
        # In a real implementation, this would call a service to generate a signed URL
        ingestion_type = stream["ingestion_type"]
        stream_key = stream.get("stream_key", "")

        # Mock preview URL generation - in production, this would use a proper signing service
        preview_url = f"http://localhost:8000/preview/{stream['id']}?token={stream_key[:16]}"

        # Update stream with new preview URL
        await rtmp_service.update_stream(
            stream_id=stream_id,
            preview_url=preview_url
        )

        logger.info(f"User {current_user.id} generated preview URL for stream {stream_id}")

        return GeneratePreviewResponse(
            stream_id=stream_id,
            preview_url=preview_url,
            expires_at=None,  # Could calculate expiration based on token
            message="Preview URL generated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating stream preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate stream preview"
        )


@router.get("/{stream_id}/health", response_model=StreamHealthResponse, status_code=200)
async def get_stream_health(
    stream_id: int = Path(gt=0, description="Stream ID"),
    current_user: User = Depends(get_current_user),
    rtmp_service: RTMPIngestService = Depends(lambda: RTMPIngestService()),
    latency_service: LatencyMonitorService = Depends(lambda: LatencyMonitorService())
):
    """
    Get stream health status for preview.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Notes**:
    - Returns comprehensive health information
    - Useful for determining if stream is ready to go live
    - Includes latency, bitrate, and connection quality metrics
    """
    try:
        # Get stream
        stream = await rtmp_service.get_stream(stream_id=stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )

        # Get current latency
        latency = await latency_service.get_current_latency(stream_id=stream_id)

        # Check latency health
        is_healthy, health_issues = await latency_service.check_latency_health(
            stream_id=stream_id,
            threshold_ms=5000  # 5 second threshold
        )

        # Calculate health score (0-100)
        health_score = 100
        issues = []
        warnings = []

        if latency and latency > 5000:
            health_score -= 30
            issues.append(f"High latency: {latency}ms")
        elif latency and latency > 3000:
            health_score -= 15
            warnings.append(f"Elevated latency: {latency}ms")

        if stream["error_count"] > 5:
            health_score -= 20
            issues.append(f"Multiple errors: {stream['error_count']}")

        if stream["status"] == LiveStreamStatus.ERROR.value:
            health_score -= 40
            issues.append("Stream in error state")

        if stream["last_error"]:
            warnings.append(f"Last error: {stream['last_error']}")

        if health_score < 0:
            health_score = 0

        # Get additional metrics (mock for now)
        bitrate = None
        packet_loss = None

        # If stream is active, we could get real metrics from the streaming service
        if stream["status"] == LiveStreamStatus.ACTIVE.value:
            bitrate = 2500  # Mock bitrate in kbps
            packet_loss = 0.5  # Mock packet loss percentage

        return StreamHealthResponse(
            stream_id=stream_id,
            status=stream["status"],
            is_healthy=is_healthy,
            health_score=health_score,
            issues=issues,
            warnings=warnings,
            latency_ms=latency,
            viewer_count=stream.get("viewer_count", 0),
            bitrate=bitrate,
            packet_loss=packet_loss,
            last_checked=datetime.utcnow().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stream health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stream health"
        )
