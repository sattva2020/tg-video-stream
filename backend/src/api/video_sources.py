"""
Video sources API router for the Telegram broadcast platform.

This module provides REST API endpoints for video source management,
including automatic URL detection, validation, and source type information.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, field_validator

from src.database import get_db
from src.models.user import User
from src.lib.source_detector import SourceDetector, SourceType
from api.auth import get_current_user


router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class VideoSourceDetectRequest(BaseModel):
    """Request model for video source detection."""
    url: str

    @field_validator('url')
    @classmethod
    def validate_url_not_empty(cls, v: str) -> str:
        """Validate that URL is not empty."""
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        return v.strip()


class VideoSourceDetectResponse(BaseModel):
    """Response model for video source detection."""
    valid: bool
    source_type: str
    source_type_label: str
    metadata: Dict[str, Any]
    normalized_url: str
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VideoSourceValidateRequest(BaseModel):
    """Request model for video source validation."""
    url: str
    check_availability: bool = False

    @field_validator('url')
    @classmethod
    def validate_url_not_empty(cls, v: str) -> str:
        """Validate that URL is not empty."""
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        return v.strip()


class VideoSourceValidateResponse(BaseModel):
    """Response model for video source validation."""
    valid: bool
    source_type: str
    source_type_label: str
    is_available: Optional[bool] = None
    compatibility_issues: List[str] = []
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupportedSourcesResponse(BaseModel):
    """Response model for supported sources list."""
    sources: List[Dict[str, Any]]
    total_count: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/detect", response_model=VideoSourceDetectResponse)
async def detect_video_source(
    request: VideoSourceDetectRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Detect video source type from URL.

    Automatically detects the type of video source from a given URL
    and extracts relevant metadata such as video IDs, file IDs, etc.

    Supports:
    - YouTube (videos, playlists, channels)
    - Vimeo (videos, playlists)
    - Twitch (channels, VODs, clips)
    - Dailymotion (videos)
    - Direct video URLs (MP4, WebM, MKV, AVI, etc.)
    - HLS/DASH streaming URLs (.m3u8, .mpd)
    - Cloud storage (Google Drive, Dropbox, OneDrive)
    - RSS/Atom feeds with video enclosures
    """
    try:
        # Normalize the URL
        normalized_url = SourceDetector.normalize_url(request.url)

        # Detect source type
        detection_result = SourceDetector.detect_source(normalized_url)

        # Get human-readable label for source type
        source_type_label = _get_source_type_label(detection_result["source_type"])

        return VideoSourceDetectResponse(
            valid=detection_result["valid"],
            source_type=detection_result["source_type"],
            source_type_label=source_type_label,
            metadata=detection_result["metadata"],
            normalized_url=normalized_url,
            error=detection_result.get("error")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting video source: {str(e)}"
        )


@router.post("/validate", response_model=VideoSourceValidateResponse)
async def validate_video_source(
    request: VideoSourceValidateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate video source URL and check compatibility.

    Validates that a URL is a supported video source and optionally
    checks if the video is available for streaming.

    Returns compatibility issues for direct video URLs (codec checks, etc.).
    """
    try:
        # Normalize the URL
        normalized_url = SourceDetector.normalize_url(request.url)

        # Detect source type
        detection_result = SourceDetector.detect_source(normalized_url)

        if not detection_result["valid"]:
            return VideoSourceValidateResponse(
                valid=False,
                source_type=SourceType.UNKNOWN,
                source_type_label="Unknown",
                error=detection_result.get("error", "Unable to detect source type")
            )

        source_type = detection_result["source_type"]
        source_type_label = _get_source_type_label(source_type)

        # Check availability if requested (placeholder for future implementation)
        is_available = None
        compatibility_issues = []

        if request.check_availability:
            # TODO: Implement availability checking
            # This would involve making HTTP requests to validate the URL
            # and checking if the video is accessible
            pass

        # Check for compatibility issues
        if source_type == SourceType.DIRECT:
            # Direct video URLs may have codec compatibility issues
            metadata = detection_result.get("metadata", {})
            extension = metadata.get("extension", "")

            # Check for potentially problematic formats
            if extension in ['.avi', '.wmv', '.flv']:
                compatibility_issues.append(
                    f"File format {extension} may require transcoding for streaming"
                )

        return VideoSourceValidateResponse(
            valid=True,
            source_type=source_type,
            source_type_label=source_type_label,
            is_available=is_available,
            compatibility_issues=compatibility_issues,
            error=None
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating video source: {str(e)}"
        )


@router.get("/supported", response_model=SupportedSourcesResponse)
async def get_supported_sources(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of supported video source types.

    Returns information about all supported video source types,
    including descriptions and examples.
    """
    sources = [
        {
            "type": SourceType.YOUTUBE,
            "label": "YouTube",
            "description": "YouTube videos, playlists, and channels",
            "examples": [
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://youtu.be/dQw4w9WgXcQ",
                "https://www.youtube.com/playlist?list=PLxyz"
            ]
        },
        {
            "type": SourceType.VIMEO,
            "label": "Vimeo",
            "description": "Vimeo videos and playlists",
            "examples": [
                "https://vimeo.com/123456789",
                "https://vimeo.com/channels/staffpicks/123456789"
            ]
        },
        {
            "type": SourceType.TWITCH,
            "label": "Twitch",
            "description": "Twitch channels, VODs, and clips",
            "examples": [
                "https://www.twitch.tv/username",
                "https://www.twitch.tv/videos/123456789"
            ]
        },
        {
            "type": SourceType.DAILYMOTION,
            "label": "Dailymotion",
            "description": "Dailymotion videos",
            "examples": [
                "https://www.dailymotion.com/video/x123abc",
                "https://dai.ly/x123abc"
            ]
        },
        {
            "type": SourceType.DIRECT,
            "label": "Direct Video URL",
            "description": "Direct video file URLs (MP4, WebM, MKV, etc.)",
            "examples": [
                "https://example.com/videos/video.mp4",
                "https://cdn.example.com/content/video.webm"
            ]
        },
        {
            "type": SourceType.HLS,
            "label": "HLS Stream",
            "description": "HTTP Live Streaming (.m3u8)",
            "examples": [
                "https://example.com/stream/playlist.m3u8"
            ]
        },
        {
            "type": SourceType.DASH,
            "label": "DASH Stream",
            "description": "Dynamic Adaptive Streaming over HTTP (.mpd)",
            "examples": [
                "https://example.com/stream/manifest.mpd"
            ]
        },
        {
            "type": SourceType.GOOGLE_DRIVE,
            "label": "Google Drive",
            "description": "Videos stored on Google Drive",
            "examples": [
                "https://drive.google.com/file/d/1Ab2Cd3Ef4Gh5Ij6Kl7Mn8Op9Qr0St1U/view"
            ]
        },
        {
            "type": SourceType.DROPBOX,
            "label": "Dropbox",
            "description": "Videos stored on Dropbox",
            "examples": [
                "https://www.dropbox.com/s/abc123def456/video.mp4?dl=0"
            ]
        },
        {
            "type": SourceType.ONEDRIVE,
            "label": "OneDrive",
            "description": "Videos stored on Microsoft OneDrive",
            "examples": [
                "https://onedrive.live.com/?authkey=...",
                "https://1drv.ms/u/s!AbC123DeF456"
            ]
        },
        {
            "type": SourceType.RSS_FEED,
            "label": "RSS/Atom Feed",
            "description": "RSS or Atom feeds with video enclosures",
            "examples": [
                "https://example.com/feed.xml",
                "https://example.com/rss",
                "https://example.com/atom.xml"
            ]
        }
    ]

    return SupportedSourcesResponse(
        sources=sources,
        total_count=len(sources)
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _get_source_type_label(source_type: SourceType) -> str:
    """
    Get human-readable label for source type.

    Args:
        source_type: SourceType enum value

    Returns:
        str: Human-readable label
    """
    labels = {
        SourceType.YOUTUBE: "YouTube",
        SourceType.VIMEO: "Vimeo",
        SourceType.DAILYMOTION: "Dailymotion",
        SourceType.TWITCH: "Twitch",
        SourceType.DIRECT: "Direct Video URL",
        SourceType.HLS: "HLS Stream",
        SourceType.DASH: "DASH Stream",
        SourceType.GOOGLE_DRIVE: "Google Drive",
        SourceType.DROPBOX: "Dropbox",
        SourceType.ONEDRIVE: "OneDrive",
        SourceType.RSS_FEED: "RSS/Atom Feed",
        SourceType.UNKNOWN: "Unknown"
    }

    return labels.get(source_type, str(source_type))
