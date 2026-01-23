"""
Feature 022 Phase 2: Stream Quality Schemas for Admin API

Schemas для отображения информации о качестве потока в admin dashboard.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class AudioQualityMetrics(BaseModel):
    """Метрики качества аудио"""
    codec: Optional[str] = None
    bitrate_kbps: Optional[int] = None
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None
    duration_sec: Optional[float] = None
    quality: Optional[str] = None  # low, medium, high, lossless


class VideoQualityMetrics(BaseModel):
    """Метрики качества видео"""
    codec: Optional[str] = None
    bitrate_kbps: Optional[int] = None
    resolution: Optional[str] = None  # e.g. "1920x1080"
    fps: Optional[float] = None
    duration_sec: Optional[float] = None
    quality: Optional[str] = None  # low, medium, high, ultra


class PerformanceMetrics(BaseModel):
    """Метрики производительности стрима (из логов FFmpeg)"""
    dropped_frames: Optional[int] = 0
    speed: Optional[float] = None
    fps: Optional[float] = None
    bitrate_kbps: Optional[float] = None


class StreamQualityResponse(BaseModel):
    """
    Feature 022 Phase 2: Ответ с информацией о качестве потока
    
    Использует StreamQuality от streamer/ffprobe_utils.py
    """
    url: str
    audio: Optional[AudioQualityMetrics] = None
    video: Optional[VideoQualityMetrics] = None
    performance: Optional[PerformanceMetrics] = None
    is_audio_only: bool = False
    is_video_only: bool = False
    has_both: bool = False
    overall_quality: str  # low, medium, high, lossless, ultra, unknown
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/stream.mp3",
                "audio": {
                    "codec": "opus",
                    "bitrate_kbps": 96,
                    "sample_rate_hz": 48000,
                    "channels": 2,
                    "duration_sec": 180.5,
                    "quality": "medium"
                },
                "video": None,
                "is_audio_only": True,
                "is_video_only": False,
                "has_both": False,
                "overall_quality": "medium"
            }
        }


class StreamQualityStatus(BaseModel):
    """Статус анализа качества потока"""
    stream_id: str
    quality: Optional[StreamQualityResponse] = None
    analyzed_at: Optional[str] = None  # ISO 8601 timestamp
    status: str  # analyzing, success, error
    error_message: Optional[str] = None


# ========== Feature 022 Phase 3: Trends & Alerts ==========

from datetime import datetime


class QualityHistoryPoint(BaseModel):
    """Одна точка истории качества"""
    timestamp: datetime
    overall_quality: str
    audio_quality: Optional[str] = None
    audio_bitrate_kbps: Optional[int] = None
    video_quality: Optional[str] = None
    video_bitrate_kbps: Optional[int] = None
    video_resolution: Optional[str] = None
    video_fps: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


class QualityTrendData(BaseModel):
    """
    Feature 022 Phase 3: Данные тренда качества за 24 часа
    
    Используется для отображения графиков в dashboard
    """
    stream_url: str
    stream_name: Optional[str] = None
    
    # История (точки за 24 часа или за выбранный период)
    history: list[QualityHistoryPoint] = []
    
    # Статистика
    average_quality: str  # Среднее качество за период
    min_quality: str  # Минимальное качество
    max_quality: str  # Максимальное качество
    
    audio_avg_bitrate_kbps: Optional[int] = None
    video_avg_bitrate_kbps: Optional[int] = None
    video_avg_resolution: Optional[str] = None
    
    # Успешность анализа
    success_rate: float  # 0-1, процент успешных анализов
    
    # Период данных
    period_start: datetime
    period_end: datetime
    samples_count: int


class QualityAlertConfigUpdate(BaseModel):
    """
    Feature 022 Phase 3: Запрос для создания/обновления alert конфигурации
    """
    stream_url: str
    stream_name: Optional[str] = None
    
    # Пороги качества
    min_overall_quality: Optional[str] = None  # low, medium, high, lossless, ultra
    min_audio_quality: Optional[str] = None
    min_video_quality: Optional[str] = None
    
    # Пороги bitrate
    min_audio_bitrate_kbps: Optional[int] = None
    min_video_bitrate_kbps: Optional[int] = None
    
    # Пороги разрешения
    min_video_resolution: Optional[str] = None  # "1280x720"
    min_video_fps: Optional[float] = None
    
    # Поведение
    enabled: Optional[bool] = None
    notify_on_degradation: Optional[bool] = None
    notify_on_recovery: Optional[bool] = None
    consecutive_failures: Optional[int] = None
    
    # Каналы уведомлений
    alert_channels: Optional[Dict[str, list]] = None


class QualityAlertConfigResponse(BaseModel):
    """Ответ с конфигурацией alert"""
    id: int
    stream_url: str
    stream_name: Optional[str]
    min_overall_quality: str
    min_audio_quality: Optional[str]
    min_video_quality: Optional[str]
    min_audio_bitrate_kbps: Optional[int]
    min_video_bitrate_kbps: Optional[int]
    min_video_resolution: Optional[str]
    min_video_fps: Optional[float]
    enabled: bool
    notify_on_degradation: bool
    notify_on_recovery: bool
    consecutive_failures: int
    alert_channels: Dict[str, list]
    last_alert_at: Optional[datetime]
    last_alert_type: Optional[str]
    consecutive_failures_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class QualityAlertEvent(BaseModel):
    """
    Событие alert при падении качества
    """
    stream_url: str
    stream_name: Optional[str]
    alert_type: str  # degradation, recovery, offline
    severity: str  # info, warning, error
    message: str
    previous_quality: Optional[str]
    current_quality: Optional[str]
    failed_checks: list[str]  # Какие пороги были нарушены
    triggered_at: datetime


# ========== Feature 010: Encoding Profiles ==========


class EncodingProfileUpdate(BaseModel):
    """
    Feature 010: Запрос для создания/обновления encoding profile

    Позволяет настраивать кодеки, битрейт и разрешение для канала
    """
    # Видеокодек: h264, h265, vp9
    video_codec: Optional[str] = None

    # Аудиокодек: aac, mp3, opus
    audio_codec: Optional[str] = None

    # Битрейт видео в kbps (килобит в секунду)
    video_bitrate: Optional[int] = None

    # Битрейт аудио в kbps
    audio_bitrate: Optional[int] = None

    # Разрешение видео, например "1920x1080", "1280x720"
    resolution: Optional[str] = None

    # Дополнительные параметры FFmpeg
    custom_ffmpeg_args: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "video_codec": "h264",
                "audio_codec": "aac",
                "video_bitrate": 2500,
                "audio_bitrate": 128,
                "resolution": "1920x1080",
                "custom_ffmpeg_args": "-preset fast -tune zerolatency"
            }
        }


class EncodingProfileResponse(BaseModel):
    """
    Feature 010: Ответ с encoding profile канала
    """
    id: int
    channel_id: int
    video_codec: str
    audio_codec: str
    video_bitrate: Optional[int]
    audio_bitrate: Optional[int]
    resolution: Optional[str]
    custom_ffmpeg_args: Optional[str]
    is_active: bool  # Используется ли этот профиль сейчас
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CodecValidationResult(BaseModel):
    """
    Feature 010: Результат валидации кодека

    Возвращает информацию о поддержке кодека и рекомендации
    """
    # Валидна ли комбинация кодеков
    is_valid: bool

    # Выбранные кодеки
    video_codec: str
    audio_codec: str

    # Поддерживается ли видеокодек в FFmpeg
    video_codec_supported: bool

    # Поддерживается ли аудиокодек в FFmpeg
    audio_codec_supported: bool

    # Список поддерживаемых видеокодеков
    supported_video_codecs: list[str]

    # Список поддерживаемых аудиокодеков
    supported_audio_codecs: list[str]

    # Предупреждения (некритичные проблемы)
    warnings: list[str] = []

    # Ошибки (критичные проблемы, делающие комбинацию непригодной)
    errors: list[str] = []

    # Рекомендации по оптимизации
    recommendations: list[str] = []

    # Совместимость с Telegram (если применимо)
    telegram_compatible: bool

    class Config:
        schema_extra = {
            "example": {
                "is_valid": True,
                "video_codec": "h264",
                "audio_codec": "aac",
                "video_codec_supported": True,
                "audio_codec_supported": True,
                "supported_video_codecs": ["h264", "h265", "vp9"],
                "supported_audio_codecs": ["aac", "mp3", "opus"],
                "warnings": ["H.265 требует больше CPU ресурсов"],
                "errors": [],
                "recommendations": ["Используйте H.264 для максимальной совместимости"],
                "telegram_compatible": True
            }
        }

