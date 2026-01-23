"""
Feature 010: Encoding Profile Service

Сервис для валидации кодеков и управления профилями кодирования.
Предоставляет API для проверки совместимости кодеков и управления пресетами качества.
"""

import asyncio
import logging
import subprocess
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass

log = logging.getLogger(__name__)


class VideoCodec(str, Enum):
    """Поддерживаемые видео кодеки."""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"


class AudioCodec(str, Enum):
    """Поддерживаемые аудио кодеки."""
    AAC = "aac"
    OPUS = "opus"
    MP3 = "mp3"


class QualityPreset(str, Enum):
    """Пресеты качества для кодирования."""
    LOW = "low"        # 480p, 500-1000 kbps
    MEDIUM = "medium"  # 720p, 1500-2500 kbps
    HIGH = "high"      # 1080p, 3000-5000 kbps
    ULTRA = "ultra"    # 1440p+, 6000+ kbps


@dataclass
class CodecValidationResult:
    """
    Результат валидации кодека.

    Attributes:
        is_valid: Является ли комбинация кодеков валидной
        video_codec_supported: Поддерживается ли видео кодек FFmpeg
        audio_codec_supported: Поддерживается ли аудио кодек FFmpeg
        combination_valid: Валидна ли комбинация видео+аудио кодеков
        warnings: Список предупреждений
        errors: Список ошибок
        recommended_bitrates: Рекомендуемые битрейты для выбранного качества
    """
    is_valid: bool
    video_codec_supported: bool
    audio_codec_supported: bool
    combination_valid: bool
    warnings: List[str]
    errors: List[str]
    recommended_bitrates: Optional[Dict[str, int]] = None


@dataclass
class EncodingProfile:
    """
    Профиль кодирования.

    Attributes:
        video_codec: Видео кодек
        audio_codec: Аудио кодек
        video_bitrate: Видео битрейт в kbps
        audio_bitrate: Аудио битрейт в kbps
        resolution: Разрешение (например, "1920x1080")
        quality_preset: Пресет качества
        custom_ffmpeg_args: Дополнительные аргументы для FFmpeg
    """
    video_codec: str
    audio_codec: str
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    resolution: Optional[str] = None
    quality_preset: Optional[str] = None
    custom_ffmpeg_args: Optional[str] = None

    def to_dict(self) -> Dict:
        """Конвертирует профиль в словарь."""
        return {
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "video_bitrate": self.video_bitrate,
            "audio_bitrate": self.audio_bitrate,
            "resolution": self.resolution,
            "quality_preset": self.quality_preset,
            "custom_ffmpeg_args": self.custom_ffmpeg_args,
        }


class EncodingProfileService:
    """
    Feature 010: Сервис для управления профилями кодирования

    Предоставляет API для:
    - Валидации комбинаций кодеков
    - Проверки поддержки кодеков FFmpeg
    - Получения рекомендованных настроек для пресетов качества
    - Управления профилями кодирования
    """

    _instance = None
    _ffmpeg_codec_cache: Optional[Dict[str, bool]] = None
    _cache_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # Валидные комбинации видео+аудио кодеков
    VALID_CODEC_COMBINATIONS = {
        VideoCodec.H264: [AudioCodec.AAC, AudioCodec.OPUS, AudioCodec.MP3],
        VideoCodec.H265: [AudioCodec.AAC, AudioCodec.OPUS],
        VideoCodec.VP9: [AudioCodec.OPUS, AudioCodec.AAC],
    }

    # Рекомендуемые настройки для пресетов качества
    QUALITY_PRESETS = {
        QualityPreset.LOW: {
            "resolution": "854x480",  # 480p
            "video_bitrate": 800,
            "audio_bitrate": 64,
        },
        QualityPreset.MEDIUM: {
            "resolution": "1280x720",  # 720p
            "video_bitrate": 2000,
            "audio_bitrate": 128,
        },
        QualityPreset.HIGH: {
            "resolution": "1920x1080",  # 1080p
            "video_bitrate": 4000,
            "audio_bitrate": 128,
        },
        QualityPreset.ULTRA: {
            "resolution": "2560x1440",  # 1440p
            "video_bitrate": 8000,
            "audio_bitrate": 192,
        },
    }

    # Ограничения на битрейты (kbps)
    BITRATE_LIMITS = {
        VideoCodec.H264: {"min": 500, "max": 10000},
        VideoCodec.H265: {"min": 500, "max": 15000},
        VideoCodec.VP9: {"min": 500, "max": 15000},
    }

    # Ограничения на аудио битрейты (kbps)
    AUDIO_BITRATE_LIMITS = {
        AudioCodec.AAC: {"min": 32, "max": 256},
        AudioCodec.OPUS: {"min": 16, "max": 256},
        AudioCodec.MP3: {"min": 64, "max": 320},
    }

    def __init__(self):
        """Инициализация сервиса."""
        if not self._cache_initialized:
            self._initialize_codec_cache()

    def _initialize_codec_cache(self):
        """Инициализирует кеш поддержки кодеков FFmpeg."""
        if self._ffmpeg_codec_cache is not None:
            return

        self._ffmpeg_codec_cache = {}
        EncodingProfileService._cache_initialized = True

        # Проверяем поддержку кодеков асинхронно при первом запросе
        log.debug("FFmpeg codec cache initialized (lazy loading enabled)")

    async def _check_ffmpeg_codec_support(self, codec: str, codec_type: str) -> bool:
        """
        Проверяет поддержку кодека в FFmpeg.

        Args:
            codec: Название кодека (h264, h265, vp9, aac, opus, mp3)
            codec_type: Тип кодека ('video' или 'audio')

        Returns:
            True если кодек поддерживается, иначе False
        """
        if self._ffmpeg_codec_cache is None:
            self._ffmpeg_codec_cache = {}

        cache_key = f"{codec_type}_{codec}"
        if cache_key in self._ffmpeg_codec_cache:
            return self._ffmpeg_codec_cache[cache_key]

        try:
            # Используем ffmpeg -codecs для проверки поддержки
            cmd = ["ffmpeg", "-codecs"]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                log.warning(f"Failed to check FFmpeg codecs: {stderr.decode()}")
                return False

            output = stdout.decode()
            # Ищем кодек в выводе
            # Формат: D.V.L. h264   ... (decoding/encoding)
            codec_pattern = f"{codec}\\s"

            # Проверяем кодек для кодирования
            for line in output.split('\n'):
                if codec in line and codec_type in line.lower():
                    # Проверяем флаги: E означает encoding support
                    flags = line.split()[0] if line.split() else ""
                    is_supported = 'E' in flags
                    self._ffmpeg_codec_cache[cache_key] = is_supported
                    return is_supported

            # Если не нашли, возвращаем False
            self._ffmpeg_codec_cache[cache_key] = False
            return False

        except Exception as e:
            log.error(f"Error checking FFmpeg codec support for {codec}: {e}")
            # При ошибке считаем что кодек не поддерживается
            self._ffmpeg_codec_cache[cache_key] = False
            return False

    def _validate_bitrate(
        self,
        bitrate: Optional[int],
        codec: str,
        codec_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Валидирует битрейт для кодека.

        Args:
            bitrate: Битрейт в kbps
            codec: Название кодека
            codec_type: Тип кодека ('video' или 'audio')

        Returns:
            Tuple[is_valid, error_message]
        """
        if bitrate is None:
            return True, None  # Битрейт может быть не указан

        if codec_type == "video":
            try:
                video_codec = VideoCodec(codec)
                limits = self.BITRATE_LIMITS.get(video_codec, {})
                min_bitrate = limits.get("min", 500)
                max_bitrate = limits.get("max", 10000)
            except ValueError:
                return False, f"Unsupported video codec: {codec}"
        else:
            try:
                audio_codec = AudioCodec(codec)
                limits = self.AUDIO_BITRATE_LIMITS.get(audio_codec, {})
                min_bitrate = limits.get("min", 64)
                max_bitrate = limits.get("max", 256)
            except ValueError:
                return False, f"Unsupported audio codec: {codec}"

        if bitrate < min_bitrate:
            return False, f"Bitrate {bitrate} kbps is too low for {codec}. Minimum: {min_bitrate} kbps"
        if bitrate > max_bitrate:
            return False, f"Bitrate {bitrate} kbps is too high for {codec}. Maximum: {max_bitrate} kbps"

        return True, None

    async def validate_codec_combination(
        self,
        video_codec: str,
        audio_codec: str
    ) -> CodecValidationResult:
        """
        Валидирует комбинацию видео и аудио кодеков.

        Args:
            video_codec: Видео кодек (h264, h265, vp9)
            audio_codec: Аудио кодек (aac, opus, mp3)

        Returns:
            CodecValidationResult с деталями валидации
        """
        errors = []
        warnings = []
        video_supported = False
        audio_supported = False
        combination_valid = False

        # Проверяем валидность перечислений
        try:
            video_codec_enum = VideoCodec(video_codec)
        except ValueError:
            errors.append(f"Unsupported video codec: {video_codec}. Supported: { [c.value for c in VideoCodec]}")
            return CodecValidationResult(
                is_valid=False,
                video_codec_supported=False,
                audio_codec_supported=False,
                combination_valid=False,
                warnings=warnings,
                errors=errors
            )

        try:
            audio_codec_enum = AudioCodec(audio_codec)
        except ValueError:
            errors.append(f"Unsupported audio codec: {audio_codec}. Supported: { [c.value for c in AudioCodec]}")
            return CodecValidationResult(
                is_valid=False,
                video_codec_supported=False,
                audio_codec_supported=False,
                combination_valid=False,
                warnings=warnings,
                errors=errors
            )

        # Проверяем поддержку кодеков FFmpeg
        video_supported = await self._check_ffmpeg_codec_support(video_codec, "video")
        audio_supported = await self._check_ffmpeg_codec_support(audio_codec, "audio")

        if not video_supported:
            errors.append(f"Video codec {video_codec} is not supported by FFmpeg")

        if not audio_supported:
            errors.append(f"Audio codec {audio_codec} is not supported by FFmpeg")

        # Проверяем валидность комбинации
        valid_audio_codecs = self.VALID_CODEC_COMBINATIONS.get(video_codec_enum, [])
        combination_valid = audio_codec_enum in valid_audio_codecs

        if not combination_valid:
            errors.append(
                f"Codec combination {video_codec}+{audio_codec} is not recommended. "
                f"Valid audio codecs for {video_codec}: { [c.value for c in valid_audio_codecs]}"
            )

        # Предупреждения для определенных комбинаций
        if video_codec_enum == VideoCodec.VP9 and audio_codec_enum == AudioCodec.AAC:
            warnings.append(
                "VP9 + AAC combination may not be supported by all players. "
                "Consider using VP9 + OPUS for better compatibility."
            )

        # Рекомендуемые битрейты
        recommended_bitrates = None
        if video_supported and audio_supported:
            recommended_bitrates = {
                "video": self.QUALITY_PRESETS[QualityPreset.MEDIUM]["video_bitrate"],
                "audio": self.QUALITY_PRESETS[QualityPreset.MEDIUM]["audio_bitrate"],
            }

        is_valid = video_supported and audio_supported and combination_valid

        return CodecValidationResult(
            is_valid=is_valid,
            video_codec_supported=video_supported,
            audio_codec_supported=audio_supported,
            combination_valid=combination_valid,
            warnings=warnings,
            errors=errors,
            recommended_bitrates=recommended_bitrates
        )

    async def validate_encoding_profile(
        self,
        profile: EncodingProfile
    ) -> CodecValidationResult:
        """
        Валидирует полный профиль кодирования.

        Args:
            profile: EncodingProfile для валидации

        Returns:
            CodecValidationResult с деталями валидации
        """
        result = await self.validate_codec_combination(
            profile.video_codec,
            profile.audio_codec
        )

        # Дополнительная валидация битрейтов
        if profile.video_bitrate is not None:
            is_valid, error = self._validate_bitrate(
                profile.video_bitrate,
                profile.video_codec,
                "video"
            )
            if not is_valid:
                result.errors.append(error)
                result.is_valid = False

        if profile.audio_bitrate is not None:
            is_valid, error = self._validate_bitrate(
                profile.audio_bitrate,
                profile.audio_codec,
                "audio"
            )
            if not is_valid:
                result.errors.append(error)
                result.is_valid = False

        # Валидация разрешения
        if profile.resolution is not None:
            if not self._validate_resolution(profile.resolution):
                result.errors.append(
                    f"Invalid resolution format: {profile.resolution}. "
                    f"Expected format: WIDTHxHEIGHT (e.g., 1920x1080)"
                )
                result.is_valid = False

        return result

    def _validate_resolution(self, resolution: str) -> bool:
        """
        Валидирует формат разрешения.

        Args:
            resolution: Строка разрешения (например, "1920x1080")

        Returns:
            True если формат валиден
        """
        try:
            parts = resolution.lower().split('x')
            if len(parts) != 2:
                return False
            width = int(parts[0])
            height = int(parts[1])
            return width > 0 and height > 0
        except (ValueError, AttributeError):
            return False

    def get_quality_preset(self, preset: str) -> Optional[Dict]:
        """
        Получает настройки пресета качества.

        Args:
            preset: Название пресета (low, medium, high, ultra)

        Returns:
            Словарь с настройками или None если пресет не найден
        """
        try:
            quality_preset = QualityPreset(preset)
            return self.QUALITY_PRESETS.get(quality_preset)
        except ValueError:
            return None

    def create_profile_from_preset(
        self,
        preset: str,
        video_codec: str = "h264",
        audio_codec: str = "aac"
    ) -> Optional[EncodingProfile]:
        """
        Создает профиль кодирования из пресета качества.

        Args:
            preset: Пресет качества (low, medium, high, ultra)
            video_codec: Видео кодек
            audio_codec: Аудио кодек

        Returns:
            EncodingProfile или None если пресет не найден
        """
        settings = self.get_quality_preset(preset)
        if not settings:
            return None

        return EncodingProfile(
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_bitrate=settings["video_bitrate"],
            audio_bitrate=settings["audio_bitrate"],
            resolution=settings["resolution"],
            quality_preset=preset
        )

    def get_supported_codecs(self) -> Dict[str, List[str]]:
        """
        Получает список поддерживаемых кодеков.

        Returns:
            Словарь с video и audio кодеками
        """
        return {
            "video": [c.value for c in VideoCodec],
            "audio": [c.value for c in AudioCodec],
        }

    def get_valid_combinations(self) -> Dict[str, List[str]]:
        """
        Получает валидные комбинации кодеков.

        Returns:
            Словарь {video_codec: [audio_codecs]}
        """
        return {
            video_codec.value: [ac.value for ac in audio_codecs]
            for video_codec, audio_codecs in self.VALID_CODEC_COMBINATIONS.items()
        }

    def clear_codec_cache(self):
        """
        Очищает кеш поддержки кодеков.
        Полезно после обновления FFmpeg.
        """
        self._ffmpeg_codec_cache = None
        self._cache_initialized = False
        log.debug("FFmpeg codec cache cleared")


# Singleton instance
encoding_profile_service = EncodingProfileService()


# Dependency для FastAPI
async def get_encoding_profile_service() -> EncodingProfileService:
    """FastAPI dependency для получения сервиса профилей кодирования"""
    return encoding_profile_service
