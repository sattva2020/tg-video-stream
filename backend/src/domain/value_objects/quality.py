"""
Quality Value Object для Video/Audio качества.

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Stream Entity, broadcast settings.

**Phase 8**: Clean Architecture - Value Objects
**Reference**: specs/025-clean-architecture-rules/tasks.md T076
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


class VideoQuality(str, Enum):
    """
    Предустановленные уровни качества видео.
    
    Соответствуют стандартным разрешениям и битрейтам.
    """
    LOW = "low"          # 360p, 500 kbps
    MEDIUM = "medium"    # 480p, 1000 kbps
    HIGH = "high"        # 720p, 2500 kbps
    FULL_HD = "fullhd"   # 1080p, 5000 kbps
    ULTRA_HD = "ultrahd" # 4K, 15000 kbps


class AudioQuality(str, Enum):
    """
    Предустановленные уровни качества аудио.
    """
    LOW = "low"          # 64 kbps
    MEDIUM = "medium"    # 128 kbps
    HIGH = "high"        # 256 kbps
    LOSSLESS = "lossless" # 320 kbps / FLAC


@dataclass(frozen=True)
class Quality(ValueObject):
    """
    Quality settings для video/audio streams.

    **Properties**:
    - video_quality: Уровень качества видео
    - audio_quality: Уровень качества аудио
    - bitrate: Опциональный custom bitrate (kbps)
    - fps: Опциональный custom framerate

    **Validation Rules**:
    - video_quality должен быть валидным VideoQuality
    - audio_quality должен быть валидным AudioQuality
    - bitrate (если задан) >= 100 и <= 50000 kbps
    - fps (если задан) >= 1 и <= 120

    Examples:
        >>> quality = Quality(VideoQuality.HIGH, AudioQuality.MEDIUM)
        >>> quality.video_bitrate
        2500
        
        >>> quality = Quality(VideoQuality.LOW, AudioQuality.LOW, bitrate=800)
        >>> quality.bitrate
        800
    """

    video_quality: VideoQuality
    audio_quality: AudioQuality
    bitrate: Optional[int] = None  # Custom video bitrate in kbps
    fps: Optional[int] = None      # Custom framerate

    # Bitrate mappings (kbps)
    VIDEO_BITRATES = {
        VideoQuality.LOW: 500,
        VideoQuality.MEDIUM: 1000,
        VideoQuality.HIGH: 2500,
        VideoQuality.FULL_HD: 5000,
        VideoQuality.ULTRA_HD: 15000,
    }
    
    AUDIO_BITRATES = {
        AudioQuality.LOW: 64,
        AudioQuality.MEDIUM: 128,
        AudioQuality.HIGH: 256,
        AudioQuality.LOSSLESS: 320,
    }
    
    # Resolution mappings (width x height)
    VIDEO_RESOLUTIONS = {
        VideoQuality.LOW: (640, 360),
        VideoQuality.MEDIUM: (854, 480),
        VideoQuality.HIGH: (1280, 720),
        VideoQuality.FULL_HD: (1920, 1080),
        VideoQuality.ULTRA_HD: (3840, 2160),
    }

    # Limits
    MIN_BITRATE = 100
    MAX_BITRATE = 50000
    MIN_FPS = 1
    MAX_FPS = 120

    def __post_init__(self):
        """Валидация при создании."""
        # Validate video_quality
        if not isinstance(self.video_quality, VideoQuality):
            raise ValidationError(
                f"Invalid video quality: {self.video_quality}. "
                f"Must be one of: {[q.value for q in VideoQuality]}"
            )
        
        # Validate audio_quality
        if not isinstance(self.audio_quality, AudioQuality):
            raise ValidationError(
                f"Invalid audio quality: {self.audio_quality}. "
                f"Must be one of: {[q.value for q in AudioQuality]}"
            )
        
        # Validate custom bitrate if provided
        if self.bitrate is not None:
            if not self.MIN_BITRATE <= self.bitrate <= self.MAX_BITRATE:
                raise ValidationError(
                    f"Bitrate must be between {self.MIN_BITRATE} and {self.MAX_BITRATE} kbps"
                )
        
        # Validate custom fps if provided
        if self.fps is not None:
            if not self.MIN_FPS <= self.fps <= self.MAX_FPS:
                raise ValidationError(
                    f"FPS must be between {self.MIN_FPS} and {self.MAX_FPS}"
                )

    @property
    def video_bitrate(self) -> int:
        """
        Возвращает video bitrate в kbps.
        
        Использует custom bitrate если задан, иначе preset.
        """
        if self.bitrate is not None:
            return self.bitrate
        return self.VIDEO_BITRATES[self.video_quality]

    @property
    def audio_bitrate(self) -> int:
        """Возвращает audio bitrate в kbps."""
        return self.AUDIO_BITRATES[self.audio_quality]

    @property
    def total_bitrate(self) -> int:
        """Возвращает общий bitrate (video + audio) в kbps."""
        return self.video_bitrate + self.audio_bitrate

    @property
    def resolution(self) -> tuple[int, int]:
        """Возвращает разрешение (width, height)."""
        return self.VIDEO_RESOLUTIONS[self.video_quality]

    @property
    def width(self) -> int:
        """Возвращает ширину видео."""
        return self.resolution[0]

    @property
    def height(self) -> int:
        """Возвращает высоту видео."""
        return self.resolution[1]

    @property
    def framerate(self) -> int:
        """
        Возвращает framerate.
        
        Использует custom fps если задан, иначе 30.
        """
        return self.fps if self.fps is not None else 30

    @classmethod
    def default(cls) -> "Quality":
        """
        Создаёт Quality с настройками по умолчанию.
        
        Returns:
            Quality с MEDIUM video и audio
        """
        return cls(
            video_quality=VideoQuality.MEDIUM,
            audio_quality=AudioQuality.MEDIUM
        )

    @classmethod
    def high_quality(cls) -> "Quality":
        """
        Создаёт Quality для высокого качества.
        
        Returns:
            Quality с HIGH video и audio
        """
        return cls(
            video_quality=VideoQuality.HIGH,
            audio_quality=AudioQuality.HIGH
        )

    @classmethod
    def low_bandwidth(cls) -> "Quality":
        """
        Создаёт Quality для низкой пропускной способности.
        
        Returns:
            Quality с LOW video и audio
        """
        return cls(
            video_quality=VideoQuality.LOW,
            audio_quality=AudioQuality.LOW
        )

    def __str__(self) -> str:
        """Человекочитаемое представление."""
        return f"{self.video_quality.value}/{self.audio_quality.value} ({self.total_bitrate}kbps)"

    def is_higher_than(self, other: "Quality") -> bool:
        """
        Сравнивает качество с другим.
        
        Args:
            other: Quality для сравнения
            
        Returns:
            True если текущее качество выше
        """
        return self.total_bitrate > other.total_bitrate

    def to_ffmpeg_params(self) -> dict:
        """
        Возвращает параметры для FFmpeg.
        
        Returns:
            Dict с video_bitrate, audio_bitrate, resolution, fps
        """
        return {
            "video_bitrate": f"{self.video_bitrate}k",
            "audio_bitrate": f"{self.audio_bitrate}k",
            "resolution": f"{self.width}x{self.height}",
            "fps": self.framerate,
        }
