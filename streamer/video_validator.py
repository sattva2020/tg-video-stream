"""
Feature 003: Video Format Validation & Transcoding Pipeline

Модуль для валидации видео файлов на совместимость с Telegram.
Проверяет кодеки, форматы, ориентацию и другие параметры.

Architecture:
- VideoValidator — основной класс валидации
- Telegram-supported codecs: h264, h265 (video), aac, mp3, opus (audio)
- Orientation detection (subtask-1-3)
- Validation results with actionable error messages
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from streamer.ffprobe_utils import (
    analyze_stream_quality,
    AudioMetadata,
    VideoMetadata,
    _normalize_codec
)

log = logging.getLogger("tg_video_streamer")


class VideoFormat(str, Enum):
    """Поддерживаемые видео форматы для Telegram"""
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WEBM = "webm"


@dataclass
class ValidationResult:
    """
    Результат валидации видео файла.

    Attributes:
        valid: Флаг валидности
        is_compatible: Совместимость с Telegram
        video_codec: Название видео кодека
        audio_codec: Название аудио кодека
        format: Контейнер формата
        has_orientation: Наличие метаданных ориентации
        errors: Список ошибок валидации
        warnings: Список предупреждений
    """
    valid: bool
    is_compatible: bool
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    format: Optional[str] = None
    has_orientation: bool = False
    orientation_value: Optional[int] = None
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "is_compatible": self.is_compatible,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "format": self.format,
            "has_orientation": self.has_orientation,
            "orientation_value": self.orientation_value,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class VideoValidator:
    """
    Валидатор видео файлов для проверки совместимости с Telegram.

    Проверяет:
    - Видео кодеки (h264, h265)
    - Аудио кодеки (aac, mp3, opus)
    - Формат контейнера
    - Ориентацию видео

    Examples:
        >>> validator = VideoValidator()
        >>> result = await validator.validate_url("https://example.com/video.mp4")
        >>> if result.is_compatible:
        ...     print("Video is compatible with Telegram")
    """

    # Telegram поддерживаемые кодеки
    TELEGRAM_SUPPORTED_VIDEO_CODECS = ["h264", "h265", "hevc"]
    TELEGRAM_SUPPORTED_AUDIO_CODECS = ["aac", "mp3", "opus"]
    TELEGRAM_SUPPORTED_CODECS = TELEGRAM_SUPPORTED_VIDEO_CODECS + TELEGRAM_SUPPORTED_AUDIO_CODECS

    # Telegram поддерживаемые форматы
    TELEGRAM_SUPPORTED_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]

    def __init__(self):
        """Инициализация валидатора."""
        log.debug("VideoValidator initialized")

    @staticmethod
    def detect_orientation(ffprobe_json: Dict[str, Any]) -> Optional[int]:
        """
        Detect video orientation from FFprobe metadata.

        Извлекает значение orientation из метаданных видео.
        Значения:
        - 0: Normal (no rotation)
        - 90: Rotate 90 degrees clockwise
        - 180: Rotate 180 degrees
        - 270: Rotate 270 degrees clockwise (or 90 counter-clockwise)

        Args:
            ffprobe_json: Parsed JSON from FFprobe

        Returns:
            Orientation value (0, 90, 180, 270) or None if not present
        """
        # Check in format tags
        format_tags = ffprobe_json.get("format", {}).get("tags", {})

        # Common keys for orientation metadata
        orientation_keys = ["rotate", "orientation", "com.apple.quicktime.orientation"]

        for key in orientation_keys:
            if key in format_tags:
                try:
                    value = int(format_tags[key])
                    log.debug(f"Found orientation in format tags: {key}={value}")
                    return value
                except (ValueError, TypeError):
                    continue

        # Check in video stream tags
        streams = ffprobe_json.get("streams", [])
        for stream in streams:
            if stream.get("codec_type") == "video":
                stream_tags = stream.get("tags", {})
                for key in orientation_keys:
                    if key in stream_tags:
                        try:
                            value = int(stream_tags[key])
                            log.debug(f"Found orientation in stream tags: {key}={value}")
                            return value
                        except (ValueError, TypeError):
                            continue

                # Check side_data_list for rotate
                side_data_list = stream.get("side_data_list", [])
                for side_data in side_data_list:
                    if "rotate" in side_data:
                        try:
                            value = int(side_data["rotate"])
                            log.debug(f"Found orientation in side_data: rotate={value}")
                            return value
                        except (ValueError, TypeError):
                            continue

        log.debug("No orientation metadata found")
        return None

    async def validate_url(self, url: str, timeout: int = 10) -> ValidationResult:
        """
        Validate video URL for Telegram compatibility.

        Args:
            url: Video URL to validate
            timeout: FFprobe timeout in seconds (default: 10)

        Returns:
            ValidationResult with compatibility status and detailed information

        Examples:
            >>> validator = VideoValidator()
            >>> result = await validator.validate_url("https://example.com/video.mp4")
            >>> print(result.to_dict())
        """
        log.info(f"Validating video URL: {url}")

        errors = []
        warnings = []
        is_compatible = True

        # Analyze stream quality using existing ffprobe_utils
        stream_quality = await analyze_stream_quality(url, timeout)

        if not stream_quality:
            log.error(f"Failed to analyze stream quality for {url}")
            return ValidationResult(
                valid=False,
                is_compatible=False,
                errors=["Failed to analyze video stream. URL may be invalid or inaccessible."]
            )

        # Extract metadata
        video_meta = stream_quality.video
        audio_meta = stream_quality.audio

        if not video_meta:
            errors.append("No video stream found in URL")
            is_compatible = False
        else:
            # Validate video codec
            video_codec = _normalize_codec(video_meta.codec or "unknown")
            if video_codec not in self.TELEGRAM_SUPPORTED_VIDEO_CODECS:
                is_compatible = False
                errors.append(
                    f"Video codec '{video_codec}' is not supported by Telegram. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_VIDEO_CODECS)}. "
                    f"Action: Transcode to h264 or h265."
                )
                log.warning(f"Unsupported video codec: {video_codec}")

        if audio_meta:
            # Validate audio codec
            audio_codec = _normalize_codec(audio_meta.codec or "unknown")
            if audio_codec not in self.TELEGRAM_SUPPORTED_AUDIO_CODECS:
                is_compatible = False
                errors.append(
                    f"Audio codec '{audio_codec}' is not supported by Telegram. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_AUDIO_CODECS)}. "
                    f"Action: Transcode audio to aac, mp3, or opus."
                )
                log.warning(f"Unsupported audio codec: {audio_codec}")
        else:
            warnings.append("No audio stream found (video-only file)")

        # Detect orientation (requires raw ffprobe data)
        # For now, we'll mark it as not detected
        # This will be expanded in subtask-1-3

        valid = len(errors) == 0

        log.info(
            f"Validation complete for {url}: compatible={is_compatible}, "
            f"valid={valid}, errors={len(errors)}, warnings={len(warnings)}"
        )

        return ValidationResult(
            valid=valid,
            is_compatible=is_compatible,
            video_codec=video_meta.codec if video_meta else None,
            audio_codec=audio_meta.codec if audio_meta else None,
            format=None,  # Will be extracted from ffprobe in subtask-1-3
            has_orientation=False,  # Will be detected in subtask-1-3
            errors=errors,
            warnings=warnings
        )

    def validate_codecs(self, video_codec: Optional[str], audio_codec: Optional[str]) -> Dict[str, Any]:
        """
        Validate video and audio codecs for Telegram compatibility.

        Args:
            video_codec: Video codec name (e.g., 'h264', 'hevc')
            audio_codec: Audio codec name (e.g., 'aac', 'opus')

        Returns:
            Dict with 'valid' bool and 'errors' list

        Examples:
            >>> validator = VideoValidator()
            >>> result = validator.validate_codecs('h264', 'aac')
            >>> print(result['valid'])  # True
        """
        errors = []

        # Normalize codec names
        video_codec_norm = _normalize_codec(video_codec or "")
        audio_codec_norm = _normalize_codec(audio_codec or "")

        # Validate video codec
        if video_codec_norm and video_codec_norm != "unknown":
            if video_codec_norm not in self.TELEGRAM_SUPPORTED_VIDEO_CODECS:
                errors.append(
                    f"Video codec '{video_codec_norm}' is not supported. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_VIDEO_CODECS)}"
                )

        # Validate audio codec
        if audio_codec_norm and audio_codec_norm != "unknown":
            if audio_codec_norm not in self.TELEGRAM_SUPPORTED_AUDIO_CODECS:
                errors.append(
                    f"Audio codec '{audio_codec_norm}' is not supported. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_AUDIO_CODECS)}"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def check_transcoding_required(self, result: ValidationResult) -> Dict[str, Any]:
        """
        Check if transcoding is required based on validation result.

        Args:
            result: ValidationResult from validate_url()

        Returns:
            Dict with 'required' bool and 'reasons' list

        Examples:
            >>> validator = VideoValidator()
            >>> result = await validator.validate_url("https://example.com/video.avi")
            >>> check = validator.check_transcoding_required(result)
            >>> if check['required']:
            ...     print(f"Transcoding needed: {check['reasons']}")
        """
        if result.is_compatible:
            return {"required": False, "reasons": []}

        reasons = []

        # Check video codec
        if result.video_codec:
            video_codec = _normalize_codec(result.video_codec)
            if video_codec not in self.TELEGRAM_SUPPORTED_VIDEO_CODECS:
                reasons.append(f"Video codec '{video_codec}' -> h264/h265")

        # Check audio codec
        if result.audio_codec:
            audio_codec = _normalize_codec(result.audio_codec)
            if audio_codec not in self.TELEGRAM_SUPPORTED_AUDIO_CODECS:
                reasons.append(f"Audio codec '{audio_codec}' -> aac/mp3/opus")

        # Check orientation
        if result.has_orientation and result.orientation_value and result.orientation_value != 0:
            reasons.append(f"Video orientation correction ({result.orientation_value}°)")

        return {
            "required": len(reasons) > 0,
            "reasons": reasons
        }
