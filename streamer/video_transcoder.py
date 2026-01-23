"""
Feature 003: Video Format Validation & Transcoding Pipeline

Модуль для транскодирования видео файлов в форматы, совместимые с Telegram.
Поддерживает конвертацию кодеков, коррекцию ориентации и профили качества.

Architecture:
- VideoTranscoder — основной класс для транскодирования
- QualityProfile — профили качества (low, medium, high, ultra)
- FFmpeg command builder для video transcoding
- Orientation correction с transpose filter
"""

import asyncio
import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, AsyncIterator, Dict, Any

logger = logging.getLogger(__name__)


class QualityProfile(str, Enum):
    """Профили качества для транскодирования видео."""

    LOW = "low"        # 480p, 500-1000 kbps
    MEDIUM = "medium"  # 720p, 1500-2500 kbps
    HIGH = "high"      # 1080p, 3000-5000 kbps
    ULTRA = "ultra"    # 1440p+, 6000+ kbps

    def get_video_settings(self) -> tuple[int, int]:
        """
        Возвращает настройки видео для профиля.

        Returns:
            Tuple[height, bitrate_kbps]
        """
        settings = {
            QualityProfile.LOW: (480, 800),
            QualityProfile.MEDIUM: (720, 2000),
            QualityProfile.HIGH: (1080, 4000),
            QualityProfile.ULTRA: (1440, 8000),
        }
        return settings.get(self, (720, 2000))

    def get_audio_settings(self) -> int:
        """
        Возвращает битрейт аудио для профиля.

        Returns:
            Audio bitrate in kbps
        """
        audio_settings = {
            QualityProfile.LOW: 64,
            QualityProfile.MEDIUM: 128,
            QualityProfile.HIGH: 128,
            QualityProfile.ULTRA: 192,
        }
        return audio_settings.get(self, 128)


@dataclass
class VideoTranscodeRequest:
    """
    Запрос на транскодирование видео.

    Attributes:
        source_url: URL исходного видео файла
        video_codec: Целевой видео кодек (h264, h265)
        audio_codec: Целевой аудио кодек (aac, mp3, opus)
        format: Выходной формат контейнера (mp4, mkv, webm)
        quality: Профиль качества
        orientation: Ориентация для коррекции (0, 90, 180, 270)
        bitrate: Переопределить битрейт видео (kbps)
        audio_bitrate: Переопределить битрейт аудио (kbps)
        width: Переопределить ширину
        height: Переопределить высоту
        fps: Целевой FPS
    """

    source_url: str
    video_codec: str = "h264"
    audio_codec: str = "aac"
    format: str = "mp4"
    quality: QualityProfile = QualityProfile.MEDIUM
    orientation: Optional[int] = None
    bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в dict для логирования."""
        return {
            "source_url": self.source_url,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "format": self.format,
            "quality": self.quality.value,
            "orientation": self.orientation,
            "bitrate": self.bitrate,
            "audio_bitrate": self.audio_bitrate,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
        }


class VideoTranscoder:
    """
    Транскодер видео файлов для совместимости с Telegram.

    Features:
    - Конвертация видео кодеков (h264, h265)
    - Конвертация аудио кодеков (aac, mp3, opus)
    - Коррекция ориентации (transpose filter)
    - Профили качества (low, medium, high, ultra)
    - Streaming output в stdout

    Examples:
        >>> transcoder = VideoTranscoder()
        >>> request = VideoTranscodeRequest(
        ...     source_url="input.avi",
        ...     video_codec="h264",
        ...     audio_codec="aac",
        ...     quality=QualityProfile.MEDIUM
        ... )
        >>> async for chunk in transcoder.transcode(request):
        ...     process_chunk(chunk)
    """

    # Telegram поддерживаемые кодеки
    SUPPORTED_VIDEO_CODECS = ["h264", "h265"]
    SUPPORTED_AUDIO_CODECS = ["aac", "mp3", "opus"]
    SUPPORTED_FORMATS = ["mp4", "mkv", "webm"]

    def __init__(self):
        """Инициализация транскодера."""
        logger.debug("VideoTranscoder initialized", extra={
            "supported_video_codecs": self.SUPPORTED_VIDEO_CODECS,
            "supported_audio_codecs": self.SUPPORTED_AUDIO_CODECS,
            "supported_formats": self.SUPPORTED_FORMATS
        })

    @staticmethod
    def build_ffmpeg_command(
        source_url: str,
        video_codec: str = "h264",
        audio_codec: str = "aac",
        output_format: str = "mp4",
        quality: QualityProfile = QualityProfile.MEDIUM,
        orientation: Optional[int] = None,
        bitrate: Optional[int] = None,
        audio_bitrate: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
    ) -> list[str]:
        """
        Строит команду FFmpeg для транскодирования видео.

        Args:
            source_url: URL исходного видео
            video_codec: Целевой видео кодек
            audio_codec: Целевой аудио кодек
            output_format: Выходной формат контейнера
            quality: Профиль качества
            orientation: Ориентация для коррекции (0, 90, 180, 270)
            bitrate: Переопределить битрейт видео (kbps)
            audio_bitrate: Переопределить битрейт аудио (kbps)
            width: Переопределить ширину
            height: Переопределить высоту
            fps: Целевой FPS

        Returns:
            Список аргументов для subprocess

        Examples:
            >>> cmd = VideoTranscoder.build_ffmpeg_command(
            ...     "input.mp4", "h264", "aac"
            ... )
            >>> print(cmd[0])  # 'ffmpeg'
        """
        logger.debug("Building FFmpeg command", extra={
            "source_url": source_url,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "output_format": output_format,
            "quality": quality.value,
            "orientation": orientation,
            "bitrate": bitrate,
            "audio_bitrate": audio_bitrate,
            "width": width,
            "height": height,
            "fps": fps
        })

        # Base command
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-y",
            "-i", source_url,
        ]

        # Video codec
        cmd.extend(["-c:v", video_codec])

        # Quality settings
        if not (width or height):
            target_height, target_bitrate = quality.get_video_settings()
        else:
            target_height = height or quality.get_video_settings()[0]
            target_bitrate = bitrate or quality.get_video_settings()[1]

        logger.debug("Transcoding quality settings determined", extra={
            "target_height": target_height,
            "target_bitrate": target_bitrate,
            "quality_profile": quality.value
        })

        # Bitrate
        cmd.extend(["-b:v", f"{target_bitrate}k"])

        # Resolution (scaling)
        if width or height:
            scale_filter = f"scale={width or -2}:{height or -2}"
            cmd.extend(["-vf", scale_filter])

        # FPS
        if fps:
            cmd.extend(["-r", str(fps)])

        # Audio codec
        cmd.extend(["-c:a", audio_codec])

        # Audio bitrate
        target_audio_bitrate = audio_bitrate or quality.get_audio_settings()
        cmd.extend(["-b:a", f"{target_audio_bitrate}k"])

        # Orientation correction (transpose filter)
        if orientation and orientation != 0:
            transpose_value = VideoTranscoder._get_transpose_value(orientation)
            if transpose_value is not None:
                # Add to existing filters or create new filter chain
                if width or height:
                    # Existing scale filter, append transpose
                    existing_filter = cmd[cmd.index("-vf") + 1]
                    cmd[cmd.index("-vf") + 1] = f"{existing_filter},transpose={transpose_value}"
                else:
                    cmd.extend(["-vf", f"transpose={transpose_value}"])

        # Pixel format (для совместимости)
        cmd.extend(["-pix_fmt", "yuv420p"])

        # Output format
        cmd.extend(["-f", output_format])

        # Fast start (Move metadata to beginning of file for streaming)
        if output_format == "mp4":
            cmd.append("-movflags")
            cmd.append("faststart")

        # Output to stdout
        cmd.append("pipe:1")

        return cmd

    @staticmethod
    def _get_transpose_value(orientation: int) -> Optional[int]:
        """
        Конвертирует значение ориентации в значение transpose фильтра FFmpeg.

        Args:
            orientation: Значение ориентации (0, 90, 180, 270)

        Returns:
            Значение для transpose={clockwise, cclockwise, ...}
            None если коррекция не требуется

        Transpose values:
            0 = 90° counter-clockwise & vertical flip (default)
            1 = 90° clockwise
            2 = 90° counter-clockwise
            3 = 90° clockwise & vertical flip
        """
        # Orientation это поворот против часовой стрелки
        # Transpose работает по часовой стрелке
        transpose_map = {
            90: 2,   # 90° CCW = transpose=2
            180: None,  # 180° requires transpose=1,transpose=1
            270: 1,  # 270° CCW = 90° CW = transpose=1
        }

        if orientation == 180:
            # Special case: 180° requires two transposes
            # This will be handled in apply_orientation_correction
            return "1,transpose=1"

        return transpose_map.get(orientation)

    @staticmethod
    def apply_orientation_correction(
        source_url: str,
        orientation: int,
        output_url: str,
    ) -> list[str]:
        """
        Применяет коррекцию ориентации к видео.

        Args:
            source_url: URL исходного видео
            orientation: Значение ориентации (90, 180, 270)
            output_url: URL для сохранения результата

        Returns:
            Список аргументов для subprocess

        Examples:
            >>> cmd = VideoTranscoder.apply_orientation_correction(
            ...     "input.mp4", 90, "output.mp4"
            ... )
            >>> print("transpose" in " ".join(cmd))  # True
        """
        logger.debug("Building orientation correction command", extra={
            "source_url": source_url,
            "orientation": orientation,
            "output_url": output_url
        })

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-y",
            "-i", source_url,
        ]

        # Build transpose filter based on orientation
        if orientation == 90:
            cmd.extend(["-vf", "transpose=2"])  # 90° CCW
            logger.debug("Orientation correction: 90° counter-clockwise")
        elif orientation == 180:
            cmd.extend(["-vf", "transpose=1,transpose=1"])  # 180°
            logger.debug("Orientation correction: 180° rotation")
        elif orientation == 270:
            cmd.extend(["-vf", "transpose=1"])  # 90° CW (270° CCW)
            logger.debug("Orientation correction: 270° counter-clockwise (90° clockwise)")
        else:
            # No correction needed
            logger.debug("No orientation correction needed", extra={
                "orientation": orientation
            })
            cmd.extend(["-c", "copy"])  # Stream copy

        cmd.extend(["-c:a", "copy"])  # Copy audio without re-encoding
        cmd.append(output_url)

        return cmd

    async def transcode(
        self,
        request: VideoTranscodeRequest,
    ) -> AsyncIterator[bytes]:
        """
        Транскодирует видео и стримит результат.

        Args:
            request: VideoTranscodeRequest с параметрами транскодирования

        Yields:
            Chunks транскодированного видео

        Examples:
            >>> transcoder = VideoTranscoder()
            >>> request = VideoTranscodeRequest("input.avi")
            >>> async for chunk in transcoder.transcode(request):
            ...     # Process chunks
            ...     pass
        """
        logger.info("Starting video transcoding", extra={
            "source_url": request.source_url,
            "video_codec": request.video_codec,
            "audio_codec": request.audio_codec,
            "format": request.format,
            "quality": request.quality.value,
            "orientation": request.orientation,
            "bitrate": request.bitrate,
            "audio_bitrate": request.audio_bitrate,
            "width": request.width,
            "height": request.height,
            "fps": request.fps
        })

        cmd = self.build_ffmpeg_command(
            source_url=request.source_url,
            video_codec=request.video_codec,
            audio_codec=request.audio_codec,
            output_format=request.format,
            quality=request.quality,
            orientation=request.orientation,
            bitrate=request.bitrate,
            audio_bitrate=request.audio_bitrate,
            width=request.width,
            height=request.height,
            fps=request.fps,
        )

        logger.debug("FFmpeg command built", extra={
            "command": " ".join(cmd),
            "source_url": request.source_url
        })

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        chunk_count = 0
        total_bytes = 0

        try:
            logger.debug("Starting to read transcoded video chunks", extra={
                "source_url": request.source_url
            })

            while True:
                chunk = await process.stdout.read(8192)  # 8KB chunks for video
                if not chunk:
                    logger.debug("End of stream reached", extra={
                        "source_url": request.source_url,
                        "chunks_read": chunk_count,
                        "total_bytes": total_bytes
                    })
                    break
                chunk_count += 1
                total_bytes += len(chunk)
                yield chunk

                # Log progress every 100 chunks (~800KB)
                if chunk_count % 100 == 0:
                    logger.debug("Transcoding progress", extra={
                        "source_url": request.source_url,
                        "chunks": chunk_count,
                        "total_bytes": total_bytes
                    })

            returncode = await process.wait()

            if returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")
                logger.error("FFmpeg transcoding failed", extra={
                    "source_url": request.source_url,
                    "returncode": returncode,
                    "error": error_msg,
                    "video_codec": request.video_codec,
                    "audio_codec": request.audio_codec,
                    "action": "check_ffmpeg_logs_and_source_video"
                })
                raise RuntimeError(f"Video transcoding failed with code {returncode}: {error_msg}")

            logger.info("Video transcoding completed successfully", extra={
                "source_url": request.source_url,
                "output_format": request.format,
                "chunks": chunk_count,
                "total_bytes": total_bytes
            })

        except Exception as e:
            logger.exception("Error during video transcoding", extra={
                "source_url": request.source_url,
                "error": str(e),
                "error_type": type(e).__name__,
                "chunks_processed": chunk_count,
                "total_bytes": total_bytes
            })
            if process.returncode is None:
                logger.debug("Terminating transcoding process", extra={
                    "source_url": request.source_url
                })
                process.terminate()
                await process.wait()
            raise

    async def transcode_to_file(
        self,
        request: VideoTranscodeRequest,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Транскодирует видео и сохраняет в файл.

        Args:
            request: VideoTranscodeRequest с параметрами
            output_path: Путь для сохранения выходного файла

        Returns:
            Dict с информацией о результате

        Examples:
            >>> transcoder = VideoTranscoder()
            >>> request = VideoTranscodeRequest("input.avi")
            >>> result = await transcoder.transcode_to_file(request, "output.mp4")
            >>> print(result['success'])
        """
        logger.info("Starting video transcoding to file", extra={
            "source_url": request.source_url,
            "output_path": output_path,
            "video_codec": request.video_codec,
            "audio_codec": request.audio_codec,
            "format": request.format,
            "quality": request.quality.value
        })

        cmd = self.build_ffmpeg_command(
            source_url=request.source_url,
            video_codec=request.video_codec,
            audio_codec=request.audio_codec,
            output_format=request.format,
            quality=request.quality,
            orientation=request.orientation,
            bitrate=request.bitrate,
            audio_bitrate=request.audio_bitrate,
            width=request.width,
            height=request.height,
            fps=request.fps,
        )

        # Replace pipe:1 with output path
        cmd[-1] = output_path

        logger.debug("FFmpeg command for file transcoding", extra={
            "command": " ".join(cmd),
            "source_url": request.source_url,
            "output_path": output_path
        })

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode(errors="replace")
            logger.error("FFmpeg transcoding to file failed", extra={
                "source_url": request.source_url,
                "output_path": output_path,
                "returncode": process.returncode,
                "error": error_msg,
                "action": "check_ffmpeg_logs_and_source_video"
            })
            return {
                "success": False,
                "error": error_msg,
                "returncode": process.returncode,
            }

        logger.info("Video transcoding to file completed successfully", extra={
            "source_url": request.source_url,
            "output_path": output_path,
            "returncode": process.returncode,
            "video_codec": request.video_codec,
            "audio_codec": request.audio_codec
        })

        return {
            "success": True,
            "output_path": output_path,
            "returncode": process.returncode,
        }


# Singleton instance для использования в приложении
_transcoder: Optional[VideoTranscoder] = None


def get_video_transcoder() -> VideoTranscoder:
    """Возвращает singleton VideoTranscoder."""
    global _transcoder
    if _transcoder is None:
        _transcoder = VideoTranscoder()
    return _transcoder
