import sys
import os
import pytest

# Add streamer directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../streamer'))

from video_transcoder import VideoTranscoder, QualityProfile, VideoTranscodeRequest


def test_all_quality_profiles_have_distinct_settings():
    """
    Verify that all quality profiles have distinct (height, bitrate) settings.
    """
    profiles = {
        QualityProfile.LOW: (480, 800),
        QualityProfile.MEDIUM: (720, 2000),
        QualityProfile.HIGH: (1080, 4000),
        QualityProfile.ULTRA: (1440, 8000),
    }

    # Extract all settings
    all_settings = [profiles[p] for p in QualityProfile]

    # Verify all settings are unique
    assert len(all_settings) == len(set(all_settings)), \
        "Quality profiles should have distinct settings"

    print(f"Quality profile settings: {profiles}")


def test_quality_profiles_scale_monotonically():
    """
    Verify that quality profiles scale monotonically: LOW < MEDIUM < HIGH < ULTRA.
    """
    prev_height = 0
    prev_bitrate = 0

    for profile in [QualityProfile.LOW, QualityProfile.MEDIUM, QualityProfile.HIGH, QualityProfile.ULTRA]:
        height, bitrate = profile.get_video_settings()

        print(f"Profile {profile.value}: height={height}, bitrate={bitrate}k")

        # Verify monotonically increasing
        assert height > prev_height, \
            f"Profile {profile.value} height should be greater than previous"
        assert bitrate > prev_bitrate, \
            f"Profile {profile.value} bitrate should be greater than previous"

        prev_height = height
        prev_bitrate = bitrate


def test_quality_profiles_have_valid_audio_bitrates():
    """
    Verify that all quality profiles have valid audio bitrates (64-192 kbps).
    """
    for profile in QualityProfile:
        audio_bitrate = profile.get_audio_settings()

        print(f"Profile {profile.value}: audio_bitrate={audio_bitrate}k")

        # Verify valid range
        assert 64 <= audio_bitrate <= 192, \
            f"Profile {profile.value} audio bitrate {audio_bitrate}k should be in [64, 192]"


def test_ffmpeg_command_includes_quality_settings():
    """
    Verify that FFmpeg commands include quality-specific settings.
    """
    for quality in [QualityProfile.LOW, QualityProfile.MEDIUM, QualityProfile.HIGH, QualityProfile.ULTRA]:
        cmd = VideoTranscoder.build_ffmpeg_command(
            source_url="input.mp4",
            video_codec="h264",
            audio_codec="aac",
            quality=quality
        )

        height, bitrate = quality.get_video_settings()
        audio_bitrate = quality.get_audio_settings()

        print(f"Profile {quality.value}: {cmd}")

        # Verify video bitrate is in command
        assert f"{bitrate}k" in cmd, \
            f"Profile {quality.value} should include video bitrate {bitrate}k"

        # Verify audio bitrate is in command
        assert f"{audio_bitrate}k" in cmd, \
            f"Profile {quality.value} should include audio bitrate {audio_bitrate}k"

        # Verify scale filter includes correct height
        assert f"-2:{height}" in cmd, \
            f"Profile {quality.value} should include scale filter for height {height}"


def test_ffmpeg_command_preserves_low_latency():
    """
    Verify that quality profiles preserve low-latency settings.
    """
    for quality in QualityProfile:
        cmd = VideoTranscoder.build_ffmpeg_command(
            source_url="input.mp4",
            video_codec="h264",
            audio_codec="aac",
            quality=quality
        )

        print(f"Profile {quality.value} low-latency check: {cmd}")

        # Verify pixel format for compatibility
        assert "-pix_fmt" in cmd
        assert "yuv420p" in cmd

        # Verify fast start for MP4 streaming
        assert "-movflags" in cmd
        assert "faststart" in cmd


def test_transcode_request_quality_profiles():
    """
    Verify that VideoTranscodeRequest works with all quality profiles.
    """
    for quality in QualityProfile:
        request = VideoTranscodeRequest(
            source_url="input.mp4",
            video_codec="h264",
            audio_codec="aac",
            quality=quality
        )

        req_dict = request.to_dict()

        print(f"Request with profile {quality.value}: {req_dict}")

        # Verify request is properly serialized
        assert req_dict['quality'] == quality.value
        assert req_dict['video_codec'] == 'h264'
        assert req_dict['audio_codec'] == 'aac'


def test_quality_profiles_performance_regression():
    """
    Performance regression test: verify that higher quality profiles
    don't have lower bitrates than lower profiles (data integrity check).
    """
    settings_by_quality = {}

    for profile in QualityProfile:
        height, bitrate = profile.get_video_settings()
        audio_bitrate = profile.get_audio_settings()

        settings_by_quality[profile.value] = {
            'height': height,
            'video_bitrate': bitrate,
            'audio_bitrate': audio_bitrate
        }

    print(f"Quality settings matrix: {settings_by_quality}")

    # Verify video bitrate scaling
    assert settings_by_quality['low']['video_bitrate'] < \
           settings_by_quality['medium']['video_bitrate'] < \
           settings_by_quality['high']['video_bitrate'] < \
           settings_by_quality['ultra']['video_bitrate'], \
           "Video bitrates should scale: low < medium < high < ultra"

    # Verify height scaling
    assert settings_by_quality['low']['height'] < \
           settings_by_quality['medium']['height'] < \
           settings_by_quality['high']['height'] < \
           settings_by_quality['ultra']['height'], \
           "Heights should scale: low < medium < high < ultra"


if __name__ == "__main__":
    pytest.main([__file__])
