"""
Unit tests для Feature 003: Video Format Validation & Transcoding Pipeline
Subtask 5-4: Verify mobile video orientation correction with sample videos

Тесты покрывают:
- Детекцию ориентации из FFprobe метаданных
- Конвертацию ориентации в FFmpeg transpose фильтр
- Построение FFmpeg команд с коррекцией ориентации
- Коррекцию ориентации для мобильных видео (iOS/Android)
- Обработку edge cases и ошибок
"""

import pytest

# Импортируем из streamer модуля
import sys
import os
streamer_path = os.path.join(os.path.dirname(__file__), '../../streamer')
sys.path.insert(0, streamer_path)

from video_validator import VideoValidator
from video_transcoder import VideoTranscoder, QualityProfile


# ============================================================================
# Tests: Orientation Detection from FFprobe Metadata
# ============================================================================

def test_detect_orientation_from_format_tags_rotate():
    """Test: Детекция ориентации из format.tags.rotate"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": "90"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 90


def test_detect_orientation_from_format_tags_orientation():
    """Test: Детекция ориентации из format.tags.orientation"""
    ffprobe_json = {
        "format": {
            "tags": {
                "orientation": "180"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 180


def test_detect_orientation_from_quicktime_tag():
    """Test: Детекция ориентации из com.apple.quicktime.orientation (iOS videos)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "com.apple.quicktime.orientation": "270"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 270


def test_detect_orientation_from_stream_tags():
    """Test: Детекция ориентации из video stream tags"""
    ffprobe_json = {
        "format": {"tags": {}},
        "streams": [
            {
                "codec_type": "video",
                "tags": {
                    "rotate": "90"
                }
            }
        ]
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 90


def test_detect_orientation_from_side_data_list():
    """Test: Детекция ориентации из side_data_list.rotate"""
    ffprobe_json = {
        "format": {"tags": {}},
        "streams": [
            {
                "codec_type": "video",
                "tags": {},
                "side_data_list": [
                    {
                        "rotate": "180"
                    }
                ]
            }
        ]
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 180


def test_detect_orientation_no_metadata():
    """Test: Отсутствие метаданных ориентации возвращает None"""
    ffprobe_json = {
        "format": {"tags": {}},
        "streams": [
            {
                "codec_type": "video",
                "tags": {}
            }
        ]
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation is None


def test_detect_orientation_invalid_value():
    """Test: Некорректное значение ориентации игнорируется"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": "invalid"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation is None


def test_detect_orientation_priority_format_over_stream():
    """Test: Priority: format tags проверяются раньше stream tags"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": "90"
            }
        },
        "streams": [
            {
                "codec_type": "video",
                "tags": {
                    "rotate": "180"
                }
            }
        ]
    }

    # Должен вернуть значение из format tags
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 90


def test_detect_orientation_multiple_streams_video_only():
    """Test: Ориентация ищется только в video потоках"""
    ffprobe_json = {
        "format": {"tags": {}},
        "streams": [
            {
                "codec_type": "audio",
                "tags": {
                    "rotate": "90"
                }
            },
            {
                "codec_type": "video",
                "tags": {
                    "rotate": "180"
                }
            }
        ]
    }

    # Должен найти ориентацию только в video потоке
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 180


def test_detect_orientation_all_standard_values():
    """Test: Все стандартные значения ориентации (0, 90, 180, 270)"""
    for orientation_value in [0, 90, 180, 270]:
        ffprobe_json = {
            "format": {
                "tags": {
                    "rotate": str(orientation_value)
                }
            },
            "streams": []
        }

        orientation = VideoValidator.detect_orientation(ffprobe_json)
        assert orientation == orientation_value


# ============================================================================
# Tests: Transpose Value Conversion
# ============================================================================

def test_get_transpose_value_90_degrees():
    """Test: 90° против часовой стрелки = transpose=2"""
    transpose = VideoTranscoder._get_transpose_value(90)
    assert transpose == 2


def test_get_transpose_value_180_degrees():
    """Test: 180° = special case '1,transpose=1'"""
    transpose = VideoTranscoder._get_transpose_value(180)
    assert transpose == "1,transpose=1"


def test_get_transpose_value_270_degrees():
    """Test: 270° против часовой стрелки = transpose=1"""
    transpose = VideoTranscoder._get_transpose_value(270)
    assert transpose == 1


def test_get_transpose_value_0_degrees():
    """Test: 0° возвращает None (коррекция не требуется)"""
    transpose = VideoTranscoder._get_transpose_value(0)
    assert transpose is None


def test_get_transpose_value_invalid():
    """Test: Некорректное значение ориентации возвращает None"""
    transpose = VideoTranscoder._get_transpose_value(45)
    assert transpose is None

    transpose = VideoTranscoder._get_transpose_value(-90)
    assert transpose is None

    transpose = VideoTranscoder._get_transpose_value(360)
    assert transpose is None


# ============================================================================
# Tests: FFmpeg Command Building with Orientation
# ============================================================================

def test_build_ffmpeg_command_with_orientation_90():
    """Test: FFmpeg команда с ориентацией 90°"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="input.mp4",
        video_codec="h264",
        audio_codec="aac",
        orientation=90
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    assert "transpose=2" in cmd[vf_index + 1]


def test_build_ffmpeg_command_with_orientation_180():
    """Test: FFmpeg команда с ориентацией 180° (двойной transpose)"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="input.mp4",
        video_codec="h264",
        audio_codec="aac",
        orientation=180
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    # 180° требует два transpose
    assert "transpose=1,transpose=1" in cmd[vf_index + 1]


def test_build_ffmpeg_command_with_orientation_270():
    """Test: FFmpeg команда с ориентацией 270°"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="input.mp4",
        video_codec="h264",
        audio_codec="aac",
        orientation=270
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    assert "transpose=1" in cmd[vf_index + 1]


def test_build_ffmpeg_command_without_orientation():
    """Test: FFmpeg команда без ориентации (orientation=None)"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="input.mp4",
        video_codec="h264",
        audio_codec="aac",
        orientation=None
    )

    assert "ffmpeg" in cmd
    # transpose фильтр не должен присутствовать
    assert "-vf" not in cmd or "transpose" not in " ".join(cmd)


def test_build_ffmpeg_command_with_orientation_and_scale():
    """Test: FFmpeg команда с ориентацией и масштабированием"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="input.mp4",
        video_codec="h264",
        audio_codec="aac",
        orientation=90,
        width=1280,
        height=720
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    vf_filter = cmd[vf_index + 1]
    # Должен содержать и scale, и transpose
    assert "scale=" in vf_filter
    assert "transpose=2" in vf_filter


# ============================================================================
# Tests: Apply Orientation Correction
# ============================================================================

def test_apply_orientation_correction_90():
    """Test: Коррекция ориентации 90° против часовой стрелки"""
    cmd = VideoTranscoder.apply_orientation_correction(
        source_url="input.mp4",
        orientation=90,
        output_url="output.mp4"
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    assert cmd[vf_index + 1] == "transpose=2"
    assert "output.mp4" in cmd
    assert "-c:a" in cmd
    assert "copy" in cmd


def test_apply_orientation_correction_180():
    """Test: Коррекция ориентации 180°"""
    cmd = VideoTranscoder.apply_orientation_correction(
        source_url="input.mp4",
        orientation=180,
        output_url="output.mp4"
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    # 180° требует два transpose
    assert cmd[vf_index + 1] == "transpose=1,transpose=1"


def test_apply_orientation_correction_270():
    """Test: Коррекция ориентации 270° против часовой стрелки (90° по часовой)"""
    cmd = VideoTranscoder.apply_orientation_correction(
        source_url="input.mp4",
        orientation=270,
        output_url="output.mp4"
    )

    assert "ffmpeg" in cmd
    assert "-vf" in cmd
    vf_index = cmd.index("-vf")
    assert cmd[vf_index + 1] == "transpose=1"


def test_apply_orientation_correction_0():
    """Test: Ориентация 0° использует stream copy без перекодирования"""
    cmd = VideoTranscoder.apply_orientation_correction(
        source_url="input.mp4",
        orientation=0,
        output_url="output.mp4"
    )

    assert "ffmpeg" in cmd
    # Не должно быть -vf (transpose)
    assert "-vf" not in cmd
    # Должен быть stream copy
    assert "-c" in cmd
    copy_index = cmd.index("-c")
    assert cmd[copy_index + 1] == "copy"
    assert "-c:a" in cmd


def test_apply_orientation_correction_audio_copy():
    """Test: При коррекции ориентации аудио копируется без перекодирования"""
    cmd = VideoTranscoder.apply_orientation_correction(
        source_url="input.mp4",
        orientation=90,
        output_url="output.mp4"
    )

    # Аудио должно быть скопировано
    assert "-c:a" in cmd
    audio_index = cmd.index("-c:a")
    assert cmd[audio_index + 1] == "copy"


# ============================================================================
# Tests: Mobile Video Scenarios (iOS/Android)
# ============================================================================

def test_ios_video_landscape_orientation():
    """Test: iOS видео записанное в landscape (orientation=0)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "com.apple.quicktime.orientation": "0"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 0

    # Коррекция не требуется
    cmd = VideoTranscoder.apply_orientation_correction(
        "input.mp4", orientation, "output.mp4"
    )
    assert "-vf" not in cmd


def test_ios_video_portrait_orientation():
    """Test: iOS видео записанное в portrait (orientation=90)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "com.apple.quicktime.orientation": "90"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 90

    # Требуется коррекция
    cmd = VideoTranscoder.apply_orientation_correction(
        "input.mp4", orientation, "output.mp4"
    )
    assert "-vf" in cmd
    assert "transpose=2" in cmd


def test_android_video_rotation_metadata():
    """Test: Android видео с тегом rotate"""
    ffprobe_json = {
        "format": {"tags": {}},
        "streams": [
            {
                "codec_type": "video",
                "tags": {
                    "rotate": "270"
                }
            }
        ]
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 270

    # Требуется коррекция
    cmd = VideoTranscoder.apply_orientation_correction(
        "input.mp4", orientation, "output.mp4"
    )
    assert "-vf" in cmd
    assert "transpose=1" in cmd


def test_mobile_video_upside_down():
    """Test: Мобильное видео перевёрнуто (orientation=180)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": "180"
            }
        },
        "streams": []
    }

    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 180

    # Требуется двойная коррекция
    cmd = VideoTranscoder.apply_orientation_correction(
        "input.mp4", orientation, "output.mp4"
    )
    assert "-vf" in cmd
    assert "transpose=1,transpose=1" in cmd


def test_mobile_video_with_transcoding():
    """Test: Полное транскодирование мобильного видео с коррекцией ориентации"""
    cmd = VideoTranscoder.build_ffmpeg_command(
        source_url="mobile_video.mp4",
        video_codec="h264",
        audio_codec="aac",
        output_format="mp4",
        quality=QualityProfile.MEDIUM,
        orientation=90
    )

    # Проверяем наличие всех необходимых компонентов
    assert "ffmpeg" in cmd
    assert "-i" in cmd
    assert "-c:v" in cmd
    assert "h264" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert "-b:v" in cmd
    assert "-b:a" in cmd
    assert "-pix_fmt" in cmd
    assert "yuv420p" in cmd
    assert "-vf" in cmd

    vf_index = cmd.index("-vf")
    assert "transpose=2" in cmd[vf_index + 1]


# ============================================================================
# Tests: Edge Cases and Error Handling
# ============================================================================

def test_orientation_empty_ffprobe_json():
    """Test: Пустой FFprobe JSON"""
    ffprobe_json = {}
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation is None


def test_orientation_missing_format_and_streams():
    """Test: Отсутствует format и streams"""
    ffprobe_json = {
        "format": {},
        "streams": []
    }
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation is None


def test_orientation_numeric_value_in_tags():
    """Test: Числовое значение в тегах (вместо строки)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": 90  # Число, а не строка
            }
        },
        "streams": []
    }

    # Должен обрабатывать и числовые значения
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    assert orientation == 90


def test_orientation_float_value():
    """Test: Float значение ориентации (должно быть конвертировано в int)"""
    ffprobe_json = {
        "format": {
            "tags": {
                "rotate": 90.0
            }
        },
        "streams": []
    }

    # Float не должен конвертироваться (требуется int)
    orientation = VideoValidator.detect_orientation(ffprobe_json)
    # Если int(90.0) работает, то вернется 90, иначе None
    # Ожидаем, что код попытается int() и это сработает
    assert orientation is not None


def test_transpose_orientation_none():
    """Test: None как значение ориентации"""
    transpose = VideoTranscoder._get_transpose_value(None)
    assert transpose is None


def test_build_command_with_various_qualities_and_orientations():
    """Test: Комбинирование различных профилей качества с ориентацией"""
    for quality in [QualityProfile.LOW, QualityProfile.MEDIUM, QualityProfile.HIGH, QualityProfile.ULTRA]:
        for orientation in [None, 0, 90, 180, 270]:
            cmd = VideoTranscoder.build_ffmpeg_command(
                source_url="input.mp4",
                video_codec="h264",
                audio_codec="aac",
                quality=quality,
                orientation=orientation
            )

            assert "ffmpeg" in cmd
            assert "-b:v" in cmd
            assert "-b:a" in cmd

            # Проверяем orientation фильтр
            if orientation and orientation != 0:
                assert "-vf" in cmd
                vf_index = cmd.index("-vf")
                assert "transpose" in cmd[vf_index + 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
