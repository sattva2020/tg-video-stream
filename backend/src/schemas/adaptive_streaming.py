"""
Feature 009 Phase 2: Adaptive Streaming Schemas for Admin API

Schemas для управления конфигурацией адаптивного битрейта и мониторинга пропускной способности.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ========== Enums ==========

class QualityLevel(str, Enum):
    """Уровни качества потока"""
    LOW = "low"      # 360p
    MEDIUM = "medium" # 480p
    HIGH = "high"     # 720p
    ULTRA = "ultra"   # 1080p


class DeviceType(str, Enum):
    """Типы устройств для автоматической оптимизации"""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    TV = "tv"
    UNKNOWN = "unknown"


# ========== Quality Profiles ==========

class QualityProfile(BaseModel):
    """Профиль качества с настройками кодирования"""
    resolution: str = Field(..., description="Разрешение в формате 'WIDTHxHEIGHT', например '1280x720'")
    video_bitrate_kbps: int = Field(..., ge=64, le=20000, description="Видеобитрейт в Kbps")
    audio_bitrate_kbps: int = Field(..., ge=32, le=320, description="Аудиобитрейт в Kbps")
    fps: Optional[float] = Field(None, ge=15, le=60, description="Кадров в секунду")
    codec: Optional[str] = Field("h264", description="Видеокодек")

    class Config:
        schema_extra = {
            "example": {
                "resolution": "1280x720",
                "video_bitrate_kbps": 3000,
                "audio_bitrate_kbps": 128,
                "fps": 30.0,
                "codec": "h264"
            }
        }


class DeviceRule(BaseModel):
    """Правило для конкретного типа устройства"""
    max_quality: QualityLevel = Field(..., description="Максимальное качество для этого устройства")
    bandwidth_multiplier: float = Field(..., ge=0.1, le=1.0, description="Множитель пропускной способности")
    preferred_resolution: Optional[str] = Field(None, description="Предпочтительное разрешение")

    class Config:
        schema_extra = {
            "example": {
                "max_quality": "high",
                "bandwidth_multiplier": 0.7,
                "preferred_resolution": "1280x720"
            }
        }


# ========== Bandwidth Detection ==========

class BandwidthMeasurement(BaseModel):
    """Результат измерения пропускной способности"""
    bandwidth_kbps: float = Field(..., description="Измеренная пропускная способность в Kbps")
    latency_ms: Optional[float] = Field(None, description="Задержка в миллисекундах")
    packet_loss: Optional[float] = Field(None, ge=0.0, le=1.0, description="Потеря пакетов (0-1)")
    measured_at: datetime = Field(default_factory=datetime.now, description="Время измерения")
    measurement_method: str = Field("http", description="Метод измерения: http, websocket, webrtc")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в измерении (0-1)")


class BandwidthStatus(BaseModel):
    """Статус пропускной способности сети"""
    current_bandwidth_kbps: Optional[float] = None
    smoothed_bandwidth_kbps: Optional[float] = None
    recommended_quality: Optional[QualityLevel] = None
    current_quality: Optional[QualityLevel] = None
    device_type: DeviceType = DeviceType.UNKNOWN
    last_measurement: Optional[BandwidthMeasurement] = None
    adaptation_enabled: bool = False
    seconds_since_last_measurement: Optional[int] = None


# ========== Adaptive Stream Config Schemas ==========

class AdaptiveStreamConfigBase(BaseModel):
    """Базовая схема для конфигурации адаптивного стрима"""
    enabled: bool = Field(True, description="Включена ли адаптивная трансляция")
    default_quality: QualityLevel = Field(QualityLevel.HIGH, description="Качество по умолчанию")
    min_quality: QualityLevel = Field(QualityLevel.LOW, description="Минимальное качество")
    max_quality: QualityLevel = Field(QualityLevel.ULTRA, description="Максимальное качество")

    # Bandwidth Thresholds (Kbps)
    bandwidth_threshold_low_kbps: int = Field(500, ge=64, le=20000, description="Порог для low quality (Kbps)")
    bandwidth_threshold_medium_kbps: int = Field(1500, ge=64, le=20000, description="Порог для medium quality (Kbps)")
    bandwidth_threshold_high_kbps: int = Field(3000, ge=64, le=20000, description="Порог для high quality (Kbps)")
    bandwidth_threshold_ultra_kbps: int = Field(6000, ge=64, le=20000, description="Порог для ultra quality (Kbps)")

    # Adaptive Settings
    adaptation_interval_seconds: int = Field(30, ge=5, le=300, description="Интервал проверки пропускной способности (сек)")
    bandwidth_smoothing_factor: float = Field(0.3, ge=0.0, le=1.0, description="Коэффициент сглаживания (0-1)")
    consecutive_measurements_required: int = Field(3, ge=1, le=10, description="Измерений для переключения качества")

    # Device Rules
    device_rules: Optional[Dict[str, DeviceRule]] = Field(None, description="Правила для устройств")

    # Quality Profiles
    quality_profiles: Optional[Dict[str, QualityProfile]] = Field(None, description="Пользовательские профили качества")

    # Monitoring
    enable_bandwidth_monitoring: bool = Field(True, description="Включить мониторинг пропускной способности")
    enable_quality_logging: bool = Field(True, description="Включить логирование изменений качества")

    @validator('bandwidth_threshold_low_kbps', 'bandwidth_threshold_medium_kbps',
               'bandwidth_threshold_high_kbps', 'bandwidth_threshold_ultra_kbps')
    def validate_thresholds_order(cls, v, values):
        """Проверка правильности порядка порогов"""
        # This will be validated with all fields present
        return v

    @validator('max_quality')
    def validate_quality_range(cls, v, values):
        """Проверка что max_quality >= min_quality"""
        if 'min_quality' in values:
            min_q = values['min_quality']
            quality_order = ['low', 'medium', 'high', 'ultra']
            if quality_order.index(v) < quality_order.index(min_q):
                raise ValueError('max_quality must be >= min_quality')
        return v

    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "default_quality": "high",
                "min_quality": "low",
                "max_quality": "ultra",
                "bandwidth_threshold_low_kbps": 500,
                "bandwidth_threshold_medium_kbps": 1500,
                "bandwidth_threshold_high_kbps": 3000,
                "bandwidth_threshold_ultra_kbps": 6000,
                "adaptation_interval_seconds": 30,
                "bandwidth_smoothing_factor": 0.3,
                "consecutive_measurements_required": 3,
                "device_rules": {
                    "mobile": {
                        "max_quality": "high",
                        "bandwidth_multiplier": 0.7
                    }
                },
                "quality_profiles": {
                    "low": {
                        "resolution": "640x360",
                        "video_bitrate_kbps": 500,
                        "audio_bitrate_kbps": 64
                    }
                },
                "enable_bandwidth_monitoring": True,
                "enable_quality_logging": True
            }
        }


class AdaptiveStreamConfigCreate(AdaptiveStreamConfigBase):
    """Схема для создания конфигурации адаптивного стрима"""
    stream_id: str = Field(..., description="ID потока (GUID)")


class AdaptiveStreamConfigUpdate(BaseModel):
    """Схема для обновления конфигурации адаптивного стрима"""
    enabled: Optional[bool] = None
    default_quality: Optional[QualityLevel] = None
    min_quality: Optional[QualityLevel] = None
    max_quality: Optional[QualityLevel] = None

    bandwidth_threshold_low_kbps: Optional[int] = Field(None, ge=64, le=20000)
    bandwidth_threshold_medium_kbps: Optional[int] = Field(None, ge=64, le=20000)
    bandwidth_threshold_high_kbps: Optional[int] = Field(None, ge=64, le=20000)
    bandwidth_threshold_ultra_kbps: Optional[int] = Field(None, ge=64, le=20000)

    adaptation_interval_seconds: Optional[int] = Field(None, ge=5, le=300)
    bandwidth_smoothing_factor: Optional[float] = Field(None, ge=0.0, le=1.0)
    consecutive_measurements_required: Optional[int] = Field(None, ge=1, le=10)

    device_rules: Optional[Dict[str, DeviceRule]] = None
    quality_profiles: Optional[Dict[str, QualityProfile]] = None

    enable_bandwidth_monitoring: Optional[bool] = None
    enable_quality_logging: Optional[bool] = None


class AdaptiveStreamConfigResponse(AdaptiveStreamConfigBase):
    """Схема ответа с конфигурацией адаптивного стрима"""
    id: int
    stream_id: str
    statistics: Optional[Dict[str, Any]] = Field(None, description="Статистика адаптивной трансляции")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "stream_id": "123e4567-e89b-12d3-a456-426614174000",
                "enabled": True,
                "default_quality": "high",
                "min_quality": "low",
                "max_quality": "ultra",
                "bandwidth_threshold_low_kbps": 500,
                "bandwidth_threshold_medium_kbps": 1500,
                "bandwidth_threshold_high_kbps": 3000,
                "bandwidth_threshold_ultra_kbps": 6000,
                "adaptation_interval_seconds": 30,
                "bandwidth_smoothing_factor": 0.3,
                "consecutive_measurements_required": 3,
                "device_rules": None,
                "quality_profiles": None,
                "enable_bandwidth_monitoring": True,
                "enable_quality_logging": True,
                "statistics": {
                    "quality_changes": 5,
                    "last_quality": "high",
                    "avg_bandwidth_kbps": 2500
                },
                "created_at": "2024-01-23T10:00:00Z",
                "updated_at": "2024-01-23T10:00:00Z"
            }
        }


# ========== Quality Change Events ==========

class QualityChangeEvent(BaseModel):
    """Событие изменения качества потока"""
    id: int
    stream_id: str
    previous_quality: Optional[QualityLevel] = None
    new_quality: QualityLevel
    bandwidth_kbps: Optional[float] = None
    reason: str = Field(..., description="Причина изменения: bandwidth, device, manual, startup")
    device_type: Optional[DeviceType] = None
    triggered_at: datetime

    class Config:
        from_attributes = True


class QualityChangeHistory(BaseModel):
    """История изменений качества для потока"""
    stream_id: str
    stream_name: Optional[str] = None
    events: list[QualityChangeEvent] = []
    total_changes: int
    current_quality: QualityLevel
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ========== Adaptive Streaming Status ==========

class AdaptiveStreamingStatus(BaseModel):
    """Полный статус адаптивного стрима для потока"""
    stream_id: str
    stream_name: Optional[str] = None

    # Configuration
    config: Optional[AdaptiveStreamConfigResponse] = None

    # Current State
    current_quality: QualityLevel
    current_bandwidth_kbps: Optional[float] = None
    smoothed_bandwidth_kbps: Optional[float] = None
    device_type: DeviceType

    # Status Flags
    adaptive_enabled: bool
    monitoring_enabled: bool
    is_adapting: bool = False

    # Statistics
    total_quality_changes: int = 0
    last_quality_change: Optional[datetime] = None
    last_bandwidth_measurement: Optional[datetime] = None

    # Recommended Actions
    recommended_quality: Optional[QualityLevel] = None
    recommended_action: Optional[str] = None

    updated_at: datetime


# ========== Bandwidth Detection Request ==========

class BandwidthDetectionRequest(BaseModel):
    """Запрос на измерение пропускной способности"""
    stream_id: str
    timeout_seconds: int = Field(10, ge=1, le=30, description="Таймаут измерения")
    measurement_method: str = Field("http", description="Метод: http, websocket, webrtc")
    force_measurement: bool = Field(False, description="Принудительное измерение (игнорировать кэш)")


class BandwidthDetectionResponse(BaseModel):
    """Результат измерения пропускной способности"""
    stream_id: str
    measurement: BandwidthMeasurement
    recommended_quality: QualityLevel
    current_config: Optional[AdaptiveStreamConfigResponse] = None
    device_type: DeviceType
    success: bool
    error_message: Optional[str] = None
