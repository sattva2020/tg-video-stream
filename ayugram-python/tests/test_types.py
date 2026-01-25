"""
Unit tests for PyTgCalls-compatible type definitions.

This module tests the type definitions in ayugram.types, ensuring
they mirror PyTgCalls types correctly and provide proper dataclass functionality.
"""

import pytest
from ayugram.types import (
    AudioPiped,
    AudioVideoPiped,
    HighQualityAudio,
    HighQualityVideo,
    StreamType,
)


# ============================================================================
# HighQualityAudio Tests
# ============================================================================


class TestHighQualityAudio:
    """Test HighQualityAudio type definition."""

    def test_init_high_quality_audio(self):
        """Test HighQualityAudio initialization."""
        audio_params = HighQualityAudio()
        assert isinstance(audio_params, HighQualityAudio)

    def test_high_quality_audio_is_dataclass(self):
        """Test that HighQualityAudio is a dataclass."""
        audio_params = HighQualityAudio()
        assert hasattr(audio_params, "__dataclass_fields__")

    def test_high_quality_audio_can_be_instantiated_empty(self):
        """Test that HighQualityAudio can be created without parameters."""
        audio_params = HighQualityAudio()
        # Should not raise any errors


# ============================================================================
# HighQualityVideo Tests
# ============================================================================


class TestHighQualityVideo:
    """Test HighQualityVideo type definition."""

    def test_init_high_quality_video(self):
        """Test HighQualityVideo initialization."""
        video_params = HighQualityVideo()
        assert isinstance(video_params, HighQualityVideo)

    def test_high_quality_video_is_dataclass(self):
        """Test that HighQualityVideo is a dataclass."""
        video_params = HighQualityVideo()
        assert hasattr(video_params, "__dataclass_fields__")

    def test_high_quality_video_can_be_instantiated_empty(self):
        """Test that HighQualityVideo can be created without parameters."""
        video_params = HighQualityVideo()
        # Should not raise any errors


# ============================================================================
# AudioPiped Tests
# ============================================================================


class TestAudioPiped:
    """Test AudioPiped type definition."""

    def test_init_audio_piped_with_required_params(self):
        """Test AudioPiped initialization with required data_path."""
        stream = AudioPiped(data_path="https://example.com/audio.mp3")
        assert stream.data_path == "https://example.com/audio.mp3"
        assert stream.audio_parameters is None
        assert stream.additional_ffmpeg_parameters == []

    def test_init_audio_piped_with_audio_parameters(self):
        """Test AudioPiped initialization with audio quality parameters."""
        audio_params = HighQualityAudio()
        stream = AudioPiped(
            data_path="https://example.com/audio.mp3",
            audio_parameters=audio_params,
        )
        assert stream.data_path == "https://example.com/audio.mp3"
        assert stream.audio_parameters is audio_params
        assert isinstance(stream.audio_parameters, HighQualityAudio)

    def test_init_audio_piped_with_ffmpeg_parameters(self):
        """Test AudioPiped initialization with FFmpeg parameters."""
        ffmpeg_params = ["-re", "-bufsize", "96000k"]
        stream = AudioPiped(
            data_path="https://example.com/audio.mp3",
            additional_ffmpeg_parameters=ffmpeg_params,
        )
        assert stream.data_path == "https://example.com/audio.mp3"
        assert stream.additional_ffmpeg_parameters == ffmpeg_params

    def test_init_audio_piped_with_all_parameters(self):
        """Test AudioPiped initialization with all parameters."""
        audio_params = HighQualityAudio()
        ffmpeg_params = ["-re", "-bufsize", "96000k"]
        stream = AudioPiped(
            data_path="https://example.com/audio.mp3",
            audio_parameters=audio_params,
            additional_ffmpeg_parameters=ffmpeg_params,
        )
        assert stream.data_path == "https://example.com/audio.mp3"
        assert stream.audio_parameters is audio_params
        assert stream.additional_ffmpeg_parameters == ffmpeg_params

    def test_audio_piped_default_ffmpeg_parameters_is_list(self):
        """Test that default additional_ffmpeg_parameters is a mutable list."""
        stream1 = AudioPiped(data_path="test1.mp3")
        stream2 = AudioPiped(data_path="test2.mp3")
        # Each instance should have its own list
        stream1.additional_ffmpeg_parameters.append("-re")
        assert stream1.additional_ffmpeg_parameters == ["-re"]
        assert stream2.additional_ffmpeg_parameters == []

    def test_audio_piped_is_dataclass(self):
        """Test that AudioPiped is a dataclass."""
        stream = AudioPiped(data_path="test.mp3")
        assert hasattr(stream, "__dataclass_fields__")

    def test_audio_piped_equality(self):
        """Test AudioPiped equality comparison."""
        stream1 = AudioPiped(data_path="test.mp3")
        stream2 = AudioPiped(data_path="test.mp3")
        stream3 = AudioPiped(data_path="other.mp3")
        assert stream1 == stream2
        assert stream1 != stream3

    def test_audio_piped_with_local_file_path(self):
        """Test AudioPiped with local file path."""
        stream = AudioPiped(data_path="/path/to/audio.mp3")
        assert stream.data_path == "/path/to/audio.mp3"

    def test_audio_piped_with_stream_url(self):
        """Test AudioPiped with streaming URL."""
        stream = AudioPiped(data_path="https://stream.example.com/audio.mp3")
        assert stream.data_path == "https://stream.example.com/audio.mp3"

    def test_audio_piped_repr(self):
        """Test AudioPiped string representation."""
        stream = AudioPiped(data_path="test.mp3")
        repr_str = repr(stream)
        assert "AudioPiped" in repr_str
        assert "test.mp3" in repr_str


# ============================================================================
# AudioVideoPiped Tests
# ============================================================================


class TestAudioVideoPiped:
    """Test AudioVideoPiped type definition."""

    def test_init_audio_video_piped_with_required_params(self):
        """Test AudioVideoPiped initialization with required data_path."""
        stream = AudioVideoPiped(data_path="https://example.com/video.mp4")
        assert stream.data_path == "https://example.com/video.mp4"
        assert stream.video_parameters is None
        assert stream.audio_parameters is None
        assert stream.additional_ffmpeg_parameters == []

    def test_init_audio_video_piped_with_video_parameters(self):
        """Test AudioVideoPiped initialization with video quality parameters."""
        video_params = HighQualityVideo()
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            video_parameters=video_params,
        )
        assert stream.data_path == "https://example.com/video.mp4"
        assert stream.video_parameters is video_params
        assert isinstance(stream.video_parameters, HighQualityVideo)

    def test_init_audio_video_piped_with_audio_parameters(self):
        """Test AudioVideoPiped initialization with audio quality parameters."""
        audio_params = HighQualityAudio()
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            audio_parameters=audio_params,
        )
        assert stream.data_path == "https://example.com/video.mp4"
        assert stream.audio_parameters is audio_params
        assert isinstance(stream.audio_parameters, HighQualityAudio)

    def test_init_audio_video_piped_with_both_quality_parameters(self):
        """Test AudioVideoPiped initialization with both audio and video quality."""
        video_params = HighQualityVideo()
        audio_params = HighQualityAudio()
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            video_parameters=video_params,
            audio_parameters=audio_params,
        )
        assert stream.video_parameters is video_params
        assert stream.audio_parameters is audio_params

    def test_init_audio_video_piped_with_ffmpeg_parameters(self):
        """Test AudioVideoPiped initialization with FFmpeg parameters."""
        ffmpeg_params = ["-re", "-preset", "fast"]
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            additional_ffmpeg_parameters=ffmpeg_params,
        )
        assert stream.additional_ffmpeg_parameters == ffmpeg_params

    def test_init_audio_video_piped_with_all_parameters(self):
        """Test AudioVideoPiped initialization with all parameters."""
        video_params = HighQualityVideo()
        audio_params = HighQualityAudio()
        ffmpeg_params = ["-re", "-preset", "fast"]
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            video_parameters=video_params,
            audio_parameters=audio_params,
            additional_ffmpeg_parameters=ffmpeg_params,
        )
        assert stream.data_path == "https://example.com/video.mp4"
        assert stream.video_parameters is video_params
        assert stream.audio_parameters is audio_params
        assert stream.additional_ffmpeg_parameters == ffmpeg_params

    def test_audio_video_piped_default_ffmpeg_parameters_is_list(self):
        """Test that default additional_ffmpeg_parameters is a mutable list."""
        stream1 = AudioVideoPiped(data_path="test1.mp4")
        stream2 = AudioVideoPiped(data_path="test2.mp4")
        # Each instance should have its own list
        stream1.additional_ffmpeg_parameters.append("-re")
        assert stream1.additional_ffmpeg_parameters == ["-re"]
        assert stream2.additional_ffmpeg_parameters == []

    def test_audio_video_piped_is_dataclass(self):
        """Test that AudioVideoPiped is a dataclass."""
        stream = AudioVideoPiped(data_path="test.mp4")
        assert hasattr(stream, "__dataclass_fields__")

    def test_audio_video_piped_equality(self):
        """Test AudioVideoPiped equality comparison."""
        stream1 = AudioVideoPiped(data_path="test.mp4")
        stream2 = AudioVideoPiped(data_path="test.mp4")
        stream3 = AudioVideoPiped(data_path="other.mp4")
        assert stream1 == stream2
        assert stream1 != stream3

    def test_audio_video_piped_with_local_file_path(self):
        """Test AudioVideoPiped with local file path."""
        stream = AudioVideoPiped(data_path="/path/to/video.mp4")
        assert stream.data_path == "/path/to/video.mp4"

    def test_audio_video_piped_with_stream_url(self):
        """Test AudioVideoPiped with streaming URL."""
        stream = AudioVideoPiped(data_path="https://stream.example.com/video.mp4")
        assert stream.data_path == "https://stream.example.com/video.mp4"

    def test_audio_video_piped_repr(self):
        """Test AudioVideoPiped string representation."""
        stream = AudioVideoPiped(data_path="test.mp4")
        repr_str = repr(stream)
        assert "AudioVideoPiped" in repr_str
        assert "test.mp4" in repr_str


# ============================================================================
# StreamType Tests
# ============================================================================


class TestStreamType:
    """Test StreamType type alias."""

    def test_audio_piped_is_stream_type(self):
        """Test that AudioPiped is compatible with StreamType."""
        stream: StreamType = AudioPiped(data_path="test.mp3")
        assert isinstance(stream, AudioPiped)
        assert isinstance(stream, StreamType.__args__)  # Union types have __args__

    def test_audio_video_piped_is_stream_type(self):
        """Test that AudioVideoPiped is compatible with StreamType."""
        stream: StreamType = AudioVideoPiped(data_path="test.mp4")
        assert isinstance(stream, AudioVideoPiped)

    def test_stream_type_accepts_audio_piped(self):
        """Test that StreamType union accepts AudioPiped."""
        stream = AudioPiped(data_path="test.mp3")
        # Should not raise when checking if it's a valid stream type
        assert isinstance(stream, (AudioPiped, AudioVideoPiped))

    def test_stream_type_accepts_audio_video_piped(self):
        """Test that StreamType union accepts AudioVideoPiped."""
        stream = AudioVideoPiped(data_path="test.mp4")
        assert isinstance(stream, (AudioPiped, AudioVideoPiped))


# ============================================================================
# Type Compatibility Tests
# ============================================================================


class TestTypeCompatibility:
    """Test PyTgCalls compatibility of types."""

    def test_audio_piped_matches_pytgcalls_interface(self):
        """Test that AudioPiped matches PyTgCalls AudioPiped interface."""
        stream = AudioPiped(
            data_path="test.mp3",
            audio_parameters=HighQualityAudio(),
            additional_ffmpeg_parameters=["-re"],
        )
        # Check that all expected attributes exist
        assert hasattr(stream, "data_path")
        assert hasattr(stream, "audio_parameters")
        assert hasattr(stream, "additional_ffmpeg_parameters")

    def test_audio_video_piped_matches_pytgcalls_interface(self):
        """Test that AudioVideoPiped matches PyTgCalls AudioVideoPiped interface."""
        stream = AudioVideoPiped(
            data_path="test.mp4",
            video_parameters=HighQualityVideo(),
            audio_parameters=HighQualityAudio(),
            additional_ffmpeg_parameters=["-re"],
        )
        # Check that all expected attributes exist
        assert hasattr(stream, "data_path")
        assert hasattr(stream, "video_parameters")
        assert hasattr(stream, "audio_parameters")
        assert hasattr(stream, "additional_ffmpeg_parameters")

    def test_high_quality_audio_matches_pytgcalls_interface(self):
        """Test that HighQualityAudio matches PyTgCalls interface."""
        audio_params = HighQualityAudio()
        # Should be instantiable
        assert isinstance(audio_params, HighQualityAudio)

    def test_high_quality_video_matches_pytgcalls_interface(self):
        """Test that HighQualityVideo matches PyTgCalls interface."""
        video_params = HighQualityVideo()
        # Should be instantiable
        assert isinstance(video_params, HighQualityVideo)


# ============================================================================
# Integration Tests
# ============================================================================


class TestTypeIntegration:
    """Integration tests for type usage."""

    def test_create_audio_stream_for_voice_chat(self):
        """Test creating audio stream for voice chat use case."""
        stream = AudioPiped(
            data_path="https://example.com/music.mp3",
            audio_parameters=HighQualityAudio(),
        )
        assert isinstance(stream, AudioPiped)
        assert stream.data_path.endswith(".mp3")

    def test_create_video_stream_for_video_chat(self):
        """Test creating video stream for video chat use case."""
        stream = AudioVideoPiped(
            data_path="https://example.com/video.mp4",
            video_parameters=HighQualityVideo(),
            audio_parameters=HighQualityAudio(),
        )
        assert isinstance(stream, AudioVideoPiped)
        assert stream.data_path.endswith(".mp4")

    def test_stream_with_custom_ffmpeg_args(self):
        """Test creating stream with custom FFmpeg arguments."""
        custom_args = [
            "-re",
            "-bufsize",
            "96000k",
            "-probesize",
            "32",
            "-analyzeduration",
            "0",
        ]
        stream = AudioPiped(
            data_path="https://example.com/audio.mp3",
            additional_ffmpeg_parameters=custom_args,
        )
        assert len(stream.additional_ffmpeg_parameters) == 6
        assert "-re" in stream.additional_ffmpeg_parameters

    def test_multiple_streams_independent(self):
        """Test that multiple stream instances are independent."""
        stream1 = AudioPiped(data_path="song1.mp3")
        stream2 = AudioPiped(data_path="song2.mp3")
        stream1.additional_ffmpeg_parameters.append("-re")

        assert stream1.data_path == "song1.mp3"
        assert stream2.data_path == "song2.mp3"
        assert "-re" in stream1.additional_ffmpeg_parameters
        assert "-re" not in stream2.additional_ffmpeg_parameters

    def test_stream_type_polymorphism(self):
        """Test using StreamType for polymorphic stream handling."""
        streams: list[StreamType] = [
            AudioPiped(data_path="audio.mp3"),
            AudioVideoPiped(data_path="video.mp4"),
        ]

        assert len(streams) == 2
        assert isinstance(streams[0], AudioPiped)
        assert isinstance(streams[1], AudioVideoPiped)

        # Process polymorphically
        for stream in streams:
            assert hasattr(stream, "data_path")
            assert isinstance(stream.data_path, str)
