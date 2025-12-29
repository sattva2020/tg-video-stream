"""
Tests for src/services/playback_service.py.

Coverage target: 70%+

Test categories:
1. Initialization and channel scoping
2. Settings management (get_or_create, get)
3. Speed control (set, reset, validation)
4. Pitch control (set, validation)
5. Position control (seek, seek_to, rewind)
6. Equalizer management (get state, set preset, set custom)
7. Edge cases and validation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from src.services.playback_service import PlaybackService
from src.models import PlaybackSettings


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def playback_service(mock_db_session):
    """PlaybackService instance with mocked DB."""
    return PlaybackService(mock_db_session)


@pytest.fixture
def sample_settings():
    """Sample PlaybackSettings object."""
    return PlaybackSettings(
        id=1,
        user_id=100,
        channel_id=123,
        speed=1.0,
        pitch_correction=False,
        equalizer_preset="flat",
        equalizer_custom=None,
        language="en",
        auto_play=True,
        shuffle=False,
        repeat_mode="none"
    )


# ============================================================================
# Test Initialization and Channel Scoping
# ============================================================================

class TestPlaybackServiceInit:
    """Test PlaybackService initialization."""
    
    def test_init_sets_db_session(self, mock_db_session):
        """Test __init__() sets database session."""
        service = PlaybackService(mock_db_session)
        
        assert service.db == mock_db_session
        assert service.logger is not None
    
    def test_init_sets_logger(self, playback_service):
        """Test __init__() sets logger with correct name."""
        assert playback_service.logger.name == "src.services.playback_service"
    
    def test_constants_defined(self, playback_service):
        """Test class constants are properly defined."""
        assert playback_service.MIN_SPEED == 0.5
        assert playback_service.MAX_SPEED == 2.0
        assert playback_service.DEFAULT_SPEED == 1.0
        assert playback_service.MIN_PITCH == -12
        assert playback_service.MAX_PITCH == 12
        assert playback_service.DEFAULT_PITCH == 0


class TestPlaybackServiceChannelScope:
    """Test channel scoping logic."""
    
    def test_channel_scope_with_channel_id(self, playback_service):
        """Test _channel_scope() returns channel_id when provided."""
        result = playback_service._channel_scope(channel_id=123, fallback=999)
        
        assert result == 123
    
    def test_channel_scope_with_none(self, playback_service):
        """Test _channel_scope() returns fallback when channel_id is None."""
        result = playback_service._channel_scope(channel_id=None, fallback=456)
        
        assert result == 456
    
    def test_channel_scope_converts_to_int(self, playback_service):
        """Test _channel_scope() converts to int."""
        result = playback_service._channel_scope(channel_id="789", fallback=100)
        
        assert result == 789
        assert isinstance(result, int)


# ============================================================================
# Test Settings Management
# ============================================================================

class TestPlaybackServiceSettings:
    """Test settings retrieval and creation."""
    
    def test_get_or_create_settings_existing(self, playback_service, mock_db_session, sample_settings):
        """Test get_or_create_settings() returns existing settings."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = sample_settings
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = playback_service.get_or_create_settings(user_id=100, channel_id=123)
        
        assert result == sample_settings
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
    
    def test_get_or_create_settings_creates_new(self, playback_service, mock_db_session):
        """Test get_or_create_settings() creates new settings when not found."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None  # Not found
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = playback_service.get_or_create_settings(user_id=200, channel_id=456)
        
        assert isinstance(result, PlaybackSettings)
        assert result.user_id == 200
        assert result.channel_id == 456
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_get_or_create_settings_uses_fallback_channel(self, playback_service, mock_db_session):
        """Test get_or_create_settings() uses user_id as fallback when channel_id is None."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = playback_service.get_or_create_settings(user_id=300, channel_id=None)
        
        assert result.user_id == 300
        assert result.channel_id == 300  # Fallback to user_id
    
    def test_get_settings_returns_dict(self, playback_service, sample_settings):
        """Test get_settings() returns dict with all settings."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.get_settings(user_id=100, channel_id=123)
            
            assert isinstance(result, dict)
            assert result["user_id"] == 100
            assert result["channel_id"] == 123
            assert result["speed"] == 1.0
            assert result["pitch_correction"] is False
            assert result["equalizer_preset"] == "flat"
            assert result["language"] == "en"
            assert result["auto_play"] is True
            assert result["shuffle"] is False
            assert result["repeat_mode"] == "none"


# ============================================================================
# Test Speed Control
# ============================================================================

class TestPlaybackServiceSpeed:
    """Test speed control functionality."""
    
    def test_set_speed_valid_range(self, playback_service, mock_db_session, sample_settings):
        """Test set_speed() with valid speed values."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_speed(user_id=100, speed=1.5, channel_id=123)
            
            assert sample_settings.speed == 1.5
            assert result["speed"] == 1.5
            assert result["user_id"] == 100
            assert result["channel_id"] == 123
            assert "message" in result
            mock_db_session.commit.assert_called_once()
    
    def test_set_speed_minimum(self, playback_service, sample_settings):
        """Test set_speed() with minimum valid speed (0.5x)."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_speed(user_id=100, speed=0.5)
            
            assert sample_settings.speed == 0.5
            assert result["speed"] == 0.5
    
    def test_set_speed_maximum(self, playback_service, sample_settings):
        """Test set_speed() with maximum valid speed (2.0x)."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_speed(user_id=100, speed=2.0)
            
            assert sample_settings.speed == 2.0
            assert result["speed"] == 2.0
    
    def test_set_speed_below_minimum_raises_error(self, playback_service):
        """Test set_speed() raises ValueError when speed is too low."""
        with pytest.raises(ValueError, match="Speed must be between 0.5 and 2.0"):
            playback_service.set_speed(user_id=100, speed=0.3)
    
    def test_set_speed_above_maximum_raises_error(self, playback_service):
        """Test set_speed() raises ValueError when speed is too high."""
        with pytest.raises(ValueError, match="Speed must be between 0.5 and 2.0"):
            playback_service.set_speed(user_id=100, speed=3.0)
    
    def test_reset_speed_sets_default(self, playback_service, mock_db_session, sample_settings):
        """Test reset_speed() sets speed to 1.0x."""
        sample_settings.speed = 1.8  # Start with non-default
        
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.reset_speed(user_id=100, channel_id=123)
            
            assert sample_settings.speed == 1.0
            assert result["speed"] == 1.0
            assert result["message"] == "Speed reset to 1.0x"
            mock_db_session.commit.assert_called_once()
    
    def test_set_speed_logs_change(self, playback_service, sample_settings):
        """Test set_speed() logs the speed change."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            with patch.object(playback_service.logger, 'info') as mock_log:
                playback_service.set_speed(user_id=100, speed=1.25, channel_id=123)
                
                mock_log.assert_called()
                log_message = mock_log.call_args[0][0]
                assert "Speed changed" in log_message


# ============================================================================
# Test Pitch Control
# ============================================================================

class TestPlaybackServicePitch:
    """Test pitch control functionality."""
    
    def test_set_pitch_valid_range(self, playback_service, mock_db_session, sample_settings):
        """Test set_pitch() with valid semitone values."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_pitch(user_id=100, semitones=5, channel_id=123)
            
            assert sample_settings.pitch_correction is True
            assert result["pitch_semitones"] == 5
            assert result["pitch_correction"] is True
            assert result["user_id"] == 100
            mock_db_session.commit.assert_called_once()
    
    def test_set_pitch_negative(self, playback_service, sample_settings):
        """Test set_pitch() with negative semitones."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_pitch(user_id=100, semitones=-7)
            
            assert result["pitch_semitones"] == -7
            assert "Pitch shifted -7 semitones" in result["message"]
    
    def test_set_pitch_minimum(self, playback_service, sample_settings):
        """Test set_pitch() with minimum valid pitch (-12 semitones)."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_pitch(user_id=100, semitones=-12)
            
            assert result["pitch_semitones"] == -12
    
    def test_set_pitch_maximum(self, playback_service, sample_settings):
        """Test set_pitch() with maximum valid pitch (+12 semitones)."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_pitch(user_id=100, semitones=12)
            
            assert result["pitch_semitones"] == 12
    
    def test_set_pitch_below_minimum_raises_error(self, playback_service):
        """Test set_pitch() raises ValueError when pitch is too low."""
        with pytest.raises(ValueError, match="Pitch must be between -12 and 12"):
            playback_service.set_pitch(user_id=100, semitones=-15)
    
    def test_set_pitch_above_maximum_raises_error(self, playback_service):
        """Test set_pitch() raises ValueError when pitch is too high."""
        with pytest.raises(ValueError, match="Pitch must be between -12 and 12"):
            playback_service.set_pitch(user_id=100, semitones=20)


# ============================================================================
# Test Position Control
# ============================================================================

class TestPlaybackServicePosition:
    """Test position control (seek, rewind)."""
    
    def test_seek_valid_position(self, playback_service):
        """Test seek() with valid position in milliseconds."""
        result = playback_service.seek(user_id=100, position_ms=45000, channel_id=123)
        
        assert result["position_ms"] == 45000
        assert result["user_id"] == 100
        assert result["channel_id"] == 123
        assert "45000ms" in result["message"]
    
    def test_seek_zero_position(self, playback_service):
        """Test seek() to position 0 (beginning)."""
        result = playback_service.seek(user_id=100, position_ms=0)
        
        assert result["position_ms"] == 0
    
    def test_seek_negative_position_raises_error(self, playback_service):
        """Test seek() raises ValueError for negative position."""
        with pytest.raises(ValueError, match="Position cannot be negative"):
            playback_service.seek(user_id=100, position_ms=-1000)
    
    def test_seek_to_valid_seconds(self, playback_service):
        """Test seek_to() with valid position in seconds."""
        result = playback_service.seek_to(user_id=100, position_seconds=60, channel_id=123)
        
        assert result == 60
    
    def test_seek_to_zero(self, playback_service):
        """Test seek_to() to position 0."""
        result = playback_service.seek_to(user_id=100, position_seconds=0)
        
        assert result == 0
    
    def test_seek_to_negative_raises_error(self, playback_service):
        """Test seek_to() raises ValueError for negative position."""
        with pytest.raises(ValueError, match="Position cannot be negative"):
            playback_service.seek_to(user_id=100, position_seconds=-10)
    
    def test_rewind_valid_duration(self, playback_service):
        """Test rewind() with valid duration."""
        result = playback_service.rewind(user_id=100, seconds=15, channel_id=123)
        
        # With current_position=0, rewind should return 0 (can't go negative)
        assert result == 0
    
    def test_rewind_zero_raises_error(self, playback_service):
        """Test rewind() raises ValueError for zero duration."""
        with pytest.raises(ValueError, match="Rewind duration must be positive"):
            playback_service.rewind(user_id=100, seconds=0)
    
    def test_rewind_negative_raises_error(self, playback_service):
        """Test rewind() raises ValueError for negative duration."""
        with pytest.raises(ValueError, match="Rewind duration must be positive"):
            playback_service.rewind(user_id=100, seconds=-5)
    
    def test_get_position_returns_placeholder(self, playback_service):
        """Test get_position() returns placeholder data (TODO implementation)."""
        result = playback_service.get_position(user_id=100, channel_id=123)
        
        assert isinstance(result, dict)
        assert result["channel_id"] == 123
        assert result["current_position_seconds"] == 0
        assert result["total_duration_seconds"] == 0
        assert result["is_playing"] is False


# ============================================================================
# Test Equalizer Management
# ============================================================================

class TestPlaybackServiceEqualizer:
    """Test equalizer functionality."""
    
    def test_get_equalizer_state(self, playback_service, sample_settings):
        """Test get_equalizer_state() retrieves from playback controller."""
        mock_controller = MagicMock()
        mock_controller.get_equalizer_state.return_value = {
            "preset": "rock",
            "bands": [0, 2, 4, 6, 4, 2, 0, -2, -4, -2]
        }
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                result = playback_service.get_equalizer_state(user_id=100, channel_id=123)
                
                assert result["user_id"] == 100
                assert result["channel_id"] == 123
                assert result["preset"] == "rock"
                assert len(result["bands"]) == 10
                mock_controller.get_equalizer_state.assert_called_once_with("123")
    
    def test_set_equalizer_preset_valid(self, playback_service, mock_db_session, sample_settings):
        """Test set_equalizer_preset() with valid preset name."""
        mock_controller = MagicMock()
        mock_controller.set_equalizer_preset.return_value = True
        
        mock_preset = MagicMock()
        mock_preset.display_name = "Rock"
        mock_preset.description = "Rock music enhancement"
        mock_preset.bands = [0, 2, 4, 6, 4, 2, 0, -2, -4, -2]
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch('src.config.equalizer_presets.EQUALIZER_PRESETS', {"rock": mock_preset}):
                with patch('src.config.equalizer_presets.get_preset', return_value=mock_preset):
                    with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                        result = playback_service.set_equalizer_preset(
                            user_id=100, preset_name="rock", channel_id=123
                        )
                        
                        assert result["success"] is True
                        assert result["preset"] == "rock"
                        assert result["display_name"] == "Rock"
                        assert sample_settings.equalizer_preset == "rock"
                        assert sample_settings.equalizer_custom is None
                        mock_db_session.commit.assert_called_once()
    
    def test_set_equalizer_preset_invalid_raises_error(self, playback_service):
        """Test set_equalizer_preset() raises ValueError for unknown preset."""
        with patch('src.config.equalizer_presets.EQUALIZER_PRESETS', {"flat": {}, "rock": {}}):
            with pytest.raises(ValueError, match="Unknown preset"):
                playback_service.set_equalizer_preset(user_id=100, preset_name="invalid")
    
    def test_set_equalizer_preset_failure_raises_error(self, playback_service, sample_settings):
        """Test set_equalizer_preset() raises RuntimeError when controller fails."""
        mock_controller = MagicMock()
        mock_controller.set_equalizer_preset.return_value = False  # Failure
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch('src.config.equalizer_presets.EQUALIZER_PRESETS', {"rock": {}}):
                with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                    with pytest.raises(RuntimeError, match="Failed to apply equalizer preset"):
                        playback_service.set_equalizer_preset(user_id=100, preset_name="rock")
    
    def test_set_equalizer_custom_valid(self, playback_service, mock_db_session, sample_settings):
        """Test set_equalizer_custom() with valid band values."""
        custom_bands = [1.0, 2.0, 3.0, 2.5, 1.5, 0.5, -1.0, -2.0, -1.5, 0.0]
        
        mock_controller = MagicMock()
        mock_controller.set_equalizer_custom.return_value = True
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch('src.config.equalizer_presets.validate_custom_bands'):
                with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                    result = playback_service.set_equalizer_custom(
                        user_id=100, bands=custom_bands, channel_id=123
                    )
                    
                    assert result["success"] is True
                    assert result["preset"] == "custom"
                    assert result["bands"] == custom_bands
                    assert sample_settings.equalizer_preset == "custom"
                    assert sample_settings.equalizer_custom == custom_bands
                    mock_db_session.commit.assert_called_once()
    
    def test_set_equalizer_custom_invalid_raises_error(self, playback_service, sample_settings):
        """Test set_equalizer_custom() raises ValueError for invalid bands."""
        invalid_bands = [0, 0, 0]  # Wrong number of bands
        
        with patch('src.config.equalizer_presets.validate_custom_bands', side_effect=ValueError("Invalid bands")):
            with pytest.raises(ValueError, match="Invalid bands"):
                playback_service.set_equalizer_custom(user_id=100, bands=invalid_bands)
    
    def test_set_equalizer_custom_failure_raises_error(self, playback_service, sample_settings):
        """Test set_equalizer_custom() raises RuntimeError when controller fails."""
        custom_bands = [0.0] * 10
        
        mock_controller = MagicMock()
        mock_controller.set_equalizer_custom.return_value = False  # Failure
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch('src.config.equalizer_presets.validate_custom_bands'):
                with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                    with pytest.raises(RuntimeError, match="Failed to apply custom equalizer"):
                        playback_service.set_equalizer_custom(user_id=100, bands=custom_bands)


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestPlaybackServiceEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_set_speed_with_none_channel_uses_fallback(self, playback_service, sample_settings):
        """Test set_speed() with channel_id=None uses user_id as fallback."""
        sample_settings.channel_id = 200  # user_id will be 200
        
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_speed(user_id=200, speed=1.2, channel_id=None)
            
            assert result["channel_id"] == 200  # Fallback to user_id
    
    def test_set_pitch_with_zero_semitones(self, playback_service, sample_settings):
        """Test set_pitch() with zero semitones (no pitch shift)."""
        with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
            result = playback_service.set_pitch(user_id=100, semitones=0)
            
            assert result["pitch_semitones"] == 0
            assert "+0 semitones" in result["message"]
    
    def test_seek_large_position(self, playback_service):
        """Test seek() with very large position value."""
        result = playback_service.seek(user_id=100, position_ms=3600000)  # 1 hour
        
        assert result["position_ms"] == 3600000
    
    def test_multiple_settings_for_different_channels(self, playback_service, mock_db_session):
        """Test that different channels have isolated settings."""
        settings1 = PlaybackSettings(user_id=100, channel_id=123, speed=1.0)
        settings2 = PlaybackSettings(user_id=100, channel_id=456, speed=1.5)
        
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.side_effect = [settings1, settings2]
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result1 = playback_service.get_settings(user_id=100, channel_id=123)
        result2 = playback_service.get_settings(user_id=100, channel_id=456)
        
        assert result1["channel_id"] == 123
        assert result2["channel_id"] == 456
    
    def test_get_equalizer_state_updates_db_when_different(self, playback_service, mock_db_session, sample_settings):
        """Test get_equalizer_state() updates DB when live state differs."""
        sample_settings.equalizer_preset = "flat"
        
        mock_controller = MagicMock()
        mock_controller.get_equalizer_state.return_value = {
            "preset": "rock",  # Different from DB
            "bands": [0] * 10
        }
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                result = playback_service.get_equalizer_state(user_id=100, channel_id=123)
                
                assert sample_settings.equalizer_preset == "rock"  # Updated
                mock_db_session.commit.assert_called_once()
    
    def test_get_equalizer_state_updates_custom_bands(self, playback_service, mock_db_session, sample_settings):
        """Test get_equalizer_state() saves custom bands when preset is 'custom'."""
        sample_settings.equalizer_preset = "flat"
        custom_bands = [1.0] * 10
        
        mock_controller = MagicMock()
        mock_controller.get_equalizer_state.return_value = {
            "preset": "custom",
            "bands": custom_bands
        }
        
        with patch('streamer.playback_control.get_playback_controller', return_value=mock_controller):
            with patch.object(playback_service, 'get_or_create_settings', return_value=sample_settings):
                result = playback_service.get_equalizer_state(user_id=100, channel_id=123)
                
                assert sample_settings.equalizer_preset == "custom"
                assert sample_settings.equalizer_custom == custom_bands
                mock_db_session.commit.assert_called_once()
