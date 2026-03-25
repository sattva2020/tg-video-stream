"""
Unit tests for StreamControl and StreamState.

This test module covers:
- StreamState initialization and validation
- StreamControl initialization
- Seek operations (absolute position, rewind, forward)
- Volume control (0-100 and 0.0-1.0 ranges)
- Playback speed control
- Stream state management (get, update, clean)
- Playback state tracking (playing, paused)
- Duration management
- State query methods
"""

import pytest
from datetime import datetime
from ayugram.stream import StreamControl, StreamState, get_stream_control, reset_stream_control
from ayugram.exceptions import AyuGramError


# ============================================================================
# Test StreamState Initialization and Validation
# ============================================================================


class TestStreamStateInit:
    """Test StreamState dataclass initialization and validation."""

    def test_default_values(self):
        """Test StreamState initializes with default values."""
        state = StreamState()

        assert state.position_ms == 0
        assert state.duration_ms == 0
        assert state.is_playing == False
        assert state.is_paused == False
        assert state.volume == 1.0
        assert state.speed == 1.0
        assert isinstance(state.updated_at, datetime)

    def test_custom_values(self):
        """Test StreamState with custom values."""
        now = datetime.now()
        state = StreamState(
            position_ms=60000,
            duration_ms=180000,
            is_playing=True,
            is_paused=False,
            volume=0.5,
            speed=1.5,
            updated_at=now
        )

        assert state.position_ms == 60000
        assert state.duration_ms == 180000
        assert state.is_playing == True
        assert state.is_paused == False
        assert state.volume == 0.5
        assert state.speed == 1.5
        assert state.updated_at == now

    def test_volume_validation_too_high(self):
        """Test StreamState raises ValueError for volume > 1.0."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(volume=1.5)

        assert "Volume must be between 0.0 and 1.0" in str(exc_info.value)
        assert "got 1.5" in str(exc_info.value)

    def test_volume_validation_too_low(self):
        """Test StreamState raises ValueError for volume < 0.0."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(volume=-0.1)

        assert "Volume must be between 0.0 and 1.0" in str(exc_info.value)

    def test_volume_validation_boundary_high(self):
        """Test StreamState accepts volume = 1.0."""
        state = StreamState(volume=1.0)
        assert state.volume == 1.0

    def test_volume_validation_boundary_low(self):
        """Test StreamState accepts volume = 0.0."""
        state = StreamState(volume=0.0)
        assert state.volume == 0.0

    def test_speed_validation_too_high(self):
        """Test StreamState raises ValueError for speed > 2.0."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(speed=2.5)

        assert "Speed must be between 0.5 and 2.0" in str(exc_info.value)
        assert "got 2.5" in str(exc_info.value)

    def test_speed_validation_too_low(self):
        """Test StreamState raises ValueError for speed < 0.5."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(speed=0.3)

        assert "Speed must be between 0.5 and 2.0" in str(exc_info.value)

    def test_speed_validation_boundary_high(self):
        """Test StreamState accepts speed = 2.0."""
        state = StreamState(speed=2.0)
        assert state.speed == 2.0

    def test_speed_validation_boundary_low(self):
        """Test StreamState accepts speed = 0.5."""
        state = StreamState(speed=0.5)
        assert state.speed == 0.5

    def test_position_validation_negative(self):
        """Test StreamState raises ValueError for negative position."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(position_ms=-1000)

        assert "Position cannot be negative" in str(exc_info.value)

    def test_duration_validation_negative(self):
        """Test StreamState raises ValueError for negative duration."""
        with pytest.raises(ValueError) as exc_info:
            StreamState(duration_ms=-1000)

        assert "Duration cannot be negative" in str(exc_info.value)


# ============================================================================
# Test StreamControl Initialization
# ============================================================================


class TestStreamControlInit:
    """Test StreamControl initialization and default values."""

    def test_init(self):
        """Test StreamControl initializes with empty states."""
        control = StreamControl()

        assert control.states == {}
        assert control.logger is not None

    def test_init_creates_logger(self):
        """Test StreamControl creates a logger instance."""
        control = StreamControl()

        assert control.logger.name == "ayugram.stream"


# ============================================================================
# Test Seek Operations
# ============================================================================


class TestSeekOperations:
    """Test seek, rewind, and forward operations."""

    def test_seek_stream_from_zero(self, test_chat_id):
        """Test seeking from position 0."""
        control = StreamControl()
        result = control.seek_stream(test_chat_id, 30)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 30000
        assert state.updated_at is not None

    def test_seek_stream_to_new_position(self, test_chat_id):
        """Test seeking from existing position to new position."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 60)

        result = control.seek_stream(test_chat_id, 120)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 120000

    def test_seek_stream_negative_position(self, test_chat_id):
        """Test seek_stream raises ValueError for negative position."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.seek_stream(test_chat_id, -10)

        assert "Position cannot be negative" in str(exc_info.value)
        assert "got -10s" in str(exc_info.value)

    def test_seek_stream_zero_position(self, test_chat_id):
        """Test seeking to position 0 is allowed."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 60)

        result = control.seek_stream(test_chat_id, 0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 0

    def test_rewind_stream_from_zero(self, test_chat_id):
        """Test rewind from position 0 stays at 0."""
        control = StreamControl()
        result = control.rewind_stream(test_chat_id, 10)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 0

    def test_rewind_stream_from_position(self, test_chat_id):
        """Test rewind from position goes back by N seconds."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 60)

        result = control.rewind_stream(test_chat_id, 10)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 50000  # 60s - 10s = 50s

    def test_rewind_stream_negative_seconds(self, test_chat_id):
        """Test rewind_stream raises ValueError for negative seconds."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.rewind_stream(test_chat_id, -5)

        assert "Rewind duration must be positive" in str(exc_info.value)
        assert "got -5s" in str(exc_info.value)

    def test_rewind_stream_zero_seconds(self, test_chat_id):
        """Test rewind_stream raises ValueError for zero seconds."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.rewind_stream(test_chat_id, 0)

        assert "Rewind duration must be positive" in str(exc_info.value)
        assert "got 0s" in str(exc_info.value)

    def test_forward_stream_without_duration(self, test_chat_id):
        """Test forward without duration cap."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 60)

        result = control.forward_stream(test_chat_id, 30)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 90000  # 60s + 30s = 90s

    def test_forward_stream_with_duration_cap(self, test_chat_id):
        """Test forward caps at duration."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 60)
        control.update_duration(test_chat_id, 120000)  # 2 minutes

        result = control.forward_stream(test_chat_id, 90)  # Try to go to 150s

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.position_ms == 120000  # Capped at 120s (2 min)

    def test_forward_stream_negative_seconds(self, test_chat_id):
        """Test forward_stream raises ValueError for negative seconds."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.forward_stream(test_chat_id, -5)

        assert "Forward duration must be positive" in str(exc_info.value)
        assert "got -5s" in str(exc_info.value)

    def test_forward_stream_zero_seconds(self, test_chat_id):
        """Test forward_stream raises ValueError for zero seconds."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.forward_stream(test_chat_id, 0)

        assert "Forward duration must be positive" in str(exc_info.value)
        assert "got 0s" in str(exc_info.value)


# ============================================================================
# Test Volume Control
# ============================================================================


class TestVolumeControl:
    """Test volume control operations."""

    def test_set_volume_percentage_50(self, test_chat_id):
        """Test set_volume with 50%."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 50)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.5

    def test_set_volume_percentage_0(self, test_chat_id):
        """Test set_volume with 0% (mute)."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.0

    def test_set_volume_percentage_100(self, test_chat_id):
        """Test set_volume with 100% (max)."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 100)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 1.0

    def test_set_volume_normalized_0_5(self, test_chat_id):
        """Test set_volume with normalized value 0.5."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 0.5)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.5

    def test_set_volume_normalized_0_0(self, test_chat_id):
        """Test set_volume with normalized value 0.0."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 0.0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.0

    def test_set_volume_normalized_1_0(self, test_chat_id):
        """Test set_volume with normalized value 1.0."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 1.0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 1.0

    def test_set_volume_above_100(self, test_chat_id):
        """Test set_volume raises ValueError for volume > 100."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.set_volume(test_chat_id, 150)

        assert "Volume must be between 0 and 100" in str(exc_info.value)
        assert "got 150" in str(exc_info.value)

    def test_set_volume_negative_percentage(self, test_chat_id):
        """Test set_volume raises ValueError for negative percentage."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.set_volume(test_chat_id, -10)

        assert "Volume must be between 0.0 and 1.0" in str(exc_info.value)

    def test_set_volume_negative_normalized(self, test_chat_id):
        """Test set_volume raises ValueError for negative normalized value."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.set_volume(test_chat_id, -0.1)

        assert "Volume must be between" in str(exc_info.value)

    def test_set_volume_ambiguous_value(self, test_chat_id):
        """Test set_volume raises ValueError for ambiguous values (1.0-5.0)."""
        control = StreamControl()

        # Test value 3.0 (ambiguous - could be 3% or 0.03 normalized)
        with pytest.raises(ValueError) as exc_info:
            control.set_volume(test_chat_id, 3.0)

        assert "Ambiguous volume value" in str(exc_info.value)

    def test_set_volume_updates_existing(self, test_chat_id):
        """Test set_volume updates existing volume."""
        control = StreamControl()
        control.set_volume(test_chat_id, 50)

        result = control.set_volume(test_chat_id, 75)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.75

    def test_get_volume_default(self, test_chat_id):
        """Test get_volume returns default when no state exists."""
        control = StreamControl()

        volume = control.get_volume(test_chat_id)

        assert volume == 1.0

    def test_get_volume_existing(self, test_chat_id):
        """Test get_volume returns existing volume."""
        control = StreamControl()
        control.set_volume(test_chat_id, 60)

        volume = control.get_volume(test_chat_id)

        assert volume == 0.6


# ============================================================================
# Test Speed Control
# ============================================================================


class TestSpeedControl:
    """Test playback speed control operations."""

    def test_set_speed_1_0(self, test_chat_id):
        """Test set_speed with normal speed (1.0)."""
        control = StreamControl()
        result = control.set_speed(test_chat_id, 1.0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.speed == 1.0

    def test_set_speed_1_5(self, test_chat_id):
        """Test set_speed with 1.5x speed."""
        control = StreamControl()
        result = control.set_speed(test_chat_id, 1.5)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.speed == 1.5

    def test_set_speed_0_5(self, test_chat_id):
        """Test set_speed with minimum speed (0.5)."""
        control = StreamControl()
        result = control.set_speed(test_chat_id, 0.5)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.speed == 0.5

    def test_set_speed_2_0(self, test_chat_id):
        """Test set_speed with maximum speed (2.0)."""
        control = StreamControl()
        result = control.set_speed(test_chat_id, 2.0)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.speed == 2.0

    def test_set_speed_too_low(self, test_chat_id):
        """Test set_speed raises ValueError for speed < 0.5."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.set_speed(test_chat_id, 0.3)

        assert "Speed must be between 0.5 and 2.0" in str(exc_info.value)
        assert "got 0.3" in str(exc_info.value)

    def test_set_speed_too_high(self, test_chat_id):
        """Test set_speed raises ValueError for speed > 2.0."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.set_speed(test_chat_id, 2.5)

        assert "Speed must be between 0.5 and 2.0" in str(exc_info.value)
        assert "got 2.5" in str(exc_info.value)

    def test_set_speed_updates_existing(self, test_chat_id):
        """Test set_speed updates existing speed."""
        control = StreamControl()
        control.set_speed(test_chat_id, 1.0)

        result = control.set_speed(test_chat_id, 1.75)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.speed == 1.75


# ============================================================================
# Test State Management
# ============================================================================


class TestStateManagement:
    """Test stream state management operations."""

    def test_get_state_no_existing(self, test_chat_id):
        """Test get_state returns None when no state exists."""
        control = StreamControl()

        state = control.get_state(test_chat_id)

        assert state is None

    def test_get_state_existing(self, test_chat_id):
        """Test get_state returns existing state."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 30)

        state = control.get_state(test_chat_id)

        assert state is not None
        assert state.position_ms == 30000

    def test_get_position_no_state(self, test_chat_id):
        """Test get_position returns 0 when no state exists."""
        control = StreamControl()

        position = control.get_position(test_chat_id)

        assert position == 0

    def test_get_position_existing(self, test_chat_id):
        """Test get_position returns current position in seconds."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 125)

        position = control.get_position(test_chat_id)

        assert position == 125

    def test_update_duration(self, test_chat_id):
        """Test update_duration sets duration."""
        control = StreamControl()
        result = control.update_duration(test_chat_id, 180000)

        assert result is None
        state = control.get_state(test_chat_id)
        assert state.duration_ms == 180000

    def test_update_duration_negative(self, test_chat_id):
        """Test update_duration raises ValueError for negative duration."""
        control = StreamControl()

        with pytest.raises(ValueError) as exc_info:
            control.update_duration(test_chat_id, -1000)

        assert "Duration cannot be negative" in str(exc_info.value)
        assert "got -1000ms" in str(exc_info.value)

    def test_has_state_false(self, test_chat_id):
        """Test has_state returns False when no state exists."""
        control = StreamControl()

        result = control.has_state(test_chat_id)

        assert result == False

    def test_has_state_true(self, test_chat_id):
        """Test has_state returns True when state exists."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 30)

        result = control.has_state(test_chat_id)

        assert result == True

    def test_clean_state_existing(self, test_chat_id):
        """Test clean_state removes existing state."""
        control = StreamControl()
        control.seek_stream(test_chat_id, 30)

        control.clean_state(test_chat_id)

        assert control.get_state(test_chat_id) is None
        assert control.has_state(test_chat_id) == False

    def test_clean_state_non_existing(self, test_chat_id):
        """Test clean_state does nothing when state doesn't exist."""
        control = StreamControl()

        # Should not raise any exception
        control.clean_state(test_chat_id)

        assert control.get_state(test_chat_id) is None

    def test_get_all_states_empty(self):
        """Test get_all_states returns empty dict when no states exist."""
        control = StreamControl()

        states = control.get_all_states()

        assert states == {}
        assert isinstance(states, dict)

    def test_get_all_states_multiple(self, test_chat_ids):
        """Test get_all_states returns all states."""
        control = StreamControl()

        # Create states for multiple chats
        for i, chat_id in enumerate(test_chat_ids):
            control.seek_stream(str(chat_id), i * 10)

        states = control.get_all_states()

        assert len(states) == 3
        assert all(isinstance(k, str) for k in states.keys())
        assert all(isinstance(v, StreamState) for v in states.values())


# ============================================================================
# Test Playback State Tracking
# ============================================================================


class TestPlaybackStateTracking:
    """Test playback state tracking (playing, paused)."""

    def test_mark_playing_true(self, test_chat_id):
        """Test mark_playing sets is_playing=True, is_paused=False."""
        control = StreamControl()
        control.mark_playing(test_chat_id, True)

        state = control.get_state(test_chat_id)
        assert state.is_playing == True
        assert state.is_paused == False

    def test_mark_playing_false(self, test_chat_id):
        """Test mark_playing sets is_playing=False."""
        control = StreamControl()
        control.mark_playing(test_chat_id, True)
        control.mark_playing(test_chat_id, False)

        state = control.get_state(test_chat_id)
        assert state.is_playing == False
        assert state.is_paused == False

    def test_mark_paused_true(self, test_chat_id):
        """Test mark_paused sets is_paused=True, is_playing=False."""
        control = StreamControl()
        control.mark_playing(test_chat_id, True)
        control.mark_paused(test_chat_id, True)

        state = control.get_state(test_chat_id)
        assert state.is_paused == True
        assert state.is_playing == False

    def test_mark_paused_false(self, test_chat_id):
        """Test mark_paused sets is_paused=False (resume)."""
        control = StreamControl()
        control.mark_paused(test_chat_id, True)
        control.mark_paused(test_chat_id, False)

        state = control.get_state(test_chat_id)
        assert state.is_paused == False
        assert state.is_playing == False  # Not automatically set to True

    def test_playing_paused_cycle(self, test_chat_id):
        """Test playing -> paused -> playing cycle."""
        control = StreamControl()

        # Start playing
        control.mark_playing(test_chat_id, True)
        state = control.get_state(test_chat_id)
        assert state.is_playing == True
        assert state.is_paused == False

        # Pause
        control.mark_paused(test_chat_id, True)
        state = control.get_state(test_chat_id)
        assert state.is_playing == False
        assert state.is_paused == True

        # Resume
        control.mark_playing(test_chat_id, True)
        state = control.get_state(test_chat_id)
        assert state.is_playing == True
        assert state.is_paused == False


# ============================================================================
# Test Multiple Chats
# ============================================================================


class TestMultipleChats:
    """Test stream control with multiple chats simultaneously."""

    def test_separate_states_per_chat(self, test_chat_ids):
        """Test each chat has independent state."""
        control = StreamControl()

        # Set different positions for each chat
        control.seek_stream(str(test_chat_ids[0]), 10)
        control.seek_stream(str(test_chat_ids[1]), 20)
        control.seek_stream(str(test_chat_ids[2]), 30)

        # Verify each has correct position
        assert control.get_position(str(test_chat_ids[0])) == 10
        assert control.get_position(str(test_chat_ids[1])) == 20
        assert control.get_position(str(test_chat_ids[2])) == 30

    def test_separate_volumes_per_chat(self, test_chat_ids):
        """Test each chat has independent volume."""
        control = StreamControl()

        control.set_volume(str(test_chat_ids[0]), 25)
        control.set_volume(str(test_chat_ids[1]), 50)
        control.set_volume(str(test_chat_ids[2]), 75)

        assert control.get_volume(str(test_chat_ids[0])) == 0.25
        assert control.get_volume(str(test_chat_ids[1])) == 0.50
        assert control.get_volume(str(test_chat_ids[2])) == 0.75

    def test_clean_one_chat_doesnt_affect_others(self, test_chat_ids):
        """Test cleaning one chat doesn't affect others."""
        control = StreamControl()

        control.seek_stream(str(test_chat_ids[0]), 10)
        control.seek_stream(str(test_chat_ids[1]), 20)
        control.seek_stream(str(test_chat_ids[2]), 30)

        # Clean middle chat
        control.clean_state(str(test_chat_ids[1]))

        assert control.has_state(str(test_chat_ids[0])) == True
        assert control.has_state(str(test_chat_ids[1])) == False
        assert control.has_state(str(test_chat_ids[2])) == True


# ============================================================================
# Test Global Singleton
# ============================================================================


class TestGlobalSingleton:
    """Test global stream control singleton functions."""

    def test_get_stream_control_returns_instance(self):
        """Test get_stream_control returns StreamControl instance."""
        reset_stream_control()  # Start fresh

        control = get_stream_control()

        assert isinstance(control, StreamControl)

    def test_get_stream_control_returns_same_instance(self):
        """Test get_stream_control returns singleton instance."""
        reset_stream_control()  # Start fresh

        control1 = get_stream_control()
        control2 = get_stream_control()

        assert control1 is control2

    def test_reset_stream_control(self):
        """Test reset_stream_control clears singleton."""
        control1 = get_stream_control()
        control1.seek_stream("chat1", 30)

        reset_stream_control()
        control2 = get_stream_control()

        assert control1 is not control2
        assert control2.get_state("chat1") is None


# ============================================================================
# Test State Persistence Across Operations
# ============================================================================


class TestStatePersistence:
    """Test that state persists across operations."""

    def test_state_persists_across_operations(self, test_chat_id):
        """Test state values persist across multiple operations."""
        control = StreamControl()

        # Set initial state
        control.seek_stream(test_chat_id, 60)
        control.set_volume(test_chat_id, 50)
        control.set_speed(test_chat_id, 1.5)
        control.update_duration(test_chat_id, 180000)
        control.mark_playing(test_chat_id, True)

        # Perform more operations
        control.rewind_stream(test_chat_id, 10)
        control.set_volume(test_chat_id, 75)

        # Verify final state
        state = control.get_state(test_chat_id)
        assert state.position_ms == 50000  # 60s - 10s
        assert state.volume == 0.75  # Updated to 75%
        assert state.speed == 1.5  # Unchanged
        assert state.duration_ms == 180000  # Unchanged
        assert state.is_playing == True

    def test_updated_at_timestamp_changes(self, test_chat_id):
        """Test updated_at timestamp changes with each operation."""
        import time

        control = StreamControl()

        control.seek_stream(test_chat_id, 10)
        first_timestamp = control.get_state(test_chat_id).updated_at

        time.sleep(0.01)  # Small delay

        control.set_volume(test_chat_id, 50)
        second_timestamp = control.get_state(test_chat_id).updated_at

        assert second_timestamp > first_timestamp


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_position_value(self, test_chat_id):
        """Test seeking to very large position (hours)."""
        control = StreamControl()
        result = control.seek_stream(test_chat_id, 7200)  # 2 hours

        assert result == True
        assert control.get_position(test_chat_id) == 7200

    def test_very_small_volume(self, test_chat_id):
        """Test setting very small volume value."""
        control = StreamControl()
        result = control.set_volume(test_chat_id, 0.01)

        assert result == True
        state = control.get_state(test_chat_id)
        assert state.volume == 0.01

    def test_string_chat_id(self):
        """Test operations work with string chat IDs."""
        control = StreamControl()
        chat_id = "-1001234567890"

        control.seek_stream(chat_id, 30)
        control.set_volume(chat_id, 50)

        assert control.get_position(chat_id) == 30
        assert control.get_volume(chat_id) == 0.5

    def test_integer_chat_id(self):
        """Test operations work with integer chat IDs."""
        control = StreamControl()
        chat_id = -1001234567890

        control.seek_stream(str(chat_id), 30)
        control.set_volume(str(chat_id), 50)

        assert control.get_position(str(chat_id)) == 30
        assert control.get_volume(str(chat_id)) == 0.5
