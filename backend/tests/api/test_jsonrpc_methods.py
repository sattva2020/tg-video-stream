"""
Unit tests for JSON-RPC method implementations.
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.api.jsonrpc.methods.call_control import CallControlMethods
from src.api.jsonrpc.methods.media_streaming import MediaStreamingMethods
from src.services.stream_controller import StreamController
from src.services.playback_service import PlaybackService


class TestCallControlMethods:
    """Test CallControlMethods RPC methods"""

    @pytest.fixture
    def call_methods(self, mocker):
        """Create CallControlMethods instance with mocked StreamController"""
        mock_controller = mocker.Mock(spec=StreamController)
        mock_controller.start_stream.return_value = True
        mock_controller.stop_stream.return_value = True
        mock_controller.restart_stream.return_value = True
        mock_controller.get_logs.return_value = ["log line 1", "log line 2"]
        return CallControlMethods(mock_controller, user_id="test-user-id")

    @pytest.mark.asyncio
    async def test_start_call_success(self, call_methods):
        """Test start_call with valid parameters"""
        result = await call_methods.start_call(channel_id=123, quality="720p")
        assert result["success"] is True
        assert result["channel_id"] == 123
        assert result["quality"] == "720p"
        assert "message" in result
        call_methods.stream_controller.start_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_call_invalid_channel_id_negative(self, call_methods):
        """Test start_call raises ValueError for negative channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.start_call(channel_id=-1, quality="720p")

    @pytest.mark.asyncio
    async def test_start_call_invalid_channel_id_zero(self, call_methods):
        """Test start_call raises ValueError for zero channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.start_call(channel_id=0, quality="720p")

    @pytest.mark.asyncio
    async def test_start_call_invalid_channel_id_string(self, call_methods):
        """Test start_call raises ValueError for string channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.start_call(channel_id="invalid", quality="720p")

    @pytest.mark.asyncio
    async def test_start_call_invalid_quality(self, call_methods):
        """Test start_call raises ValueError for invalid quality"""
        with pytest.raises(ValueError, match="Invalid quality"):
            await call_methods.start_call(channel_id=123, quality="9999p")

    @pytest.mark.asyncio
    async def test_start_call_default_quality(self, call_methods):
        """Test start_call uses default quality of 720p"""
        result = await call_methods.start_call(channel_id=123)
        assert result["channel_id"] == 123
        assert result["quality"] == "720p"

    @pytest.mark.asyncio
    async def test_start_call_all_valid_qualities(self, call_methods):
        """Test start_call with all valid quality presets"""
        valid_qualities = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]
        for quality in valid_qualities:
            result = await call_methods.start_call(channel_id=123, quality=quality)
            assert result["quality"] == quality

    @pytest.mark.asyncio
    async def test_stop_call_success(self, call_methods):
        """Test stop_call with valid parameters"""
        result = await call_methods.stop_call(channel_id=123)
        assert result["success"] is True
        assert result["channel_id"] == 123
        assert "message" in result
        call_methods.stream_controller.stop_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_call_invalid_channel_id(self, call_methods):
        """Test stop_call raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.stop_call(channel_id=-5)

    @pytest.mark.asyncio
    async def test_restart_call_success(self, call_methods):
        """Test restart_call with valid parameters"""
        result = await call_methods.restart_call(channel_id=456)
        assert result["success"] is True
        assert result["channel_id"] == 456
        assert "message" in result
        call_methods.stream_controller.restart_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_call_invalid_channel_id(self, call_methods):
        """Test restart_call raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.restart_call(channel_id=0)

    @pytest.mark.asyncio
    async def test_get_stream_logs_success(self, call_methods):
        """Test get_stream_logs returns logs"""
        result = await call_methods.get_stream_logs(channel_id=789, lines=10)
        assert "logs" in result
        assert result["lines"] == 10
        assert isinstance(result["logs"], list)
        assert len(result["logs"]) == 2
        call_methods.stream_controller.get_logs.assert_called_once_with(lines=10)

    @pytest.mark.asyncio
    async def test_get_stream_logs_invalid_lines_zero(self, call_methods):
        """Test get_stream_logs raises ValueError for zero lines"""
        with pytest.raises(ValueError, match="lines must be a positive integer"):
            await call_methods.get_stream_logs(channel_id=789, lines=0)

    @pytest.mark.asyncio
    async def test_get_stream_logs_invalid_lines_negative(self, call_methods):
        """Test get_stream_logs raises ValueError for negative lines"""
        with pytest.raises(ValueError, match="lines must be a positive integer"):
            await call_methods.get_stream_logs(channel_id=789, lines=-10)

    @pytest.mark.asyncio
    async def test_get_stream_logs_invalid_channel_id(self, call_methods):
        """Test get_stream_logs raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await call_methods.get_stream_logs(channel_id=-1, lines=10)


class TestMediaStreamingMethods:
    """Test MediaStreamingMethods RPC methods"""

    @pytest.fixture
    def media_methods(self, db_session):
        """Create MediaStreamingMethods instance with mocked PlaybackService"""
        mock_service = Mock(spec=PlaybackService)
        # Configure mock return values
        mock_service.set_speed.return_value = {
            "user_id": 123,
            "channel_id": 123,
            "speed": 1.5,
            "pitch_correction": True,
            "message": "Speed changed to 1.5x"
        }
        mock_service.set_pitch.return_value = {
            "user_id": 123,
            "channel_id": 123,
            "pitch_semitones": 6,
            "pitch_correction": True,
            "message": "Pitch set to 6 semitones"
        }
        mock_service.set_equalizer_preset.return_value = {
            "success": True,
            "user_id": 123,
            "channel_id": 123,
            "preset": "rock",
            "display_name": "Rock",
            "description": "Rock music preset",
            "bands": [3, 5, 4, 3, 2, 1, 0, 0, 1, 2]
        }
        mock_service.set_equalizer_custom.return_value = {
            "success": True,
            "user_id": 123,
            "channel_id": 123,
            "preset": "custom",
            "bands": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        }
        mock_service.get_settings.return_value = {
            "user_id": 123,
            "channel_id": 123,
            "speed": 1.0,
            "pitch_correction": False,
            "equalizer_preset": "flat",
            "equalizer_custom": None,
            "language": "en",
            "auto_play": True,
            "shuffle": False,
            "repeat_mode": "none"
        }
        return MediaStreamingMethods(mock_service, user_id="123")

    @pytest.mark.asyncio
    async def test_set_playback_speed_valid(self, media_methods):
        """Test set_playback_speed with valid speed"""
        result = await media_methods.set_playback_speed(channel_id=123, speed=1.5)
        assert result["speed"] == 1.5
        assert "message" in result
        media_methods.playback_service.set_speed.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_playback_speed_minimum_boundary(self, media_methods):
        """Test set_playback_speed at minimum boundary (0.5)"""
        result = await media_methods.set_playback_speed(channel_id=123, speed=0.5)
        assert result["speed"] == 0.5

    @pytest.mark.asyncio
    async def test_set_playback_speed_maximum_boundary(self, media_methods):
        """Test set_playback_speed at maximum boundary (2.0)"""
        result = await media_methods.set_playback_speed(channel_id=123, speed=2.0)
        assert result["speed"] == 2.0

    @pytest.mark.asyncio
    async def test_set_playback_speed_too_low(self, media_methods):
        """Test set_playback_speed raises ValueError for speed < 0.5"""
        with pytest.raises(ValueError, match="Speed must be between 0.5 and 2.0"):
            await media_methods.set_playback_speed(channel_id=123, speed=0.4)

    @pytest.mark.asyncio
    async def test_set_playback_speed_too_high(self, media_methods):
        """Test set_playback_speed raises ValueError for speed > 2.0"""
        with pytest.raises(ValueError, match="Speed must be between 0.5 and 2.0"):
            await media_methods.set_playback_speed(channel_id=123, speed=2.1)

    @pytest.mark.asyncio
    async def test_set_playback_speed_negative(self, media_methods):
        """Test set_playback_speed raises ValueError for negative speed"""
        with pytest.raises(ValueError, match="Speed must be between 0.5 and 2.0"):
            await media_methods.set_playback_speed(channel_id=123, speed=-1.0)

    @pytest.mark.asyncio
    async def test_set_playback_speed_invalid_type(self, media_methods):
        """Test set_playback_speed raises ValueError for non-numeric speed"""
        with pytest.raises(ValueError, match="speed must be numeric"):
            await media_methods.set_playback_speed(channel_id=123, speed="fast")

    @pytest.mark.asyncio
    async def test_set_pitch_valid_positive(self, media_methods):
        """Test set_pitch with valid positive semitones"""
        result = await media_methods.set_pitch(channel_id=123, semitones=6)
        assert result["pitch_semitones"] == 6

    @pytest.mark.asyncio
    async def test_set_pitch_valid_negative(self, media_methods):
        """Test set_pitch with valid negative semitones"""
        result = await media_methods.set_pitch(channel_id=123, semitones=-6)
        assert result["pitch_semitones"] == -6

    @pytest.mark.asyncio
    async def test_set_pitch_minimum_boundary(self, media_methods):
        """Test set_pitch at minimum boundary (-12)"""
        result = await media_methods.set_pitch(channel_id=123, semitones=-12)
        assert result["pitch_semitones"] == -12

    @pytest.mark.asyncio
    async def test_set_pitch_maximum_boundary(self, media_methods):
        """Test set_pitch at maximum boundary (12)"""
        result = await media_methods.set_pitch(channel_id=123, semitones=12)
        assert result["pitch_semitones"] == 12

    @pytest.mark.asyncio
    async def test_set_pitch_too_low(self, media_methods):
        """Test set_pitch raises ValueError for semitones < -12"""
        with pytest.raises(ValueError, match="Pitch must be between -12 and \\+12"):
            await media_methods.set_pitch(channel_id=123, semitones=-13)

    @pytest.mark.asyncio
    async def test_set_pitch_too_high(self, media_methods):
        """Test set_pitch raises ValueError for semitones > 12"""
        with pytest.raises(ValueError, match="Pitch must be between -12 and \\+12"):
            await media_methods.set_pitch(channel_id=123, semitones=13)

    @pytest.mark.asyncio
    async def test_set_pitch_non_integer(self, media_methods):
        """Test set_pitch raises ValueError for non-integer semitones"""
        with pytest.raises(ValueError, match="semitones must be integer"):
            await media_methods.set_pitch(channel_id=123, semitones=6.5)

    @pytest.mark.asyncio
    async def test_set_pitch_invalid_type(self, media_methods):
        """Test set_pitch raises ValueError for non-numeric semitones"""
        with pytest.raises(ValueError, match="semitones must be integer"):
            await media_methods.set_pitch(channel_id=123, semitones="high")

    @pytest.mark.asyncio
    async def test_set_equalizer_preset_valid(self, media_methods):
        """Test set_equalizer_preset with valid preset"""
        result = await media_methods.set_equalizer_preset(channel_id=123, preset_name="rock")
        assert result["success"] is True
        assert result["preset"] == "rock"
        assert "display_name" in result
        assert "bands" in result

    @pytest.mark.asyncio
    async def test_set_equalizer_preset_invalid_type(self, media_methods):
        """Test set_equalizer_preset raises ValueError for non-string preset"""
        with pytest.raises(ValueError, match="preset_name must be a string"):
            await media_methods.set_equalizer_preset(channel_id=123, preset_name=123)

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_valid(self, media_methods):
        """Test set_equalizer_custom with valid bands"""
        bands = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        result = await media_methods.set_equalizer_custom(channel_id=123, bands=bands)
        assert result["success"] is True
        assert result["preset"] == "custom"
        assert result["bands"] == bands

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_invalid_length(self, media_methods):
        """Test set_equalizer_custom raises ValueError for wrong number of bands"""
        with pytest.raises(ValueError, match="bands must contain exactly 10 values"):
            await media_methods.set_equalizer_custom(channel_id=123, bands=[1, 2, 3])

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_invalid_type(self, media_methods):
        """Test set_equalizer_custom raises ValueError for non-list bands"""
        with pytest.raises(ValueError, match="bands must be a list"):
            await media_methods.set_equalizer_custom(channel_id=123, bands="not-a-list")

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_band_out_of_range(self, media_methods):
        """Test set_equalizer_custom raises ValueError for band value out of range"""
        with pytest.raises(ValueError, match="Band .* out of range"):
            await media_methods.set_equalizer_custom(channel_id=123, bands=[0]*9 + [100])

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_non_numeric_band(self, media_methods):
        """Test set_equalizer_custom raises ValueError for non-numeric band value"""
        with pytest.raises(ValueError, match="Band .* must be numeric"):
            await media_methods.set_equalizer_custom(channel_id=123, bands=[0]*9 + ["invalid"])

    @pytest.mark.asyncio
    async def test_get_stream_status(self, media_methods):
        """Test get_stream_status returns current status"""
        result = await media_methods.get_stream_status(channel_id=123)
        assert "speed" in result
        assert "pitch_correction" in result
        assert "equalizer_preset" in result
        assert "language" in result
        assert "auto_play" in result

    @pytest.mark.asyncio
    async def test_media_methods_requires_user_id(self, db_session):
        """Test that MediaStreamingMethods raises ValueError without user_id"""
        mock_service = Mock(spec=PlaybackService)
        methods = MediaStreamingMethods(mock_service, user_id=None)

        with pytest.raises(ValueError, match="user_id is required"):
            await methods.set_playback_speed(channel_id=123, speed=1.5)

    @pytest.mark.asyncio
    async def test_set_playback_speed_invalid_channel_id(self, media_methods):
        """Test set_playback_speed raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await media_methods.set_playback_speed(channel_id=0, speed=1.5)

    @pytest.mark.asyncio
    async def test_set_pitch_invalid_channel_id(self, media_methods):
        """Test set_pitch raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await media_methods.set_pitch(channel_id=-5, semitones=6)

    @pytest.mark.asyncio
    async def test_set_equalizer_preset_invalid_channel_id(self, media_methods):
        """Test set_equalizer_preset raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await media_methods.set_equalizer_preset(channel_id=0, preset_name="rock")

    @pytest.mark.asyncio
    async def test_set_equalizer_custom_invalid_channel_id(self, media_methods):
        """Test set_equalizer_custom raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await media_methods.set_equalizer_custom(channel_id=-1, bands=[0]*10)

    @pytest.mark.asyncio
    async def test_get_stream_status_invalid_channel_id(self, media_methods):
        """Test get_stream_status raises ValueError for invalid channel_id"""
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            await media_methods.get_stream_status(channel_id=0)
