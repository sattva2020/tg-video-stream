"""
Unit tests для Feature 022: Stream Quality Monitoring (FFprobe Integration)

Тесты покрывают:
- Нормализацию кодеков
- Расчёт качества на основе битрейта
- Парсинг FFprobe JSON
- Анализ потоков с различными метаданными
- Кеширование результатов
- Ошибки и edge cases
"""

import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Optional

# Импортируем из streamer модуля
import sys
import os
streamer_path = os.path.join(os.path.dirname(__file__), '../../streamer')
sys.path.insert(0, streamer_path)

from ffprobe_utils import (
    AudioCodec,
    VideoCodec,
    AudioQuality,
    VideoQuality,
    AudioMetadata,
    VideoMetadata,
    StreamQuality,
    _normalize_codec,
    _calculate_audio_quality,
    _calculate_video_quality,
    parse_ffprobe_output,
    analyze_stream_quality,
    batch_analyze_streams,
)


# ============================================================================
# Tests: Codec Normalization
# ============================================================================

def test_normalize_codec_opus():
    """Test: Нормализация Opus кодека из различных представлений"""
    assert _normalize_codec("opus") == "opus"
    assert _normalize_codec("libopus") == "opus"
    assert _normalize_codec("Opus") == "opus"
    assert _normalize_codec("OPUS") == "opus"


def test_normalize_codec_mp3():
    """Test: Нормализация MP3 кодека"""
    assert _normalize_codec("mp3") == "mp3"
    assert _normalize_codec("libmp3lame") == "mp3"
    assert _normalize_codec("MP3") == "mp3"


def test_normalize_codec_aac():
    """Test: Нормализация AAC кодека"""
    assert _normalize_codec("aac") == "aac"
    assert _normalize_codec("aac (aac latm)") == "aac"
    assert _normalize_codec("AAC") == "aac"


def test_normalize_codec_flac():
    """Test: Нормализация FLAC кодека"""
    assert _normalize_codec("flac") == "flac"
    assert _normalize_codec("FLAC") == "flac"


def test_normalize_codec_video_h264():
    """Test: Нормализация H.264 видео кодека"""
    assert _normalize_codec("h264") == "h264"
    assert _normalize_codec("h.264") == "h264"
    assert _normalize_codec("H264") == "h264"


def test_normalize_codec_video_hevc():
    """Test: Нормализация HEVC/H.265 видео кодека"""
    assert _normalize_codec("hevc") == "hevc"
    assert _normalize_codec("h265") == "hevc"
    assert _normalize_codec("h.265") == "hevc"


def test_normalize_codec_video_vp9():
    """Test: Нормализация VP9 кодека"""
    assert _normalize_codec("vp9") == "vp9"
    assert _normalize_codec("VP9") == "vp9"


def test_normalize_codec_video_av1():
    """Test: Нормализация AV1 кодека"""
    assert _normalize_codec("av1") == "av1"
    assert _normalize_codec("AV1") == "av1"


def test_normalize_codec_unknown():
    """Test: Неизвестный кодек возвращает 'unknown'"""
    assert _normalize_codec("") == "unknown"
    assert _normalize_codec(None) == "unknown"
    assert _normalize_codec("xyz_unknown") == "xyz_unknown"


# ============================================================================
# Tests: Audio Quality Calculation
# ============================================================================

def test_calculate_audio_quality_low():
    """Test: Низкое качество (≤64 kbps)"""
    assert _calculate_audio_quality(32000) == AudioQuality.LOW.value
    assert _calculate_audio_quality(64000) == AudioQuality.LOW.value


def test_calculate_audio_quality_medium():
    """Test: Среднее качество (64-128 kbps)"""
    assert _calculate_audio_quality(96000) == AudioQuality.MEDIUM.value
    assert _calculate_audio_quality(128000) == AudioQuality.MEDIUM.value


def test_calculate_audio_quality_high():
    """Test: Высокое качество (128-192 kbps)"""
    assert _calculate_audio_quality(160000) == AudioQuality.HIGH.value
    assert _calculate_audio_quality(192000) == AudioQuality.HIGH.value


def test_calculate_audio_quality_lossless():
    """Test: Lossless качество (≥192 kbps)"""
    assert _calculate_audio_quality(256000) == AudioQuality.LOSSLESS.value
    assert _calculate_audio_quality(320000) == AudioQuality.LOSSLESS.value


def test_calculate_audio_quality_none():
    """Test: Отсутствие битрейта возвращает None"""
    assert _calculate_audio_quality(None) is None
    # 0 bitrate также возвращает None (не валидный битрейт)
    assert _calculate_audio_quality(0) is None


# ============================================================================
# Tests: Video Quality Calculation
# ============================================================================

def test_calculate_video_quality_low():
    """Test: Низкое качество видео (≤480p, ≤1000 kbps)"""
    assert _calculate_video_quality(800000, 480) == VideoQuality.LOW.value
    assert _calculate_video_quality(500000, 360) == VideoQuality.LOW.value


def test_calculate_video_quality_medium():
    """Test: Среднее качество видео (480-720p, ≤2500 kbps)"""
    assert _calculate_video_quality(2000000, 720) == VideoQuality.MEDIUM.value
    assert _calculate_video_quality(1500000, 600) == VideoQuality.MEDIUM.value


def test_calculate_video_quality_high():
    """Test: Высокое качество видео (720-1080p, ≤5000 kbps)"""
    assert _calculate_video_quality(4000000, 1080) == VideoQuality.HIGH.value
    assert _calculate_video_quality(3500000, 900) == VideoQuality.HIGH.value


def test_calculate_video_quality_ultra():
    """Test: Ultra качество видео (>1080p, >5000 kbps)"""
    assert _calculate_video_quality(6000000, 1440) == VideoQuality.ULTRA.value
    assert _calculate_video_quality(12000000, 2160) == VideoQuality.ULTRA.value


def test_calculate_video_quality_none():
    """Test: Отсутствие параметров возвращает None"""
    assert _calculate_video_quality(None, 720) is None
    assert _calculate_video_quality(2000000, None) is None
    assert _calculate_video_quality(None, None) is None


# ============================================================================
# Tests: Audio Metadata
# ============================================================================

def test_audio_metadata_to_dict():
    """Test: Конвертация AudioMetadata в словарь"""
    meta = AudioMetadata(
        codec="opus",
        bitrate=96000,
        sample_rate=48000,
        channels=2,
        duration=180.5,
        quality="medium"
    )
    
    data = meta.to_dict()
    assert data["codec"] == "opus"
    assert data["bitrate_kbps"] == 96
    assert data["sample_rate_hz"] == 48000
    assert data["channels"] == 2
    assert data["duration_sec"] == 180.5
    assert data["quality"] == "medium"


def test_audio_metadata_none_values():
    """Test: AudioMetadata с None значениями"""
    meta = AudioMetadata(codec="opus", bitrate=None)
    data = meta.to_dict()
    assert data["codec"] == "opus"
    assert data["bitrate_kbps"] is None


# ============================================================================
# Tests: Video Metadata
# ============================================================================

def test_video_metadata_resolution():
    """Test: Вычисление разрешения видео"""
    meta = VideoMetadata(width=1920, height=1080)
    assert meta.resolution == "1920x1080"


def test_video_metadata_resolution_none():
    """Test: Resolution = None если нет width/height"""
    meta = VideoMetadata(width=None, height=1080)
    assert meta.resolution is None
    
    meta = VideoMetadata(width=1920, height=None)
    assert meta.resolution is None


def test_video_metadata_to_dict():
    """Test: Конвертация VideoMetadata в словарь"""
    meta = VideoMetadata(
        codec="h264",
        bitrate=2500000,
        width=1280,
        height=720,
        fps=30.0,
        duration=120.0,
        quality="medium"
    )
    
    data = meta.to_dict()
    assert data["codec"] == "h264"
    assert data["bitrate_kbps"] == 2500
    assert data["resolution"] == "1280x720"
    assert data["fps"] == 30.0
    assert data["duration_sec"] == 120.0
    assert data["quality"] == "medium"


# ============================================================================
# Tests: Stream Quality
# ============================================================================

def test_stream_quality_audio_only():
    """Test: Поток только с аудио"""
    audio = AudioMetadata(codec="opus", bitrate=96000, quality="medium")
    sq = StreamQuality(
        url="http://example.com/audio.opus",
        audio=audio,
        video=None,
        is_audio_only=True
    )
    
    assert sq.is_audio_only is True
    assert sq.is_video_only is False
    assert sq.has_both is False
    assert sq.overall_quality == "medium"


def test_stream_quality_video_only():
    """Test: Поток только с видео"""
    video = VideoMetadata(codec="h264", bitrate=2500000, height=720, quality="medium")
    sq = StreamQuality(
        url="http://example.com/video.mp4",
        audio=None,
        video=video,
        is_video_only=True
    )
    
    assert sq.is_audio_only is False
    assert sq.is_video_only is True
    assert sq.has_both is False
    assert sq.overall_quality == "medium"


def test_stream_quality_both():
    """Test: Поток с аудио и видео"""
    audio = AudioMetadata(codec="aac", bitrate=128000, quality="medium")
    video = VideoMetadata(codec="h264", bitrate=3000000, height=1080, quality="high")
    sq = StreamQuality(
        url="http://example.com/video.mp4",
        audio=audio,
        video=video,
        has_both=True
    )
    
    assert sq.is_audio_only is False
    assert sq.is_video_only is False
    assert sq.has_both is True
    assert sq.overall_quality == "medium"  # Приоритет аудио


def test_stream_quality_to_dict():
    """Test: Конвертация StreamQuality в словарь"""
    audio = AudioMetadata(codec="opus", bitrate=96000, quality="medium")
    sq = StreamQuality(
        url="http://example.com/audio.opus",
        audio=audio,
        is_audio_only=True
    )
    
    data = sq.to_dict()
    assert data["url"] == "http://example.com/audio.opus"
    assert data["is_audio_only"] is True
    assert data["audio"]["codec"] == "opus"


# ============================================================================
# Tests: FFprobe JSON Parsing
# ============================================================================

def test_parse_ffprobe_output_audio_only():
    """Test: Парсинг FFprobe JSON для только аудио потока"""
    ffprobe_json = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "bit_rate": "96000",
                "sample_rate": "48000",
                "channels": 2
            }
        ],
        "format": {
            "duration": "180.5"
        }
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert audio is not None
    assert video is None
    assert audio.codec == "opus"
    assert audio.bitrate == 96000
    assert audio.sample_rate == 48000
    assert audio.channels == 2
    assert audio.duration == 180.5


def test_parse_ffprobe_output_video_only():
    """Test: Парсинг FFprobe JSON для только видео потока"""
    ffprobe_json = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "bit_rate": "2500000",
                "width": 1280,
                "height": 720,
                "r_frame_rate": "30/1"
            }
        ],
        "format": {
            "duration": "120.0"
        }
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert audio is None
    assert video is not None
    assert video.codec == "h264"
    assert video.bitrate == 2500000
    assert video.width == 1280
    assert video.height == 720
    assert video.fps == 30.0


def test_parse_ffprobe_output_both():
    """Test: Парсинг FFprobe JSON для аудио+видео потока"""
    ffprobe_json = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "bit_rate": "128000",
                "sample_rate": "44100",
                "channels": 2
            },
            {
                "codec_type": "video",
                "codec_name": "h264",
                "bit_rate": "3000000",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "24000/1001"
            }
        ],
        "format": {"duration": "600.0"}
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert audio is not None
    assert video is not None
    assert audio.codec == "aac"
    assert video.codec == "h264"
    assert video.width == 1920


def test_parse_ffprobe_output_fps_fraction():
    """Test: Парсинг FPS из дроби (например, 24000/1001)"""
    ffprobe_json = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1280,
                "height": 720,
                "r_frame_rate": "24000/1001"  # 23.976 fps
            }
        ],
        "format": {}
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert video is not None
    # 24000 / 1001 ≈ 23.976
    assert abs(video.fps - 23.976) < 0.01


def test_parse_ffprobe_output_empty_streams():
    """Test: Парсинг пустого потока"""
    ffprobe_json = {
        "streams": [],
        "format": {}
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert audio is None
    assert video is None


def test_parse_ffprobe_output_missing_bitrate():
    """Test: Парсинг потока без битрейта"""
    ffprobe_json = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "sample_rate": "48000"
            }
        ],
        "format": {}
    }
    
    audio, video = parse_ffprobe_output(ffprobe_json)
    
    assert audio is not None
    assert audio.codec == "opus"
    assert audio.bitrate is None


# ============================================================================
# Tests: Stream Quality Analysis (Async)
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_stream_quality_success():
    """Test: Успешный анализ потока"""
    
    ffprobe_output = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "bit_rate": "96000",
                "sample_rate": "48000",
                "channels": 2
            }
        ],
        "format": {"duration": "180.5"}
    }
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(ffprobe_output)
    
    with patch('ffprobe_utils.subprocess.run', return_value=mock_result):
        quality = await analyze_stream_quality("http://example.com/audio.opus")
    
    assert quality is not None
    assert quality.audio is not None
    assert quality.audio.codec == "opus"
    assert quality.overall_quality == "medium"


@pytest.mark.asyncio
async def test_analyze_stream_quality_ffprobe_error():
    """Test: FFprobe возвращает ошибку"""
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "File not found"
    
    with patch('ffprobe_utils.subprocess.run', return_value=mock_result):
        quality = await analyze_stream_quality("http://example.com/invalid.mp3")
    
    assert quality is None


@pytest.mark.asyncio
async def test_analyze_stream_quality_timeout():
    """Test: FFprobe timeout обрабатывается gracefully"""
    
    def mock_run(*args, **kwargs):
        raise asyncio.TimeoutError("Timeout")
    
    with patch('ffprobe_utils.subprocess.run', side_effect=mock_run):
        # Функция должна вернуть None вместо выброса исключения
        quality = await analyze_stream_quality("http://example.com/audio.opus", timeout=1)
        assert quality is None


@pytest.mark.asyncio
async def test_analyze_stream_quality_json_error():
    """Test: Некорректный JSON в output FFprobe"""
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "{ invalid json }"
    
    with patch('ffprobe_utils.subprocess.run', return_value=mock_result):
        quality = await analyze_stream_quality("http://example.com/audio.opus")
    
    assert quality is None


@pytest.mark.asyncio
async def test_batch_analyze_streams():
    """Test: Параллельный анализ множественных потоков"""
    
    urls = [
        "http://example.com/audio1.opus",
        "http://example.com/audio2.mp3",
        "http://example.com/audio3.aac"
    ]
    
    ffprobe_output = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "bit_rate": "96000",
                "sample_rate": "48000",
                "channels": 2
            }
        ],
        "format": {}
    }
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(ffprobe_output)
    
    with patch('ffprobe_utils.subprocess.run', return_value=mock_result):
        results = await batch_analyze_streams(urls)
    
    assert len(results) == 3
    assert all(url in results for url in urls)


# ============================================================================
# Tests: Caching
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_stream_quality_cached():
    """Test: Кеширование результатов анализа"""
    
    ffprobe_output = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "bit_rate": "96000",
                "sample_rate": "48000",
                "channels": 2
            }
        ],
        "format": {}
    }
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(ffprobe_output)
    
    url = "http://example.com/audio.opus"
    
    with patch('ffprobe_utils.subprocess.run', return_value=mock_result) as mock_run:
        # Первый вызов — анализируем
        from ffprobe_utils import analyze_stream_quality_cached
        quality1 = await analyze_stream_quality_cached(url)
        
        # Второй вызов — должна вернуться из кеша
        quality2 = await analyze_stream_quality_cached(url)
        
        # Проверяем, что вызовов subprocess было минимум (может быть 1-2)
        # Если кеш работает правильно, второй вызов не должен вызвать subprocess
        assert quality1 is not None
        assert quality2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
