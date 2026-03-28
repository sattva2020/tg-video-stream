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

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from streamer.ffprobe_utils import (
    analyze_stream_quality,
    _normalize_codec
)

logger = logging.getLogger(__name__)


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
    # Видео: h264, h265 (hevc - альтернативное название h265)
    # Аудио: aac, mp3, opus
    TELEGRAM_SUPPORTED_VIDEO_CODECS = ["h264", "h265"]
    TELEGRAM_SUPPORTED_AUDIO_CODECS = ["aac", "mp3", "opus"]
    TELEGRAM_SUPPORTED_CODECS = TELEGRAM_SUPPORTED_VIDEO_CODECS + TELEGRAM_SUPPORTED_AUDIO_CODECS

    # Telegram поддерживаемые форматы
    TELEGRAM_SUPPORTED_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]

    # Resource limits to prevent DoS
    # Лимиты ресурсов для предотвращения DoS атак
    MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB
    MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

    def __init__(self):
        """Инициализация валидатора."""
        logger.debug("VideoValidator initialized", extra={
            "supported_video_codecs": self.TELEGRAM_SUPPORTED_VIDEO_CODECS,
            "supported_audio_codecs": self.TELEGRAM_SUPPORTED_AUDIO_CODECS,
            "supported_formats": self.TELEGRAM_SUPPORTED_FORMATS,
            "max_video_size_bytes": self.MAX_VIDEO_SIZE_BYTES,
            "max_duration_seconds": self.MAX_VIDEO_DURATION_SECONDS,
        })

    async def _get_file_size(self, url: str) -> Optional[int]:
        """
        Get file size from URL without downloading the entire file.

        Получает размер файла по URL без полной загрузки.

        Uses HTTP HEAD request to check Content-Length header.
        This is a lightweight check that prevents downloading large files.

        Args:
            url: URL to check

        Returns:
            File size in bytes, or None if not available
        """
        try:
            # Use asyncio with aiohttp for non-blocking HTTP HEAD request
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.head(url) as response:
                    if response.status == 200:
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            size = int(content_length)
                            logger.debug("Got file size from HEAD request", extra={
                                "url": url,
                                "size_bytes": size,
                                "size_mb": size / (1024 * 1024)
                            })
                            return size

            logger.debug("No Content-Length header available", extra={"url": url})
            return None

        except asyncio.TimeoutError:
            logger.warning("Timeout while checking file size", extra={"url": url})
            return None
        except Exception as e:
            logger.debug("Failed to get file size", extra={
                "url": url,
                "error": str(e)
            })
            return None

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
                    logger.debug("Found orientation in format tags", extra={
                        "key": key,
                        "orientation": value,
                        "location": "format_tags"
                    })
                    return value
                except (ValueError, TypeError):
                    logger.debug("Failed to parse orientation from format tags", extra={
                        "key": key,
                        "value": format_tags[key],
                        "error": "invalid_value_type"
                    })
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
                            logger.debug("Found orientation in stream tags", extra={
                                "key": key,
                                "orientation": value,
                                "location": "stream_tags"
                            })
                            return value
                        except (ValueError, TypeError):
                            logger.debug("Failed to parse orientation from stream tags", extra={
                                "key": key,
                                "value": stream_tags[key],
                                "error": "invalid_value_type"
                            })
                            continue

                # Check side_data_list for rotate
                side_data_list = stream.get("side_data_list", [])
                for side_data in side_data_list:
                    if "rotate" in side_data:
                        try:
                            value = int(side_data["rotate"])
                            logger.debug("Found orientation in side_data", extra={
                                "orientation": value,
                                "location": "side_data_list"
                            })
                            return value
                        except (ValueError, TypeError):
                            logger.debug("Failed to parse orientation from side_data", extra={
                                "value": side_data.get("rotate"),
                                "error": "invalid_value_type"
                            })
                            continue

        logger.debug("No orientation metadata found", extra={
            "keys_searched": orientation_keys
        })
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
        logger.info("Starting video URL validation", extra={
            "url": url,
            "timeout": timeout
        })

        errors = []
        warnings = []
        is_compatible = True

        # Check file size before validation to prevent DoS
        # Проверяем размер файла до валидации для предотвращения DoS
        file_size = await self._get_file_size(url)
        if file_size and file_size > self.MAX_VIDEO_SIZE_BYTES:
            logger.warning("Video file too large", extra={
                "url": url,
                "size": file_size,
                "max_size": self.MAX_VIDEO_SIZE_BYTES,
                "action": "reject_large_file"
            })
            return ValidationResult(
                valid=False,
                is_compatible=False,
                errors=[f"Video file too large: {file_size} bytes (max: {self.MAX_VIDEO_SIZE_BYTES} bytes = {self.MAX_VIDEO_SIZE_BYTES / (1024**3):.1f}GB)"]
            )

        # Analyze stream quality using existing ffprobe_utils
        stream_quality = await analyze_stream_quality(url, timeout)

        if not stream_quality:
            logger.error("Failed to analyze stream quality", extra={
                "url": url,
                "timeout": timeout,
                "reason": "ffprobe_analysis_failed",
                "action": "check_url_accessibility"
            })
            return ValidationResult(
                valid=False,
                is_compatible=False,
                errors=["Failed to analyze video stream. URL may be invalid or inaccessible."]
            )

        # Extract metadata
        video_meta = stream_quality.video
        audio_meta = stream_quality.audio

        # Get full ffprobe JSON for orientation detection and format info
        ffprobe_json = {}
        orientation_value = None
        has_orientation = False
        video_format = None
        
        try:
            import subprocess
            import json
            
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                ffprobe_json = json.loads(result.stdout)
                
                # Detect orientation
                orientation_value = VideoValidator.detect_orientation(ffprobe_json)
                has_orientation = orientation_value is not None and orientation_value != 0
                
                # Detect format
                format_name = ffprobe_json.get("format", {}).get("format_name", "")
                if "mp4" in format_name:
                    video_format = "mp4"
                elif "matroska" in format_name or "webm" in format_name:
                    if "webm" in format_name:
                        video_format = "webm"
                    else:
                        video_format = "mkv"
                        
                logger.debug("Detected orientation and format", extra={
                    "url": url,
                    "orientation": orientation_value,
                    "has_orientation": has_orientation,
                    "format": video_format
                })
            else:
                logger.debug("FFprobe failed to get full metadata", extra={
                    "url": url,
                    "returncode": result.returncode
                })
        except Exception as e:
            logger.debug("Error getting FFprobe metadata", extra={
                "url": url,
                "error": str(e)
            })

        if not video_meta:
            errors.append("No video stream found in URL")
            is_compatible = False
            logger.warning("No video stream found", extra={
                "url": url,
                "reason": "no_video_stream",
                "action": "verify_url_contains_video"
            })
        else:
            # Validate video codec
            video_codec = _normalize_codec(video_meta.codec or "unknown")
            # hevc is an alias for h265
            if video_codec == "hevc":
                video_codec = "h265"
            if video_codec not in self.TELEGRAM_SUPPORTED_VIDEO_CODECS:
                is_compatible = False
                error_msg = (
                    f"Video codec '{video_codec}' is not supported by Telegram. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_VIDEO_CODECS)}. "
                    f"Action: Transcode to h264 or h265."
                )
                errors.append(error_msg)
                logger.warning("Unsupported video codec detected", extra={
                    "url": url,
                    "codec": video_codec,
                    "supported_codecs": self.TELEGRAM_SUPPORTED_VIDEO_CODECS,
                    "reason": "unsupported_video_codec",
                    "action": "transcode_to_h264_or_h265"
                })
            else:
                logger.debug("Video codec validated", extra={
                    "url": url,
                    "codec": video_codec,
                    "status": "compatible"
                })

        if audio_meta:
            # Validate audio codec
            audio_codec = _normalize_codec(audio_meta.codec or "unknown")
            if audio_codec not in self.TELEGRAM_SUPPORTED_AUDIO_CODECS:
                is_compatible = False
                error_msg = (
                    f"Audio codec '{audio_codec}' is not supported by Telegram. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_AUDIO_CODECS)}. "
                    f"Action: Transcode audio to aac, mp3, or opus."
                )
                errors.append(error_msg)
                logger.warning("Unsupported audio codec detected", extra={
                    "url": url,
                    "codec": audio_codec,
                    "supported_codecs": self.TELEGRAM_SUPPORTED_AUDIO_CODECS,
                    "reason": "unsupported_audio_codec",
                    "action": "transcode_to_aac_mp3_or_opus"
                })
            else:
                logger.debug("Audio codec validated", extra={
                    "url": url,
                    "codec": audio_codec,
                    "status": "compatible"
                })
        else:
            warnings.append("No audio stream found (video-only file)")
            logger.info("No audio stream found in video", extra={
                "url": url,
                "warning": "video_only_file"
            })

        valid = len(errors) == 0

        logger.info("Validation complete", extra={
            "url": url,
            "compatible": is_compatible,
            "valid": valid,
            "video_codec": video_meta.codec if video_meta else None,
            "audio_codec": audio_meta.codec if audio_meta else None,
            "format": video_format,
            "has_orientation": has_orientation,
            "orientation_value": orientation_value,
            "errors_count": len(errors),
            "warnings_count": len(warnings),
            "errors": errors,
            "warnings": warnings
        })

        return ValidationResult(
            valid=valid,
            is_compatible=is_compatible,
            video_codec=video_meta.codec if video_meta else None,
            audio_codec=audio_meta.codec if audio_meta else None,
            format=video_format,
            has_orientation=has_orientation,
            orientation_value=orientation_value,
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
        logger.debug("Validating codecs", extra={
            "video_codec": video_codec,
            "audio_codec": audio_codec
        })

        errors = []

        # Normalize codec names
        video_codec_norm = _normalize_codec(video_codec or "")
        audio_codec_norm = _normalize_codec(audio_codec or "")

        # hevc is an alias for h265
        if video_codec_norm == "hevc":
            video_codec_norm = "h265"

        # Validate video codec
        if video_codec_norm and video_codec_norm != "unknown":
            if video_codec_norm not in self.TELEGRAM_SUPPORTED_VIDEO_CODECS:
                errors.append(
                    f"Video codec '{video_codec_norm}' is not supported. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_VIDEO_CODECS)}"
                )
                logger.warning("Codec validation failed: video codec not supported", extra={
                    "codec": video_codec_norm,
                    "supported_codecs": self.TELEGRAM_SUPPORTED_VIDEO_CODECS
                })

        # Validate audio codec
        if audio_codec_norm and audio_codec_norm != "unknown":
            if audio_codec_norm not in self.TELEGRAM_SUPPORTED_AUDIO_CODECS:
                errors.append(
                    f"Audio codec '{audio_codec_norm}' is not supported. "
                    f"Supported: {', '.join(self.TELEGRAM_SUPPORTED_AUDIO_CODECS)}"
                )
                logger.warning("Codec validation failed: audio codec not supported", extra={
                    "codec": audio_codec_norm,
                    "supported_codecs": self.TELEGRAM_SUPPORTED_AUDIO_CODECS
                })

        logger.debug("Codec validation complete", extra={
            "valid": len(errors) == 0,
            "errors_count": len(errors)
        })

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
            logger.debug("Transcoding not required: video is compatible", extra={
                "video_codec": result.video_codec,
                "audio_codec": result.audio_codec
            })
            return {"required": False, "reasons": []}

        reasons = []

        # Check video codec
        if result.video_codec:
            video_codec = _normalize_codec(result.video_codec)
            # hevc is an alias for h265
            if video_codec == "hevc":
                video_codec = "h265"
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

        logger.info("Transcoding requirement check", extra={
            "required": len(reasons) > 0,
            "reasons": reasons,
            "video_codec": result.video_codec,
            "audio_codec": result.audio_codec,
            "orientation": result.orientation_value
        })

        return {
            "required": len(reasons) > 0,
            "reasons": reasons
        }
