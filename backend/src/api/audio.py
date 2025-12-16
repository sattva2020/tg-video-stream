"""
Audio processing API endpoints.

Интеграция с rust-transcoder для обработки аудио:
- Транскодирование с изменением скорости
- Применение эквалайзера
- Pitch correction
- Прокси к rust-transcoder сервису
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
import httpx
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.models.user import User
from src.models.playback_settings import PlaybackSettings
from src.config import settings

router = APIRouter(prefix="/audio", tags=["audio"])

# URL rust-transcoder сервиса
RUST_TRANSCODER_URL = settings.RUST_TRANSCODER_URL or "http://rust-transcoder:8090"


class TranscodeRequest(BaseModel):
    """Запрос на транскодирование аудио."""
    
    source_url: str = Field(..., description="URL источника аудио")
    format: str = Field(default="mp3", description="Формат выходного файла")
    codec: str = Field(default="libmp3lame", description="Аудио кодек")
    quality: str = Field(default="medium", description="Качество: low, medium, high")
    
    # Audio filters
    speed: Optional[float] = Field(None, ge=0.5, le=2.0, description="Скорость воспроизведения (0.5-2.0x)")
    pitch_correction: Optional[bool] = Field(True, description="Коррекция высоты тона при изменении скорости")
    eq_preset: Optional[str] = Field(None, description="Пресет эквалайзера: flat, rock, jazz, pop, classical")
    eq_custom: Optional[list[float]] = Field(None, description="10 полос эквалайзера в dB")
    volume: Optional[float] = Field(None, ge=0.0, le=2.0, description="Громкость (0.0-2.0)")

    @validator('eq_custom')
    def validate_eq_bands(cls, v):
        """Проверяет что эквалайзер содержит 10 полос."""
        if v is not None and len(v) != 10:
            raise ValueError('Эквалайзер должен содержать ровно 10 полос')
        return v


class TranscodeResponse(BaseModel):
    """Ответ на запрос транскодирования."""
    
    session_id: str
    message: str
    status: str = "processing"


@router.post("/transcode", response_model=TranscodeResponse)
async def transcode_audio(
    request: TranscodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Запускает транскодирование аудио через rust-transcoder.
    
    Применяет пользовательские настройки воспроизведения если они не указаны явно.
    """
    # Получаем настройки пользователя
    user_settings = db.query(PlaybackSettings).filter(
        PlaybackSettings.user_id == current_user.id
    ).first()
    
    # Применяем настройки по умолчанию если не указаны явно
    if request.speed is None and user_settings:
        request.speed = user_settings.speed
    
    if request.eq_preset is None and user_settings:
        request.eq_preset = user_settings.equalizer_preset
        if request.eq_preset == "custom" and user_settings.equalizer_custom:
            request.eq_custom = user_settings.equalizer_custom
    
    if request.pitch_correction is None and user_settings:
        request.pitch_correction = user_settings.pitch_correction
    
    # Формируем payload для rust-transcoder
    payload = {
        "source_url": request.source_url,
        "format": request.format,
        "codec": request.codec,
        "quality": request.quality,
        "audio_filters": {
            "speed": request.speed,
            "pitch_correction": request.pitch_correction,
            "eq_preset": request.eq_preset,
            "eq_custom": request.eq_custom,
            "volume": request.volume,
        }
    }
    
    # Отправляем запрос к rust-transcoder
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{RUST_TRANSCODER_URL}/api/v1/transcode",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return TranscodeResponse(**data)
            
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Rust-transcoder unavailable: {str(e)}"
            )


@router.get("/transcode/stream")
async def stream_transcoded_audio(
    session_id: str = Query(..., description="ID сессии транскодирования"),
    current_user: User = Depends(get_current_user)
):
    """
    Стримит транскодированное аудио от rust-transcoder к клиенту.
    
    Работает как прокси между клиентом и rust-transcoder.
    """
    async def stream_from_transcoder():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                f"{RUST_TRANSCODER_URL}/api/v1/transcode/stream?session_id={session_id}"
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk
    
    return StreamingResponse(
        stream_from_transcoder(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "X-Transcode-Session": session_id,
        }
    )


@router.get("/settings")
async def get_audio_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Возвращает текущие настройки аудио пользователя.
    """
    settings = db.query(PlaybackSettings).filter(
        PlaybackSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Возвращаем дефолтные настройки
        return {
            "speed": 1.0,
            "pitch_correction": True,
            "equalizer_preset": "flat",
            "equalizer_custom": None,
            "language": "ru",
            "theme": "light",
        }
    
    return {
        "speed": settings.speed,
        "pitch_correction": settings.pitch_correction,
        "equalizer_preset": settings.equalizer_preset,
        "equalizer_custom": settings.equalizer_custom,
        "language": settings.language,
        "theme": settings.theme,
        "auto_play": settings.auto_play,
        "shuffle": settings.shuffle,
        "repeat_mode": settings.repeat_mode,
    }


@router.put("/settings")
async def update_audio_settings(
    speed: Optional[float] = Query(None, ge=0.5, le=2.0),
    pitch_correction: Optional[bool] = None,
    equalizer_preset: Optional[str] = None,
    equalizer_custom: Optional[str] = None,  # JSON string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновляет настройки аудио пользователя.
    """
    settings = db.query(PlaybackSettings).filter(
        PlaybackSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Создаём новые настройки
        settings = PlaybackSettings(user_id=current_user.id)
        db.add(settings)
    
    # Обновляем только указанные поля
    if speed is not None:
        settings.speed = speed
    if pitch_correction is not None:
        settings.pitch_correction = pitch_correction
    if equalizer_preset is not None:
        settings.equalizer_preset = equalizer_preset
    if equalizer_custom is not None:
        import json
        settings.equalizer_custom = json.loads(equalizer_custom)
    
    db.commit()
    db.refresh(settings)
    
    return {"message": "Settings updated successfully"}


@router.get("/health")
async def check_transcoder_health():
    """
    Проверяет доступность rust-transcoder сервиса.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{RUST_TRANSCODER_URL}/health")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Rust-transcoder unavailable: {str(e)}"
        )
