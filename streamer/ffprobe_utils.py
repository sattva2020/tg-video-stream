"""
Feature 022: Stream Quality Monitoring

Модуль для анализа качества аудио/видео потоков с использованием FFprobe.
Позволяет получить метрики битрейта, кодека, разрешения, fps и других параметров.

Architecture:
- analyze_stream_quality() — основная функция анализа потока
- parse_ffprobe_output() — парсинг JSON output FFprobe
- extract_audio_metadata() — извлечение аудио метаданных
- extract_video_metadata() — извлечение видео метаданных
- StreamQuality — модель данных для результатов анализа
"""

import asyncio
import subprocess
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("tg_video_streamer")


class AudioCodec(str, Enum):
    """Поддерживаемые аудио кодеки"""
    OPUS = "opus"
    MP3 = "mp3"
    AAC = "aac"
    FLAC = "flac"
    OGG = "ogg"
    WAV = "wav"
    UNKNOWN = "unknown"


class VideoCodec(str, Enum):
    """Поддерживаемые видео кодеки"""
    H264 = "h264"
    H265 = "hevc"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"
    UNKNOWN = "unknown"


class AudioQuality(str, Enum):
    """Уровни качества аудио"""
    LOW = "low"          # <= 64 kbps
    MEDIUM = "medium"    # 64-128 kbps
    HIGH = "high"        # 128-192 kbps
    LOSSLESS = "lossless"  # >= 192 kbps


class VideoQuality(str, Enum):
    """Уровни качества видео"""
    LOW = "low"        # <= 480p, < 1000 kbps
    MEDIUM = "medium"  # 480p-720p, 1000-2500 kbps
    HIGH = "high"      # 720p-1080p, 2500-5000 kbps
    ULTRA = "ultra"    # > 1080p, > 5000 kbps


@dataclass
class AudioMetadata:
    """Метаданные аудиотрека"""
    codec: Optional[str] = None
    bitrate: Optional[int] = None  # в bps
    sample_rate: Optional[int] = None  # в Hz
    channels: Optional[int] = None
    duration: Optional[float] = None  # в секундах
    quality: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codec": self.codec,
            "bitrate_kbps": self.bitrate // 1000 if self.bitrate else None,
            "sample_rate_hz": self.sample_rate,
            "channels": self.channels,
            "duration_sec": self.duration,
            "quality": self.quality,
        }


@dataclass
class VideoMetadata:
    """Метаданные видеопотока"""
    codec: Optional[str] = None
    bitrate: Optional[int] = None  # в bps
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    duration: Optional[float] = None  # в секундах
    quality: Optional[str] = None

    @property
    def resolution(self) -> Optional[str]:
        """Возвращает разрешение в формате 'WIDTHxHEIGHT'"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codec": self.codec,
            "bitrate_kbps": self.bitrate // 1000 if self.bitrate else None,
            "resolution": self.resolution,
            "fps": self.fps,
            "duration_sec": self.duration,
            "quality": self.quality,
        }


@dataclass
class StreamQuality:
    """
    Phase 5 (Feature 022): Анализ качества потока
    
    Объединённые метаданные для аудио и видео потоков
    с информацией о качестве и рекомендациях.
    """
    url: str
    audio: Optional[AudioMetadata] = None
    video: Optional[VideoMetadata] = None
    is_audio_only: bool = False
    is_video_only: bool = False
    has_both: bool = False

    @property
    def overall_quality(self) -> str:
        """Определяет общее качество потока"""
        if self.audio and self.audio.quality:
            return self.audio.quality
        if self.video and self.video.quality:
            return self.video.quality
        return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "audio": self.audio.to_dict() if self.audio else None,
            "video": self.video.to_dict() if self.video else None,
            "is_audio_only": self.is_audio_only,
            "is_video_only": self.is_video_only,
            "has_both": self.has_both,
            "overall_quality": self.overall_quality,
        }


def _normalize_codec(codec_name: str) -> str:
    """
    Нормализует название кодека из ffprobe формата.
    
    Examples:
        'aac' -> 'aac'
        'aac (aac latm)' -> 'aac'
        'opus' -> 'opus'
        'libopus' -> 'opus'
    """
    if not codec_name:
        return "unknown"
    
    codec_lower = codec_name.lower().split()[0]
    
    # Audio codecs
    if "opus" in codec_lower:
        return "opus"
    if "mp3" in codec_lower or "libmp3lame" in codec_lower:
        return "mp3"
    if "aac" in codec_lower:
        return "aac"
    if "flac" in codec_lower:
        return "flac"
    if "ogg" in codec_lower or "libvorbis" in codec_lower:
        return "ogg"
    if "wav" in codec_lower or "pcm" in codec_lower:
        return "wav"
    
    # Video codecs
    if "h264" in codec_lower or "h.264" in codec_lower:
        return "h264"
    if "h265" in codec_lower or "h.265" in codec_lower or "hevc" in codec_lower:
        return "hevc"
    if "vp8" in codec_lower:
        return "vp8"
    if "vp9" in codec_lower:
        return "vp9"
    if "av1" in codec_lower:
        return "av1"
    
    return codec_lower


def _calculate_audio_quality(bitrate: Optional[int]) -> Optional[str]:
    """Определяет уровень качества аудио на основе битрейта"""
    if not bitrate or bitrate == 0:
        return None
    
    kbps = bitrate // 1000
    if kbps <= 64:
        return AudioQuality.LOW.value
    elif kbps <= 128:
        return AudioQuality.MEDIUM.value
    elif kbps <= 192:
        return AudioQuality.HIGH.value
    else:
        return AudioQuality.LOSSLESS.value


def _calculate_video_quality(bitrate: Optional[int], height: Optional[int]) -> Optional[str]:
    """Определяет уровень качества видео на основе битрейта и разрешения"""
    if not bitrate or not height or bitrate == 0 or height == 0:
        return None
    
    kbps = bitrate // 1000
    
    if height <= 480 and kbps <= 1000:
        return VideoQuality.LOW.value
    elif height <= 720 and kbps <= 2500:
        return VideoQuality.MEDIUM.value
    elif height <= 1080 and kbps <= 5000:
        return VideoQuality.HIGH.value
    else:
        return VideoQuality.ULTRA.value


def parse_ffprobe_output(ffprobe_json: Dict[str, Any]) -> tuple[Optional[AudioMetadata], Optional[VideoMetadata]]:
    """
    Парсит JSON output от FFprobe и извлекает метаданные аудио и видео.
    
    Args:
        ffprobe_json: Parsed JSON из FFprobe
        
    Returns:
        Tuple[AudioMetadata, VideoMetadata] где каждый может быть None
    """
    audio_metadata = None
    video_metadata = None
    
    streams = ffprobe_json.get("streams", [])
    format_info = ffprobe_json.get("format", {})
    
    # Извлекаем глобальную duration если есть
    duration = None
    if "duration" in format_info:
        try:
            duration = float(format_info["duration"])
        except (ValueError, TypeError):
            pass
    
    # Обрабатываем каждый поток
    for stream in streams:
        codec_type = stream.get("codec_type", "")
        
        if codec_type == "audio":
            codec_name = _normalize_codec(stream.get("codec_name", ""))
            bitrate = None
            
            # Попытаемся получить битрейт из разных полей
            if "bit_rate" in stream:
                try:
                    bitrate = int(stream["bit_rate"])
                except (ValueError, TypeError):
                    pass
            
            sample_rate = None
            if "sample_rate" in stream:
                try:
                    sample_rate = int(stream["sample_rate"])
                except (ValueError, TypeError):
                    pass
            
            channels = stream.get("channels")
            
            audio_metadata = AudioMetadata(
                codec=codec_name,
                bitrate=bitrate,
                sample_rate=sample_rate,
                channels=channels,
                duration=duration,
                quality=_calculate_audio_quality(bitrate)
            )
        
        elif codec_type == "video":
            codec_name = _normalize_codec(stream.get("codec_name", ""))
            bitrate = None
            
            if "bit_rate" in stream:
                try:
                    bitrate = int(stream["bit_rate"])
                except (ValueError, TypeError):
                    pass
            
            width = stream.get("width")
            height = stream.get("height")
            
            fps = None
            if "r_frame_rate" in stream:
                try:
                    # r_frame_rate это строка вроде "30/1" или "24000/1001"
                    frac = stream["r_frame_rate"].split("/")
                    if len(frac) == 2:
                        fps = float(frac[0]) / float(frac[1])
                except (ValueError, TypeError, IndexError):
                    pass
            
            video_metadata = VideoMetadata(
                codec=codec_name,
                bitrate=bitrate,
                width=width,
                height=height,
                fps=fps,
                duration=duration,
                quality=_calculate_video_quality(bitrate, height)
            )
    
    return audio_metadata, video_metadata


async def analyze_stream_quality(url: str, timeout: int = 10) -> Optional[StreamQuality]:
    """
    Feature 022 (T001): Анализирует качество потока с помощью FFprobe.
    
    Использует FFprobe для извлечения метаданных о потоке и определяет
    уровень качества на основе кодека, битрейта и разрешения.
    
    Args:
        url: URL потока для анализа
        timeout: Таймаут для FFprobe в секундах (default: 10)
        
    Returns:
        StreamQuality с информацией о качестве или None если анализ неудачен
        
    Examples:
        >>> quality = await analyze_stream_quality("https://example.com/audio.mp3")
        >>> print(quality.audio.quality)  # 'medium'
        >>> print(quality.overall_quality)  # 'medium'
    """
    loop = asyncio.get_running_loop()
    
    try:
        # FFprobe команда для извлечения информации о потоке
        ffprobe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_json",
            url
        ]
        
        def _run_ffprobe():
            return subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        
        result = await loop.run_in_executor(None, _run_ffprobe)
        
        if result.returncode != 0:
            log.warning(f"FFprobe failed for {url}: {result.stderr}")
            return None
        
        ffprobe_json = json.loads(result.stdout)
        audio_meta, video_meta = parse_ffprobe_output(ffprobe_json)
        
        # Определяем тип потока
        is_audio_only = audio_meta is not None and video_meta is None
        is_video_only = video_meta is not None and audio_meta is None
        has_both = audio_meta is not None and video_meta is not None
        
        stream_quality = StreamQuality(
            url=url,
            audio=audio_meta,
            video=video_meta,
            is_audio_only=is_audio_only,
            is_video_only=is_video_only,
            has_both=has_both
        )
        
        log.info(f"Stream quality analysis for {url}: {stream_quality.overall_quality}")
        return stream_quality
        
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse FFprobe JSON for {url}: {e}")
        return None
    except subprocess.TimeoutExpired:
        log.error(f"FFprobe timeout for {url} after {timeout}s")
        return None
    except FileNotFoundError:
        log.error("FFprobe not found in PATH. Install ffmpeg/ffprobe.")
        return None
    except Exception as e:
        log.exception(f"Unexpected error analyzing stream {url}: {e}")
        return None


async def batch_analyze_streams(urls: list[str], timeout: int = 10) -> Dict[str, Optional[StreamQuality]]:
    """
    Анализирует качество множественных потоков параллельно.
    
    Args:
        urls: Список URL потоков для анализа
        timeout: Таймаут для каждого FFprobe в секундах
        
    Returns:
        Словарь {url: StreamQuality} для успешно проанализированных потоков
    """
    tasks = [analyze_stream_quality(url, timeout) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    output = {}
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            log.error(f"Error analyzing {url}: {result}")
            output[url] = None
        else:
            output[url] = result
    
    return output


# Cache для результатов анализа (TTL: 5 минут)
_quality_cache: Dict[str, tuple[StreamQuality, float]] = {}
_CACHE_TTL = 5 * 60  # 5 minutes


async def analyze_stream_quality_cached(url: str, timeout: int = 10, force: bool = False) -> Optional[StreamQuality]:
    """
    Анализирует качество потока с кешированием результатов.
    
    Args:
        url: URL потока
        timeout: Таймаут FFprobe
        force: Если True, пропустить кеш и переанализировать
        
    Returns:
        StreamQuality или None
    """
    import time
    
    current_time = time.time()
    
    # Проверяем кеш
    if not force and url in _quality_cache:
        cached_result, cached_time = _quality_cache[url]
        if current_time - cached_time < _CACHE_TTL:
            log.debug(f"Using cached quality for {url}")
            return cached_result
    
    # Анализируем заново
    result = await analyze_stream_quality(url, timeout)
    
    # Кешируем результат
    if result:
        _quality_cache[url] = (result, current_time)
    
    return result
