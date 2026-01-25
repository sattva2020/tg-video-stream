"""
Unit tests for AyuGramClient.

This test module covers:
- Client initialization and validation
- Lifecycle management (start, stop, idle)
- Group call operations (join, leave)
- Playback control (play, pause, resume)
- Stream control (seek, volume, speed)
- Event handling system
- State queries and properties
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ayugram import AyuGramClient
from ayugram.types import AudioPiped, AudioVideoPiped, HighQualityAudio, HighQualityVideo
from ayugram.exceptions import AyuGramError, CallError, ConnectionError
import asyncio


# ============================================================================
# Test Client Initialization
# ============================================================================


class TestAyuGramClientInit:
    """Test AyuGramClient initialization and client type validation."""

    def test_init_with_pyrogram_client(self, mock_pyrogram_client):
        """Test initialization with Pyrogram client."""
        client = AyuGramClient(mock_pyrogram_client)

        assert client._app == mock_pyrogram_client
        assert client._is_started == False
        assert client._active_calls == {}
        assert client._playback_states == {}
        assert client._event_listeners == {}
        assert client._client_type == "pyrogram"

    def test_init_with_telethon_client(self, mock_telethon_client):
        """Test initialization with Telethon client."""
        client = AyuGramClient(mock_telethon_client)

        assert client._app == mock_telethon_client
        assert client._is_started == False
        assert client._active_calls == {}
        assert client._client_type == "telethon"

    def test_init_with_invalid_client_type(self):
        """Test initialization raises TypeError for invalid client type."""
        invalid_client = {"not": "a client"}

        with pytest.raises(TypeError) as exc_info:
            AyuGramClient(invalid_client)

        assert "Expected Pyrogram or Telethon client" in str(exc_info.value)
        assert "got dict" in str(exc_info.value)

    def test_init_with_none_client(self):
        """Test initialization raises TypeError for None client."""
        with pytest.raises(TypeError) as exc_info:
            AyuGramClient(None)

        assert "Expected Pyrogram or Telethon client" in str(exc_info.value)

    def test_init_with_string_client(self):
        """Test initialization raises TypeError for string client."""
        with pytest.raises(TypeError) as exc_info:
            AyuGramClient("not_a_client")

        assert "Expected Pyrogram or Telethon client" in str(exc_info.value)


# ============================================================================
# Test Lifecycle Management
# ============================================================================


class TestClientLifecycle:
    """Test client lifecycle methods: start, stop, idle."""

    @pytest.mark.asyncio
    async def test_start_success(self, ayugram_client_unstarted):
        """Test successful client start."""
        client = ayugram_client_unstarted

        await client.start()

        assert client.is_started == True
        assert client._app.start.called

    @pytest.mark.asyncio
    async def test_start_already_started(self, ayugram_client):
        """Test starting already started client raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client.start()

        assert "already started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_start_connection_error(self, mock_pyrogram_client):
        """Test start handles connection errors properly."""
        # Mock start to raise ConnectionError
        mock_pyrogram_client.start.side_effect = ConnectionError("Connection failed")

        client = AyuGramClient(mock_pyrogram_client)

        with pytest.raises(ConnectionError) as exc_info:
            await client.start()

        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_unexpected_error(self, mock_pyrogram_client):
        """Test start handles unexpected errors properly."""
        # Mock start to raise generic exception
        mock_pyrogram_client.start.side_effect = RuntimeError("Unexpected error")

        client = AyuGramClient(mock_pyrogram_client)

        with pytest.raises(AyuGramError) as exc_info:
            await client.start()

        assert "Failed to start client" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_success(self, ayugram_client):
        """Test successful client stop."""
        await ayugram_client.stop()

        assert ayugram_client.is_started == False
        assert ayugram_client._app.stop.called

    @pytest.mark.asyncio
    async def test_stop_not_started(self, ayugram_client_unstarted):
        """Test stopping unstarted client raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.stop()

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_stop_with_active_calls(self, ayugram_client, test_chat_id):
        """Test stop leaves all active calls before stopping."""
        # Add an active call
        stream = AudioPiped("https://example.com/audio.mp3")
        await ayugram_client.join_group_call(test_chat_id, stream)

        assert test_chat_id in ayugram_client.active_calls

        await ayugram_client.stop()

        # Verify call was removed
        assert test_chat_id not in ayugram_client.active_calls
        assert ayugram_client.is_started == False

    @pytest.mark.asyncio
    async def test_stop_handles_leave_call_errors(self, ayugram_client, test_chat_id):
        """Test stop continues even if leaving a call fails."""
        # Add an active call
        stream = AudioPiped("https://example.com/audio.mp3")
        await ayugram_client.join_group_call(test_chat_id, stream)

        # Mock leave_group_call to raise an error
        with patch.object(
            ayugram_client,
            'leave_group_call',
            side_effect=CallError("Leave failed")
        ):
            # Should still stop despite the error
            await ayugram_client.stop()

        assert ayugram_client.is_started == False

    @pytest.mark.asyncio
    async def test_idle_with_client_idle_method(self, ayugram_client):
        """Test idle uses underlying client's idle method."""
        # Create a task that will be cancelled
        task = asyncio.create_task(ayugram_client.idle())

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Cancel the task
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify underlying idle was called
        assert ayugram_client._app.idle.called

    @pytest.mark.asyncio
    async def test_idle_not_started(self, ayugram_client_unstarted):
        """Test idle raises AyuGramError when client not started."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.idle()

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_idle_fallback_to_event_wait(self, mock_pyrogram_client):
        """Test idle falls back to asyncio.Event.wait() when no idle method."""
        # Remove idle method from mock
        delattr(mock_pyrogram_client, 'idle')

        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        # Create a task that will be cancelled
        task = asyncio.create_task(client.idle())

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Cancel the task
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        await client.stop()


# ============================================================================
# Test Group Call Operations
# ============================================================================


class TestGroupCallOperations:
    """Test join_group_call and leave_group_call methods."""

    @pytest.mark.asyncio
    async def test_join_group_call_with_audio_stream(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test joining group call with audio stream."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        assert str(test_chat_id) in ayugram_client.active_calls
        assert ayugram_client.active_calls[str(test_chat_id)]["stream"] == audio_stream

    @pytest.mark.asyncio
    async def test_join_group_call_with_video_stream(
        self, ayugram_client, test_chat_id, video_stream
    ):
        """Test joining group call with video stream."""
        await ayugram_client.join_group_call(test_chat_id, video_stream)

        assert str(test_chat_id) in ayugram_client.active_calls
        assert ayugram_client.active_calls[str(test_chat_id)]["stream"] == video_stream

    @pytest.mark.asyncio
    async def test_join_group_call_with_optional_params(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test joining group call with optional parameters."""
        join_as = 123456
        invite_hash = "invite_hash_123"

        await ayugram_client.join_group_call(
            test_chat_id,
            audio_stream,
            join_as=join_as,
            invite_hash=invite_hash
        )

        call_info = ayugram_client.active_calls[str(test_chat_id)]
        assert call_info["join_as"] == join_as
        assert call_info["invite_hash"] == invite_hash

    @pytest.mark.asyncio
    async def test_join_group_call_not_started(self, ayugram_client_unstarted, test_chat_id, audio_stream):
        """Test joining call when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.join_group_call(test_chat_id, audio_stream)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_join_group_call_invalid_stream_type(self, ayugram_client, test_chat_id):
        """Test joining call with invalid stream type raises AyuGramError."""
        invalid_stream = "not_a_stream_object"

        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client.join_group_call(test_chat_id, invalid_stream)

        assert "Invalid stream type" in str(exc_info.value)
        assert "Expected AudioPiped or AudioVideoPiped" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_join_group_call_with_string_chat_id(
        self, ayugram_client, audio_stream
    ):
        """Test joining call with string chat ID."""
        chat_id_str = "-1001234567890"

        await ayugram_client.join_group_call(chat_id_str, audio_stream)

        assert chat_id_str in ayugram_client.active_calls

    @pytest.mark.asyncio
    async def test_leave_group_call_success(self, ayugram_client, test_chat_id, audio_stream):
        """Test leaving group call successfully."""
        # First join a call
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        assert str(test_chat_id) in ayugram_client.active_calls

        # Then leave it
        await ayugram_client.leave_group_call(test_chat_id)

        assert str(test_chat_id) not in ayugram_client.active_calls

    @pytest.mark.asyncio
    async def test_leave_group_call_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test leaving call when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.leave_group_call(test_chat_id)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_leave_group_call_non_existent(self, ayugram_client, test_chat_id):
        """Test leaving call that doesn't exist doesn't raise error."""
        # Should not raise an error, just log a warning
        await ayugram_client.leave_group_call(test_chat_id)

        assert str(test_chat_id) not in ayugram_client.active_calls

    @pytest.mark.asyncio
    async def test_leave_group_call_cleans_playback_state(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test leaving call cleans up playback state."""
        # Join call and play
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.play(test_chat_id)

        # Verify playback state exists
        assert str(test_chat_id) in ayugram_client._playback_states

        # Leave call
        await ayugram_client.leave_group_call(test_chat_id)

        # Verify playback state cleaned up
        assert str(test_chat_id) not in ayugram_client._playback_states

    @pytest.mark.asyncio
    async def test_join_multiple_calls(
        self, ayugram_client, test_chat_ids, audio_stream
    ):
        """Test joining multiple calls simultaneously."""
        for chat_id in test_chat_ids:
            await ayugram_client.join_group_call(chat_id, audio_stream)

        assert len(ayugram_client.active_calls) == len(test_chat_ids)
        for chat_id in test_chat_ids:
            assert str(chat_id) in ayugram_client.active_calls


# ============================================================================
# Test Playback Control
# ============================================================================


class TestPlaybackControl:
    """Test play, pause, and resume methods."""

    @pytest.mark.asyncio
    async def test_play_starts_playback(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test play method starts playback."""
        # Join call first
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        # Play
        await ayugram_client.play(test_chat_id)

        # Check playback state
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_playing"] == True
        assert state["is_paused"] == False

    @pytest.mark.asyncio
    async def test_play_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test play when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.play(test_chat_id)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_play_no_active_call(self, ayugram_client, test_chat_id):
        """Test play without active call raises CallError."""
        with pytest.raises(CallError) as exc_info:
            await ayugram_client.play(test_chat_id)

        assert "No active call" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pause_pauses_playback(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test pause method pauses playback."""
        # Join and play
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.play(test_chat_id)

        # Pause
        await ayugram_client.pause(test_chat_id)

        # Check playback state
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_playing"] == False
        assert state["is_paused"] == True

    @pytest.mark.asyncio
    async def test_pause_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test pause when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.pause(test_chat_id)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_pause_no_active_call(self, ayugram_client, test_chat_id):
        """Test pause without active call raises CallError."""
        with pytest.raises(CallError) as exc_info:
            await ayugram_client.pause(test_chat_id)

        assert "No active call" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resume_resumes_playback(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test resume method resumes playback."""
        # Join, play, then pause
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.play(test_chat_id)
        await ayugram_client.pause(test_chat_id)

        # Resume
        await ayugram_client.resume(test_chat_id)

        # Check playback state
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_playing"] == True
        assert state["is_paused"] == False

    @pytest.mark.asyncio
    async def test_resume_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test resume when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.resume(test_chat_id)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_resume_no_active_call(self, ayugram_client, test_chat_id):
        """Test resume without active call raises CallError."""
        with pytest.raises(CallError) as exc_info:
            await ayugram_client.resume(test_chat_id)

        assert "No active call" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pause_resume_cycle(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test multiple pause/resume cycles."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        for i in range(3):
            # Play
            await ayugram_client.play(test_chat_id)
            state = ayugram_client._playback_states[str(test_chat_id)]
            assert state["is_playing"] == True
            assert state["is_paused"] == False

            # Pause
            await ayugram_client.pause(test_chat_id)
            state = ayugram_client._playback_states[str(test_chat_id)]
            assert state["is_playing"] == False
            assert state["is_paused"] == True

            # Resume
            await ayugram_client.resume(test_chat_id)
            state = ayugram_client._playback_states[str(test_chat_id)]
            assert state["is_playing"] == True
            assert state["is_paused"] == False


# ============================================================================
# Test Stream Control
# ============================================================================


class TestStreamControl:
    """Test stream control methods: seek, volume, speed."""

    @pytest.mark.asyncio
    async def test_seek_stream(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test seek_stream method."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        await ayugram_client.seek_stream(test_chat_id, 60)

        # Verify stream state was updated
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state is not None
        assert state.position_ms == 60000  # 60 seconds in milliseconds

    @pytest.mark.asyncio
    async def test_seek_stream_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test seek_stream when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            await ayugram_client_unstarted.seek_stream(test_chat_id, 30)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_seek_stream_no_active_call(self, ayugram_client, test_chat_id):
        """Test seek_stream without active call raises CallError."""
        with pytest.raises(CallError) as exc_info:
            await ayugram_client.seek_stream(test_chat_id, 30)

        assert "No active call" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_seek_stream_negative_position(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test seek_stream with negative position raises ValueError."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        with pytest.raises(ValueError):
            await ayugram_client.seek_stream(test_chat_id, -10)

    @pytest.mark.asyncio
    async def test_rewind_stream(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test rewind_stream method."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        # Set initial position
        await ayugram_client.seek_stream(test_chat_id, 120)

        # Rewind by 30 seconds
        await ayugram_client.rewind_stream(test_chat_id, 30)

        # Verify position
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state.position_ms == 90000  # 120 - 30 = 90 seconds

    @pytest.mark.asyncio
    async def test_forward_stream(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test forward_stream method."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        # Set initial position
        await ayugram_client.seek_stream(test_chat_id, 60)

        # Forward by 30 seconds
        await ayugram_client.forward_stream(test_chat_id, 30)

        # Verify position
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state.position_ms == 90000  # 60 + 30 = 90 seconds

    @pytest.mark.asyncio
    async def test_set_volume(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test set_volume method."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        await ayugram_client.set_volume(test_chat_id, 0.5)

        # Verify volume was set
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state is not None
        assert state.volume == 0.5

    @pytest.mark.asyncio
    async def test_set_volume_percentage(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test set_volume with percentage (0-100 range)."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        await ayugram_client.set_volume(test_chat_id, 75)

        # Verify volume was converted and set
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state.volume == 0.75  # 75% = 0.75

    @pytest.mark.asyncio
    async def test_set_volume_invalid_range(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test set_volume with invalid range raises ValueError."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        with pytest.raises(ValueError):
            await ayugram_client.set_volume(test_chat_id, 150)

    @pytest.mark.asyncio
    async def test_set_speed(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test set_speed method."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        await ayugram_client.set_speed(test_chat_id, 1.5)

        # Verify speed was set
        state = ayugram_client._stream_control.get_state(str(test_chat_id))
        assert state is not None
        assert state.speed == 1.5

    @pytest.mark.asyncio
    async def test_set_speed_invalid_range(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test set_speed with invalid range raises ValueError."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        with pytest.raises(ValueError):
            await ayugram_client.set_speed(test_chat_id, 5.0)


# ============================================================================
# Test State Queries
# ============================================================================


class TestStateQueries:
    """Test state query methods: get_stream_state, get_position, get_volume."""

    @pytest.mark.asyncio
    async def test_get_stream_state(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test get_stream_state returns correct state."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.seek_stream(test_chat_id, 60)

        state = ayugram_client.get_stream_state(test_chat_id)

        assert state is not None
        assert state.position_ms == 60000

    @pytest.mark.asyncio
    async def test_get_stream_state_no_state(self, ayugram_client, test_chat_id):
        """Test get_stream_state returns None when no state exists."""
        state = ayugram_client.get_stream_state(test_chat_id)

        assert state is None

    @pytest.mark.asyncio
    async def test_get_stream_state_not_started(self, ayugram_client_unstarted, test_chat_id):
        """Test get_stream_state when client not started raises AyuGramError."""
        with pytest.raises(AyuGramError) as exc_info:
            ayugram_client_unstarted.get_stream_state(test_chat_id)

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_position(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test get_position returns correct position."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.seek_stream(test_chat_id, 90)

        position = ayugram_client.get_position(test_chat_id)

        assert position == 90

    @pytest.mark.asyncio
    async def test_get_position_no_state(self, ayugram_client, test_chat_id):
        """Test get_position returns 0 when no state exists."""
        position = ayugram_client.get_position(test_chat_id)

        assert position == 0

    @pytest.mark.asyncio
    async def test_get_volume(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test get_volume returns correct volume."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client.set_volume(test_chat_id, 0.7)

        volume = ayugram_client.get_volume(test_chat_id)

        assert volume == 0.7

    @pytest.mark.asyncio
    async def test_get_volume_no_state(self, ayugram_client, test_chat_id):
        """Test get_volume returns 1.0 when no state exists."""
        volume = ayugram_client.get_volume(test_chat_id)

        assert volume == 1.0


# ============================================================================
# Test Event Handling
# ============================================================================


class TestEventHandling:
    """Test event handling system: on, remove_listener, _emit_event."""

    def test_on_registers_event_listener(self, ayugram_client_unstarted):
        """Test on method registers event listeners."""
        def callback(chat_id):
            pass

        ayugram_client_unstarted.on('stream_ended', callback)

        assert 'stream_ended' in ayugram_client_unstarted._event_listeners
        assert callback in ayugram_client_unstarted._event_listeners['stream_ended']

    def test_on_multiple_listeners(self, ayugram_client_unstarted):
        """Test on method registers multiple listeners for same event."""
        def callback1(chat_id):
            pass

        def callback2(chat_id):
            pass

        ayugram_client_unstarted.on('stream_ended', callback1)
        ayugram_client_unstarted.on('stream_ended', callback2)

        assert len(ayugram_client_unstarted._event_listeners['stream_ended']) == 2

    def test_on_empty_event_name_raises_error(self, ayugram_client_unstarted):
        """Test on with empty event name raises AyuGramError."""
        def callback(chat_id):
            pass

        with pytest.raises(AyuGramError) as exc_info:
            ayugram_client_unstarted.on('', callback)

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_on_non_callable_raises_error(self, ayugram_client_unstarted):
        """Test on with non-callable raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            ayugram_client_unstarted.on('stream_ended', "not_callable")

        assert "must be callable" in str(exc_info.value)

    def test_remove_listener_removes_callback(self, ayugram_client_unstarted):
        """Test remove_listener removes specific callback."""
        def callback(chat_id):
            pass

        ayugram_client_unstarted.on('stream_ended', callback)
        assert callback in ayugram_client_unstarted._event_listeners['stream_ended']

        ayugram_client_unstarted.remove_listener('stream_ended', callback)

        assert callback not in ayugram_client_unstarted._event_listeners.get('stream_ended', [])

    def test_remove_listener_cleans_empty_list(self, ayugram_client_unstarted):
        """Test remove_listener cleans up empty event lists."""
        def callback(chat_id):
            pass

        ayugram_client_unstarted.on('stream_ended', callback)
        ayugram_client_unstarted.remove_listener('stream_ended', callback)

        assert 'stream_ended' not in ayugram_client_unstarted._event_listeners

    def test_remove_listener_non_existent_event(self, ayugram_client_unstarted):
        """Test remove_listener with non-existent event doesn't raise error."""
        def callback(chat_id):
            pass

        # Should not raise an error
        ayugram_client_unstarted.remove_listener('non_existent_event', callback)

    def test_remove_listener_non_existent_callback(self, ayugram_client_unstarted):
        """Test remove_listener with non-existent callback doesn't raise error."""
        def callback1(chat_id):
            pass

        def callback2(chat_id):
            pass

        ayugram_client_unstarted.on('stream_ended', callback1)

        # Should not raise an error
        ayugram_client_unstarted.remove_listener('stream_ended', callback2)

    @pytest.mark.asyncio
    async def test_emit_event_calls_sync_callback(self, ayugram_client):
        """Test _emit_event calls sync callbacks."""
        callback_called = []

        def callback(chat_id):
            callback_called.append(chat_id)

        ayugram_client.on('test_event', callback)
        await ayugram_client._emit_event('test_event', -1001234567890)

        assert -1001234567890 in callback_called

    @pytest.mark.asyncio
    async def test_emit_event_calls_async_callback(self, ayugram_client):
        """Test _emit_event calls async callbacks."""
        callback_called = []

        async def callback(chat_id):
            callback_called.append(chat_id)

        ayugram_client.on('test_event', callback)
        await ayugram_client._emit_event('test_event', -1001234567890)

        assert -1001234567890 in callback_called

    @pytest.mark.asyncio
    async def test_emit_event_calls_multiple_listeners(self, ayugram_client):
        """Test _emit_event calls all registered listeners."""
        callback_called = []

        def callback1(chat_id):
            callback_called.append('callback1')

        def callback2(chat_id):
            callback_called.append('callback2')

        ayugram_client.on('test_event', callback1)
        ayugram_client.on('test_event', callback2)
        await ayugram_client._emit_event('test_event', -1001234567890)

        assert 'callback1' in callback_called
        assert 'callback2' in callback_called

    @pytest.mark.asyncio
    async def test_emit_event_handles_callback_errors(self, ayugram_client):
        """Test _emit_event continues despite callback errors."""
        callback_called = []

        def failing_callback(chat_id):
            raise RuntimeError("Callback error")

        def working_callback(chat_id):
            callback_called.append('working')

        ayugram_client.on('test_event', failing_callback)
        ayugram_client.on('test_event', working_callback)
        await ayugram_client._emit_event('test_event', -1001234567890)

        # Working callback should still be called despite failing callback
        assert 'working' in callback_called

    @pytest.mark.asyncio
    async def test_emit_event_no_listeners(self, ayugram_client):
        """Test _emit_event with no listeners doesn't raise error."""
        # Should not raise an error
        await ayugram_client._emit_event('non_existent_event', -1001234567890)


# ============================================================================
# Test Properties
# ============================================================================


class TestClientProperties:
    """Test client properties: is_started, active_calls, event_listeners."""

    def test_is_started_false_initially(self, ayugram_client_unstarted):
        """Test is_started is False before starting."""
        assert ayugram_client_unstarted.is_started == False

    def test_is_started_true_after_start(self, ayugram_client):
        """Test is_started is True after starting."""
        assert ayugram_client.is_started == True

    def test_is_started_false_after_stop(self, ayugram_client):
        """Test is_started is False after stopping."""
        # This test needs to be async
        import asyncio

        async def stop_and_check():
            await ayugram_client.stop()
            assert ayugram_client.is_started == False

        asyncio.run(stop_and_check())

    def test_active_calls_returns_copy(self, ayugram_client):
        """Test active_calls returns a copy of the internal dict."""
        calls = ayugram_client.active_calls

        # Modify returned dict
        calls['new_call'] = {}

        # Internal dict should not be modified
        assert 'new_call' not in ayugram_client._active_calls

    def test_active_calls_empty_initially(self, ayugram_client):
        """Test active_calls is empty initially."""
        assert ayugram_client.active_calls == {}

    @pytest.mark.asyncio
    async def test_active_calls_includes_active_calls(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test active_calls includes joined calls."""
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        calls = ayugram_client.active_calls

        assert str(test_chat_id) in calls

    def test_event_listeners_returns_copy(self, ayugram_client):
        """Test event_listeners returns a copy of the internal dict."""
        def callback(chat_id):
            pass

        ayugram_client.on('test_event', callback)
        listeners = ayugram_client.event_listeners

        # Modify returned dict
        listeners['new_event'] = []

        # Internal dict should not be modified
        assert 'new_event' not in ayugram_client._event_listeners

    def test_event_listeners_empty_initially(self, ayugram_client):
        """Test event_listeners is empty initially."""
        assert ayugram_client.event_listeners == {}

    def test_event_listeners_includes_registered_events(self, ayugram_client):
        """Test event_listeners includes registered events."""
        def callback(chat_id):
            pass

        ayugram_client.on('test_event', callback)

        listeners = ayugram_client.event_listeners

        assert 'test_event' in listeners
        assert callback in listeners['test_event']


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestClientIntegration:
    """Test integration scenarios combining multiple client features."""

    @pytest.mark.asyncio
    async def test_full_call_lifecycle(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test complete call lifecycle: join, play, pause, resume, leave."""
        # Join call
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        assert str(test_chat_id) in ayugram_client.active_calls

        # Play
        await ayugram_client.play(test_chat_id)
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_playing"] == True

        # Pause
        await ayugram_client.pause(test_chat_id)
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_paused"] == True

        # Resume
        await ayugram_client.resume(test_chat_id)
        state = ayugram_client._playback_states[str(test_chat_id)]
        assert state["is_playing"] == True

        # Leave call
        await ayugram_client.leave_group_call(test_chat_id)
        assert str(test_chat_id) not in ayugram_client.active_calls

    @pytest.mark.asyncio
    async def test_stream_control_during_call(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test stream control operations during a call."""
        # Join call
        await ayugram_client.join_group_call(test_chat_id, audio_stream)

        # Seek
        await ayugram_client.seek_stream(test_chat_id, 60)
        assert ayugram_client.get_position(test_chat_id) == 60

        # Set volume
        await ayugram_client.set_volume(test_chat_id, 0.6)
        assert ayugram_client.get_volume(test_chat_id) == 0.6

        # Set speed
        await ayugram_client.set_speed(test_chat_id, 1.25)
        state = ayugram_client.get_stream_state(test_chat_id)
        assert state.speed == 1.25

        # Rewind
        await ayugram_client.rewind_stream(test_chat_id, 10)
        assert ayugram_client.get_position(test_chat_id) == 50

        # Forward
        await ayugram_client.forward_stream(test_chat_id, 20)
        assert ayugram_client.get_position(test_chat_id) == 70

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls_with_controls(
        self, ayugram_client, test_chat_ids, audio_stream
    ):
        """Test managing multiple concurrent calls with individual controls."""
        # Join multiple calls
        for chat_id in test_chat_ids:
            await ayugram_client.join_group_call(chat_id, audio_stream)

        # Control each call independently
        for i, chat_id in enumerate(test_chat_ids):
            # Set different position for each call
            position = (i + 1) * 30
            await ayugram_client.seek_stream(chat_id, position)
            assert ayugram_client.get_position(chat_id) == position

            # Set different volume for each call
            volume = 0.3 + (i * 0.2)
            await ayugram_client.set_volume(chat_id, volume)
            assert ayugram_client.get_volume(chat_id) == volume

    @pytest.mark.asyncio
    async def test_event_driven_workflow(
        self, ayugram_client, test_chat_id, audio_stream
    ):
        """Test event-driven workflow with callbacks."""
        events = []

        def on_call_joined(chat_id):
            events.append(('joined', chat_id))

        def on_call_left(chat_id):
            events.append(('left', chat_id))

        ayugram_client.on('call_joined', on_call_joined)
        ayugram_client.on('call_left', on_call_left)

        # Join and leave call
        await ayugram_client.join_group_call(test_chat_id, audio_stream)
        await ayugram_client._emit_event('call_joined', test_chat_id)
        await ayugram_client.leave_group_call(test_chat_id)
        await ayugram_client._emit_event('call_left', test_chat_id)

        # Verify events were triggered
        assert ('joined', test_chat_id) in events
        assert ('left', test_chat_id) in events

    @pytest.mark.asyncio
    async def test_client_start_stop_restart(
        self, ayugram_client_unstarted, test_chat_id, audio_stream
    ):
        """Test client can be started, stopped, and restarted."""
        client = ayugram_client_unstarted

        # First start
        await client.start()
        assert client.is_started == True

        # Stop
        await client.stop()
        assert client.is_started == False

        # Restart
        await client.start()
        assert client.is_started == True

        # Should be able to join calls after restart
        await client.join_group_call(test_chat_id, audio_stream)
        assert str(test_chat_id) in client.active_calls

        await client.stop()
