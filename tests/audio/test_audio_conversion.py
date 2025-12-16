"""
Тесты для Phase 5 Audio Format Conversion (T051-T052)

Проверяет функцию convert_audio_format() для конвертации MP3/FLAC → Opus/WAV
через Rust transcoder с fallback на прямое использование.
"""

import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add streamer directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'streamer'))

import audio_utils


def async_test(func):
    """Decorator для запуска async тестов."""
    def wrapper(*args, **kwargs):
        import asyncio
        return asyncio.run(func(*args, **kwargs))
    return wrapper


class TestAudioConversion(unittest.TestCase):
    """Тесты для функции convert_audio_format()."""

    @patch('streamer.audio_utils.get_transcoding_profile')
    @patch('streamer.audio_utils.detect_content_type')
    @async_test
    async def test_convert_mp3_requires_conversion(self, mock_detect, mock_profile):
        """Тест определения MP3 как требующего конвертации."""
        # Setup
        mock_detect.return_value = "audio/mpeg"
        mock_profile.return_value = {"description": "Transcode MP3 to Opus"}
        
        # Test
        result = await audio_utils.convert_audio_format(
            source_url="https://example.com/song.mp3",
            use_rust_transcoder=False  # Используем fallback
        )
        
        # Verify - должен вернуть исходный URL при отключении transcoder
        self.assertEqual(result, "https://example.com/song.mp3")

    @async_test
    async def test_no_conversion_for_opus(self):
        """Тест пропуска конвертации для Opus."""
        # Opus - поддерживаемый формат
        source_url = "https://example.com/track.opus"
        
        # Test - должен вернуть исходный URL
        result = await audio_utils.convert_audio_format(
            source_url,
            use_rust_transcoder=False
        )
        
        # Verify
        self.assertEqual(result, source_url)

    @async_test
    async def test_disabled_rust_transcoder(self):
        """Тест отключения Rust transcoder через параметр."""
        source_url = "https://example.com/song.mp3"
        
        # Test
        result = await audio_utils.convert_audio_format(
            source_url,
            use_rust_transcoder=False
        )
        
        # Verify - должен вернуть исходный URL
        self.assertEqual(result, source_url)

    def test_get_transcoding_profile_flac(self):
        """Тест определения FLAC профиля."""
        profile = audio_utils.get_transcoding_profile("https://example.com/track.flac")
        # FLAC должен быть распознан
        self.assertIsNotNone(profile)

    def test_get_transcoding_profile_opus_not_needed(self):
        """Тест что Opus не требует конвертации."""
        profile = audio_utils.get_transcoding_profile("https://example.com/track.opus")
        # Opus - поддерживаемый формат, profile должен быть None
        self.assertIsNone(profile)

    def test_get_transcoding_profile_wav_needs_conversion(self):
        """Тест что WAV требует конвертации в Opus."""
        profile = audio_utils.get_transcoding_profile("https://example.com/track.wav")
        # WAV должен быть распознан как требующий конвертации
        self.assertIsNotNone(profile)

    @async_test
    async def test_detect_audio_formats(self):
        """Тест определения аудио форматов по расширению."""
        test_cases = [
            ("https://example.com/song.mp3", True),
            ("https://example.com/track.flac", True),
            ("https://example.com/audio.wav", True),
            ("https://example.com/stream.opus", True),
            ("https://example.com/file.ogg", True),
            ("https://example.com/video.mp4", False),
            ("https://example.com/doc.pdf", False),
        ]
        
        for url, expected_is_audio in test_cases:
            result = audio_utils.is_audio_file(url)
            self.assertEqual(
                result,
                expected_is_audio,
                f"is_audio_file({url}) = {result}, expected {expected_is_audio}"
            )

    def test_transcoding_profiles_exist(self):
        """Тест что транскодирующие профили определены."""
        # Проверяем что профили существуют
        self.assertIn("flac", audio_utils.TRANSCODING_PROFILES)
        self.assertIn("ogg", audio_utils.TRANSCODING_PROFILES)
        self.assertIn("wav", audio_utils.TRANSCODING_PROFILES)
        
        # Проверяем структуру
        for name, profile in audio_utils.TRANSCODING_PROFILES.items():
            self.assertIn("ffmpeg_args", profile)
            self.assertIn("extensions", profile)
            self.assertIn("match_mime", profile)
            self.assertIn("description", profile)


if __name__ == '__main__':
    unittest.main()

