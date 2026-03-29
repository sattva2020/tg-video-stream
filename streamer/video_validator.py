"""
Feature 003: Video Format Validation & Transcoding Pipeline

Модуль для валидации видео файлов на совместимость с Telegram.
Проверяет кодеки, форматы, ориентацию и другие параметры.

Architecture:
- VideoValidator — основной класс валидации
- Telegram-supported codecs: h264, h265 (video), aac, mp3, opus (audio)
- Orientation detection (subtask-1-3)
- Validation results with actionable error messages
- HLS/DASH stream support (subtask-4-1)
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


class StreamSourceType(str, Enum):
    """Тип источника видео потока"""
    DIRECT_URL = "direct_url"  # Прямая ссылка на видеофайл (mp4, webm, etc.)
    HLS = "hls"  # HTTP Live Streaming (.m3u8)
    DASH = "dash"  # Dynamic Adaptive Streaming over HTTP (.mpd)
    UNKNOWN = "unknown"


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
    def detect_stream_source_type(url: str) -> StreamSourceType:
        """
        Detect the type of video stream source from URL.

        Определяет тип источника видео потока по URL.

        Args:
            url: Video URL to analyze

        Returns:
            StreamSourceType enum value

        Examples:
            >>> VideoValidator.detect_stream_source_type("https://example.com/video.mp4")
            <StreamSourceType.DIRECT_URL: 'direct_url'>
            >>> VideoValidator.detect_stream_source_type("https://example.com/stream.m3u8")
            <StreamSourceType.HLS: 'hls'>
        """
        if not url:
            return StreamSourceType.UNKNOWN

        url_lower = url.lower().strip()

        # Check for HLS streams (.m3u8 playlists)
        if ".m3u8" in url_lower or url_lower.endswith("m3u8"):
            logger.debug("Detected HLS stream source", extra={"url": url})
            return StreamSourceType.HLS

        # Check for DASH streams (.mpd manifests)
        if ".mpd" in url_lower or url_lower.endswith("mpd"):
            logger.debug("Detected DASH stream source", extra={"url": url})
            return StreamSourceType.DASH

        # Check for direct video file extensions
        direct_extensions = [
            ".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv",
            ".wmv", ".m4v", ".mpg", ".mpeg", ".3gp"
        ]
        for ext in direct_extensions:
            if url_lower.endswith(ext):
                logger.debug("Detected direct video URL", extra={"url": url, "extension": ext})
                return StreamSourceType.DIRECT_URL

        # Default to unknown if we can't determine
        logger.debug("Could not determine stream source type", extra={"url": url})
        return StreamSourceType.UNKNOWN

    async def _validate_hls_stream(self, url: str, timeout: int = 15) -> ValidationResult:
        """
        Validate HLS/DASH stream for compatibility.

        Валидирует HLS/DASH поток на совместимость.

        Uses the HLS service to parse manifest/playlist and extract stream metadata.

        Args:
            url: HLS/DASH stream URL
            timeout: Request timeout in seconds

        Returns:
            ValidationResult with stream metadata and compatibility status
        """
        try:
            # Import HLS service
            from backend.src.services.hls_service import validate_stream

            logger.info("Validating HLS/DASH stream", extra={"url": url, "timeout": timeout})

            # Validate stream using HLS service
            stream_result = await validate_stream(url, timeout=timeout)

            if not stream_result.get("success"):
                logger.error("HLS/DASH stream validation failed", extra={
                    "url": url,
                    "error": stream_result.get("error")
                })
                return ValidationResult(
                    valid=False,
                    is_compatible=False,
                    errors=[f"Stream validation failed: {stream_result.get('error', 'Unknown error')}"]
                )

            stream_type = stream_result.get("stream_type", "unknown")
            is_live = stream_result.get("is_live", False)
            variants = stream_result.get("variants", [])
            total_variants = stream_result.get("total_variants", 0)

            logger.info("HLS/DASH stream validated successfully", extra={
                "url": url,
                "stream_type": stream_type,
                "is_live": is_live,
                "total_variants": total_variants
            })

            # Check if there are compatible stream variants
            # For now, we'll mark HLS streams as potentially compatible
            # The transcoding service will handle codec conversion if needed
            warnings = []

            if total_variants == 0:
                warnings.append("No stream variants found - may be a media playlist, not master playlist")
            else:
                # Log available variants
                logger.debug("Stream variants available", extra={
                    "url": url,
                    "variants": variants
                })

            if is_live:
                warnings.append("Live stream detected - transcoding may not be possible")

            return ValidationResult(
                valid=True,
                is_compatible=True,  # Mark as compatible - transcoding will handle conversion
                video_codec=None,  # Codec info is in variants
                audio_codec=None,
                format=stream_type,
                has_orientation=False,
                errors=[],
                warnings=warnings
            )

        except ImportError:
            logger.error("HLS service not available", extra={"url": url})
            return ValidationResult(
                valid=False,
                is_compatible=False,
                errors=["HLS service not available - cannot validate stream"]
            )
        except Exception as e:
            logger.exception("Error validating HLS/DASH stream", extra={"url": url})
            return ValidationResult(
                valid=False,
                is_compatible=False,
                errors=[f"Stream validation error: {str(e)}"]
            )

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

        Supports:
        - Direct video URLs (MP4, WebM, MKV, etc.)
        - HLS streams (.m3u8 playlists)
        - DASH streams (.mpd manifests)

        Args:
            url: Video URL to validate
            timeout: FFprobe timeout in seconds (default: 10)

        Returns:
            ValidationResult with compatibility status and detailed information

        Examples:
            >>> validator = VideoValidator()
            >>> result = await validator.validate_url("https://example.com/video.mp4")
            >>> print(result.to_dict())
            >>> result = await validator.validate_url("https://example.com/stream.m3u8")
            >>> print(result.is_compatible)
        """
        logger.info("Starting video URL validation", extra={
            "url": url,
            "timeout": timeout
        })

        # Detect stream source type
        source_type = self.detect_stream_source_type(url)
        logger.debug("Detected stream source type", extra={"url": url, "source_type": source_type.value})

        # Route to appropriate validation method based on source type
        if source_type == StreamSourceType.HLS or source_type == StreamSourceType.DASH:
            # Validate HLS/DASH stream
            return await self._validate_hls_stream(url, timeout)

        elif source_type == StreamSourceType.DIRECT_URL:
            # Validate direct video URL using ffprobe
            return await self._validate_direct_url(url, timeout)

        else:
            # Unknown source type - try direct URL validation as fallback
            logger.warning("Unknown stream source type, attempting direct URL validation", extra={"url": url})
            return await self._validate_direct_url(url, timeout)

    async def _validate_direct_url(self, url: str, timeout: int = 10) -> ValidationResult:
        """
        Validate direct video URL for Telegram compatibility.

        Валидирует прямую ссылку на видеофайл на совместимость с Telegram.

        Uses ffprobe to analyze stream quality and codec compatibility.

        Args:
            url: Direct video URL to validate
            timeout: FFprobe timeout in seconds

        Returns:
            ValidationResult with compatibility status and detailed information
        """
        logger.info("Validating direct video URL", extra={
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

        # Detect orientation (requires raw ffprobe data)
        # For now, we'll mark it as not detected
        # This will be expanded in subtask-1-3

        valid = len(errors) == 0

        logger.info("Direct URL validation complete", extra={
            "url": url,
            "compatible": is_compatible,
            "valid": valid,
            "video_codec": video_meta.codec if video_meta else None,
            "audio_codec": audio_meta.codec if audio_meta else None,
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
