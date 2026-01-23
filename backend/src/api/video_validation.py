"""
Video validation API endpoints.

Provides video format validation and Telegram compatibility checking:
- Video URL validation
- Codec and format verification
- Orientation detection
- Transcoding requirement checking
- Validation result caching
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from database import get_db
from src.api.auth.dependencies import get_current_user
from src.models.user import User
from src.services.video_validation_service import VideoValidationService

router = APIRouter(prefix="/video", tags=["video"])


class VideoValidationRequest(BaseModel):
    """Request model for video validation."""

    url: str = Field(..., description="Video URL to validate")
    timeout: int = Field(default=10, ge=1, le=60, description="FFprobe timeout in seconds")
    cache_result: bool = Field(default=True, description="Whether to cache validation result")

    @validator('url')
    def validate_url(cls, v):
        """Basic URL validation."""
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        return v.strip()


class CodecValidationRequest(BaseModel):
    """Request model for codec validation."""

    video_codec: Optional[str] = Field(None, description="Video codec name (e.g., 'h264', 'hevc')")
    audio_codec: Optional[str] = Field(None, description="Audio codec name (e.g., 'aac', 'opus')")


class VideoValidationResponse(BaseModel):
    """Response model for video validation."""

    validation_id: str = Field(..., description="Unique validation ID")
    url: str = Field(..., description="Validated video URL")
    timestamp: str = Field(..., description="Validation timestamp (ISO 8601)")
    valid: bool = Field(..., description="Whether video passed basic validation")
    is_compatible: bool = Field(..., description="Whether video is compatible with Telegram")
    video_codec: Optional[str] = Field(None, description="Detected video codec")
    audio_codec: Optional[str] = Field(None, description="Detected audio codec")
    format: Optional[str] = Field(None, description="Detected format")
    has_orientation: bool = Field(..., description="Whether video has orientation metadata")
    orientation_value: Optional[int] = Field(None, description="Orientation value (0, 90, 180, 270)")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    transcoding_required: bool = Field(..., description="Whether transcoding is required")
    transcoding_reasons: List[str] = Field(default_factory=list, description="Reasons for transcoding")


class CodecValidationResponse(BaseModel):
    """Response model for codec validation."""

    valid: bool = Field(..., description="Whether codecs are compatible")
    errors: List[str] = Field(default_factory=list, description="Validation errors")


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors."""

    validation_id: str = Field(..., description="Validation ID")
    url: Optional[str] = Field(None, description="Video URL")
    timestamp: Optional[str] = Field(None, description="Validation timestamp")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    transcoding_required: bool = Field(False, description="Whether transcoding is required")
    transcoding_reasons: List[str] = Field(default_factory=list, description="Reasons for transcoding")


@router.post("/validate", response_model=VideoValidationResponse)
async def validate_video(
    request: VideoValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate video URL for Telegram compatibility.

    Checks:
    - Video accessibility
    - Codec compatibility (h264, h265 for video; aac, mp3, opus for audio)
    - Format compatibility
    - Video orientation metadata
    - Transcoding requirements

    Returns validation result with compatibility status and recommendations.
    Results are cached for 1 hour in Redis.
    """
    try:
        service = VideoValidationService(db_session=db)

        result = await service.validate_video(
            url=request.url,
            timeout=request.timeout,
            cache_result=request.cache_result
        )

        return VideoValidationResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Video validation failed: {str(e)}"
        )


@router.get("/validate/{validation_id}", response_model=VideoValidationResponse)
async def get_validation_result(
    validation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cached validation result by ID.

    Returns the validation result from cache if available.
    Returns 404 if validation ID is not found or expired.
    """
    try:
        service = VideoValidationService(db_session=db)

        result = await service.get_validation_result(validation_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Validation result not found or expired: {validation_id}"
            )

        return VideoValidationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve validation result: {str(e)}"
        )


@router.get("/validate", response_model=List[Dict[str, Any]])
async def list_validations(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List recent video validations.

    Returns a list of recent validation IDs and basic info.
    Results are best-effort and depend on Redis availability.
    """
    try:
        service = VideoValidationService(db_session=db)

        results = await service.list_recent_validations(limit=limit)

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list validations: {str(e)}"
        )


@router.post("/validate/codecs", response_model=CodecValidationResponse)
async def validate_codecs(
    request: CodecValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate video and audio codecs for Telegram compatibility.

    Quick validation without downloading the full video.
    Useful for checking codec compatibility before uploading.
    """
    try:
        service = VideoValidationService(db_session=db)

        result = await service.validate_codecs(
            video_codec=request.video_codec,
            audio_codec=request.audio_codec
        )

        return CodecValidationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Codec validation failed: {str(e)}"
        )


@router.get("/errors/{validation_id}", response_model=ValidationErrorResponse)
async def get_validation_errors(
    validation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get validation errors and transcoding recommendations.

    Returns detailed error information and actionable recommendations
    for fixing video compatibility issues.
    """
    try:
        service = VideoValidationService(db_session=db)

        result = await service.get_validation_result(validation_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Validation result not found or expired: {validation_id}"
            )

        # Extract error information
        errors = result.get("errors", [])
        transcoding_required = result.get("transcoding_required", False)
        transcoding_reasons = result.get("transcoding_reasons", [])

        return ValidationErrorResponse(
            validation_id=validation_id,
            url=result.get("url"),
            timestamp=result.get("timestamp"),
            errors=errors,
            transcoding_required=transcoding_required,
            transcoding_reasons=transcoding_reasons
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve validation errors: {str(e)}"
        )


@router.delete("/validate/{validation_id}")
async def delete_validation_result(
    validation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete cached validation result.

    Removes the validation result from Redis cache.
    """
    try:
        service = VideoValidationService(db_session=db)

        success = await service.delete_validation_result(validation_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Validation result not found: {validation_id}"
            )

        return {"message": f"Validation result deleted: {validation_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete validation result: {str(e)}"
        )
