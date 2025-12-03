"""
API routes for playback control (speed, pitch, seek, rewind).

Endpoints:
  PUT /api/v1/playback/speed - Set playback speed (0.5x - 2.0x)
  PUT /api/v1/playback/pitch - Adjust pitch (±12 semitones)
  POST /api/v1/playback/seek - Seek to specific position
  POST /api/v1/playback/rewind - Rewind by N seconds
  GET /api/v1/playback/position - Get current playback position
  GET /api/v1/playback/settings - Get user's playback settings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from typing import Optional
import logging
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_playback_service
from ...services.playback_service import PlaybackService
from ...models.user import User
from ...database import get_db
from src.config.equalizer_presets import (
    BAND_FREQUENCIES,
    PRESET_CATEGORIES,
    list_presets_by_category,
    list_presets_grouped_with_metadata,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/playback", tags=["playback"])


# Request/Response Models
class SetSpeedRequest(BaseModel):
    """Request to set playback speed."""
    speed: float = Field(ge=0.5, le=2.0, description="Playback speed multiplier (0.5x - 2.0x)")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class SetPitchRequest(BaseModel):
    """Request to adjust pitch."""
    semitones: int = Field(ge=-12, le=12, description="Pitch adjustment in semitones (±12)")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class SeekRequest(BaseModel):
    """Request to seek to a specific position."""
    position_seconds: int = Field(ge=0, description="Target position in seconds")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class RewindRequest(BaseModel):
    """Request to rewind by N seconds."""
    seconds: int = Field(ge=1, le=300, description="Number of seconds to rewind (1-300)")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class SetEqualizerPresetRequest(BaseModel):
    """Request to set equalizer preset."""
    preset_name: str = Field(..., description="Name of the equalizer preset")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class SetEqualizerCustomRequest(BaseModel):
    """Request to set custom equalizer bands."""
    bands: list[float] = Field(..., min_length=10, max_length=10, description="10 band values in dB")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class UpdateEqualizerRequest(BaseModel):
    """Unified equalizer update request (preset or custom bands)."""

    preset_name: Optional[str] = Field(
        None,
        description="Preset name to apply (flat, rock, meditation, etc.)",
    )
    bands: Optional[list[float]] = Field(
        None,
        min_length=10,
        max_length=10,
        description="Custom 10-band equalizer values in dB",
    )
    channel_id: Optional[int] = Field(
        None,
        description="Telegram channel ID for multi-channel support",
    )

    @model_validator(mode="after")
    def _validate_choice(self) -> "UpdateEqualizerRequest":  # type: ignore[override]
        preset = self.preset_name
        bands = self.bands

        if not preset and bands is None:
            raise ValueError("Either preset_name or bands must be provided")
        if preset and bands is not None:
            raise ValueError("Provide preset_name or bands, not both")
        return self


class EqualizerPresetMetadata(BaseModel):
    """Metadata describing a single equalizer preset."""

    name: str
    display_name: str
    description: str
    category: str
    bands: list[float] = Field(..., min_length=10, max_length=10)


class EqualizerPresetCategory(BaseModel):
    """Group of presets that belong to the same category."""

    id: str = Field(..., description="Category identifier from config")
    label: str = Field(..., description="Human readable category name")
    presets: list[EqualizerPresetMetadata]


class EqualizerPresetListResponse(BaseModel):
    """Response describing all available presets grouped by category."""

    total: int
    categories: list[EqualizerPresetCategory]
    band_frequencies: list[dict]


def _build_preset_catalog() -> tuple[list[EqualizerPresetCategory], int]:
    """Собрать метаданные пресетов по категориям."""

    grouped = list_presets_grouped_with_metadata()
    categories: list[EqualizerPresetCategory] = []
    total = 0

    for category_id, presets in grouped.items():
        metadata_items = [EqualizerPresetMetadata(**preset) for preset in presets]
        label = PRESET_CATEGORIES.get(category_id, category_id.title())
        categories.append(
            EqualizerPresetCategory(id=category_id, label=label, presets=metadata_items)
        )
        total += len(metadata_items)

    categories.sort(key=lambda category: category.label)
    return categories, total


class PlaybackSettingsResponse(BaseModel):
    """User's playback settings."""
    speed: float
    pitch_correction: bool
    equalizer_preset: str
    language: str
    created_at: str
    updated_at: str


class PlaybackPositionResponse(BaseModel):
    """Current playback position."""
    current_position_seconds: int
    total_duration_seconds: int
    is_playing: bool


class SpeedResponse(BaseModel):
    """Response after setting speed."""
    speed: float
    message: str


class PitchResponse(BaseModel):
    """Response after adjusting pitch."""
    semitones: int
    message: str


class SeekResponse(BaseModel):
    """Response after seeking."""
    position_seconds: int
    message: str


# Route Handlers

@router.put("/speed", response_model=SpeedResponse, status_code=200)
async def set_speed(
    request: SetSpeedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set playback speed for the current stream.
    
    **Permission**: User must have active playback session
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Example**:
    ```json
    {
      "speed": 1.5,
      "channel_id": 12345
    }
    ```
    """
    try:
        channel_id = request.channel_id or current_user.id
        playback_service = PlaybackService(db)
        
        # Set speed via service
        result = playback_service.set_speed(
            user_id=current_user.id,
            channel_id=channel_id,
            speed=request.speed
        )
        
        logger.info(f"User {current_user.id} set speed to {result['speed']}x on channel {channel_id}")
        
        return SpeedResponse(
            speed=result['speed'],
            message=result['message']
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting speed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set speed")


@router.put("/pitch", response_model=PitchResponse, status_code=200)
async def set_pitch(
    request: SetPitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Adjust pitch for the current stream.
    
    **Permission**: User must have active playback session
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Example**:
    ```json
    {
      "semitones": 2,
      "channel_id": 12345
    }
    ```
    """
    try:
        channel_id = request.channel_id or current_user.id
        playback_service = PlaybackService(db)
        
        # Set pitch via service
        result = playback_service.set_pitch(
            user_id=current_user.id,
            channel_id=channel_id,
            semitones=request.semitones
        )
        
        logger.info(f"User {current_user.id} adjusted pitch to {result['pitch_semitones']} semitones on channel {channel_id}")
        
        return PitchResponse(
            semitones=result['pitch_semitones'],
            message=result['message']
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting pitch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set pitch")


@router.post("/seek", response_model=SeekResponse, status_code=200)
async def seek(
    request: SeekRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Seek to a specific position in the current track.
    
    **Permission**: User must have active playback session
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Example**:
    ```json
    {
      "position_seconds": 90,
      "channel_id": 12345
    }
    ```
    """
    try:
        channel_id = request.channel_id or current_user.id
        playback_service = PlaybackService(db)
        
        # Seek via service
        new_position = playback_service.seek_to(
            user_id=current_user.id,
            channel_id=channel_id,
            position_seconds=request.position_seconds
        )
        
        logger.info(f"User {current_user.id} seeked to {new_position}s on channel {channel_id}")
        
        return SeekResponse(
            position_seconds=new_position,
            message=f"Playback seeked to {new_position} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error seeking: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to seek")


@router.post("/rewind", response_model=SeekResponse, status_code=200)
async def rewind(
    request: RewindRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rewind the current track by N seconds.
    
    **Permission**: User must have active playback session
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Example**:
    ```json
    {
      "seconds": 30,
      "channel_id": 12345
    }
    ```
    """
    try:
        channel_id = request.channel_id or current_user.id
        playback_service = PlaybackService(db)
        
        # Rewind via service
        new_position = playback_service.rewind(
            user_id=current_user.id,
            channel_id=channel_id,
            seconds=request.seconds
        )
        
        logger.info(f"User {current_user.id} rewinded {request.seconds}s on channel {channel_id}")
        
        return SeekResponse(
            position_seconds=new_position,
            message=f"Rewinded {request.seconds} seconds (now at {new_position}s)"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error rewinding: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to rewind")


@router.get("/position", response_model=PlaybackPositionResponse, status_code=200)
async def get_position(
    channel_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current playback position for active stream.
    
    **Permission**: User must have active playback session
    
    **Rate Limit**: 200 requests/minute per user (Elevated)
    
    **Query Parameters**:
    - `channel_id`: Optional Telegram channel ID (defaults to user's primary channel)
    """
    try:
        channel_id = channel_id or current_user.id
        playback_service = PlaybackService(db)
        
        # Get position via service
        position_data = playback_service.get_position(
            user_id=current_user.id,
            channel_id=channel_id
        )
        
        return PlaybackPositionResponse(**position_data)
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get position")


@router.get("/settings", response_model=PlaybackSettingsResponse, status_code=200)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's playback settings (speed, pitch, EQ, language).
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 200 requests/minute per user (Elevated)
    """
    try:
        playback_service = PlaybackService(db)
        settings = playback_service.get_settings(user_id=current_user.id)
        
        return PlaybackSettingsResponse(**settings)
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get settings")


# ==============================================================================
# Equalizer Endpoints
# ==============================================================================

@router.get("/equalizer", response_model=dict, status_code=200)
async def get_equalizer(
    channel_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    playback_service: PlaybackService = Depends(get_playback_service),
):
    """
    Get current equalizer settings.
    
    Returns:
        {
            "preset": "meditation",
            "bands": [3, 2, 1, 0, -1, -2, -1, 0, 1, 2],
            "available_presets": {
                "standard": ["flat", "rock", "jazz", ...],
                "meditation": ["meditation", "relax", ...]
            }
        }
    """
    try:
        eq_state = playback_service.get_equalizer_state(current_user.id, channel_id)
        presets_by_category = list_presets_by_category()
        categories, total = _build_preset_catalog()
        preset_catalog = {
            "total": total,
            "categories": [category.model_dump() for category in categories],
            "band_frequencies": BAND_FREQUENCIES,
        }
        
        return {
            "preset": eq_state["preset"],
            "bands": eq_state["bands"],
            "available_presets": presets_by_category,
            "preset_catalog": preset_catalog,
        }
    except Exception as e:
        logger.error(f"Error getting equalizer state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get equalizer state"
        )


@router.get("/equalizer/presets", response_model=EqualizerPresetListResponse, status_code=200)
async def list_equalizer_presets(current_user: User = Depends(get_current_user)):
    """Вернуть полные метаданные пресетов для UI."""

    _ = current_user  # ensure dependency evaluated for auth
    categories, total = _build_preset_catalog()
    return EqualizerPresetListResponse(
        total=total,
        categories=categories,
        band_frequencies=BAND_FREQUENCIES,
    )


@router.put("/equalizer", response_model=dict, status_code=200)
async def update_equalizer(
    request: UpdateEqualizerRequest,
    current_user: User = Depends(get_current_user),
    playback_service: PlaybackService = Depends(get_playback_service),
):
    """Применить пресет или пользовательские полосы через единый endpoint."""

    try:
        if request.preset_name:
            result = playback_service.set_equalizer_preset(
                current_user.id,
                request.preset_name,
                request.channel_id,
            )
        else:
            if request.bands is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="bands are required when preset_name is not provided",
                )

            result = playback_service.set_equalizer_custom(
                current_user.id,
                request.bands,
                request.channel_id,
            )

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error("Error updating equalizer", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update equalizer",
        )


@router.put("/equalizer/preset", response_model=dict, status_code=200)
async def set_equalizer_preset(
    request: SetEqualizerPresetRequest,
    current_user: User = Depends(get_current_user),
    playback_service: PlaybackService = Depends(get_playback_service),
):
    """
    Set equalizer preset.
    
    Available presets:
    - Standard: flat, rock, jazz, classical, voice, bass_boost
    - Meditation: meditation, relax, new_age, ambient, sleep, nature
    """
    try:
        result = playback_service.set_equalizer_preset(
            current_user.id,
            request.preset_name,
            request.channel_id
        )
        
        logger.info(
            f"User {current_user.id} set equalizer preset '{request.preset_name}' "
            f"for channel {request.channel_id}"
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting equalizer preset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def set_equalizer_custom(
    request: SetEqualizerCustomRequest,
    current_user: User = Depends(get_current_user),
    playback_service: PlaybackService = Depends(get_playback_service),
):
    """
    Set custom equalizer bands.
    
    Provide an array of 10 values (dB) for each frequency band:
    - Band 0: 29 Hz
    - Band 1: 59 Hz
    - Band 2: 119 Hz
    - Band 3: 237 Hz
    - Band 4: 474 Hz
    - Band 5: 947 Hz
    - Band 6: 1.9 kHz
    - Band 7: 3.8 kHz
    - Band 8: 7.5 kHz
    - Band 9: 15 kHz
    
    Values range: -24 to +12 dB (recommended: -6 to +6)
    """
    try:
        result = playback_service.set_equalizer_custom(
            current_user.id,
            request.bands,
            request.channel_id
        )
        
        logger.info(
            f"User {current_user.id} set custom equalizer bands for channel {request.channel_id}"
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting custom equalizer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )