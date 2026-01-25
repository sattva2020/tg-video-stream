"""
Integration tests for voice call operations with mock JSON-RPC server.

These tests verify the complete voice call workflow including:
- Joining and leaving voice chats
- Stream control (play, pause, resume)
- Multiple concurrent calls
- Error handling for invalid operations
- State management during calls

Tests use the MockAyuGramServer to simulate the AyuGram JSON-RPC API.
"""

import asyncio
from unittest.mock import Mock

import pytest

from ayugram import AyuGramClient
from ayugram.exceptions import AyuGramError, CallError
from ayugram.types import AudioPiped, AudioVideoPiped, HighQualityAudio


class TestVoiceCallOperations:
    """Test voice call operations with mock server."""

    @pytest.mark.asyncio
    async def test_join_group_call_with_audio_stream(self, mock_server, mock_pyrogram_client):
        """
        Test joining a group call with audio stream.

        This test verifies:
        1. Client connects to mock server
        2. join_group_call is called with AudioPiped stream
        3. Call is tracked in active_calls
        4. Server returns success response
        """
        # Create and start AyuGram client
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        # Create audio stream
        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join group call
        await client.join_group_call(chat_id, stream)

        # Verify call is tracked
        assert chat_id in client.active_calls
        assert client.active_calls[chat_id]["stream"] == stream

        # Cleanup
        await client.stop()

    @pytest.mark.asyncio
    async def test_join_group_call_with_video_stream(self, mock_server, mock_pyrogram_client):
        """
        Test joining a group call with video stream.

        Verifies that AudioVideoPiped streams work correctly
        for video calls.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        # Create video stream
        stream = AudioVideoPiped("https://example.com/video.mp4")
        chat_id = -1001234567890

        # Join group call
        await client.join_group_call(chat_id, stream)

        # Verify call is tracked
        assert chat_id in client.active_calls
        assert isinstance(client.active_calls[chat_id]["stream"], AudioVideoPiped)

        await client.stop()

    @pytest.mark.asyncio
    async def test_join_group_call_with_high_quality_audio(self, mock_server, mock_pyrogram_client):
        """
        Test joining a group call with high quality audio settings.

        Verifies that HighQualityAudio parameters are properly
        passed through to the stream.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        # Create high quality audio stream
        high_quality = HighQualityAudio(
            bitrate=128,
            channels=2,
        )
        stream = AudioPiped("https://example.com/hq_audio.mp3", high_quality)
        chat_id = -1001234567890

        # Join group call
        await client.join_group_call(chat_id, stream)

        # Verify call is tracked with correct stream type
        assert chat_id in client.active_calls
        assert client.active_calls[chat_id]["stream"].parameters == high_quality

        await client.stop()

    @pytest.mark.asyncio
    async def test_leave_group_call(self, mock_server, mock_pyrogram_client):
        """
        Test leaving a group call.

        Verifies:
        1. Leave call removes it from active_calls
        2. Playback state is cleaned up
        3. Stream control state is cleaned up
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call first
        await client.join_group_call(chat_id, stream)
        assert chat_id in client.active_calls

        # Leave call
        await client.leave_group_call(chat_id)

        # Verify call is removed
        assert chat_id not in client.active_calls
        assert chat_id not in client._playback_states

        await client.stop()

    @pytest.mark.asyncio
    async def test_play_operation(self, mock_server, mock_pyrogram_client):
        """
        Test play operation for stream control.

        Verifies that play() starts playback and updates
        the playback state correctly.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call first
        await client.join_group_call(chat_id, stream)

        # Play stream
        await client.play(chat_id)

        # Verify playback state
        state = client._playback_states.get(chat_id)
        assert state is not None
        assert state["is_playing"] is True
        assert state["is_paused"] is False

        await client.stop()

    @pytest.mark.asyncio
    async def test_pause_operation(self, mock_server, mock_pyrogram_client):
        """
        Test pause operation for stream control.

        Verifies that pause() stops playback and updates
        the playback state correctly.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call and play
        await client.join_group_call(chat_id, stream)
        await client.play(chat_id)

        # Pause stream
        await client.pause(chat_id)

        # Verify playback state
        state = client._playback_states.get(chat_id)
        assert state is not None
        assert state["is_playing"] is False
        assert state["is_paused"] is True

        await client.stop()

    @pytest.mark.asyncio
    async def test_resume_operation(self, mock_server, mock_pyrogram_client):
        """
        Test resume operation for stream control.

        Verifies that resume() resumes playback from paused state.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call, play, then pause
        await client.join_group_call(chat_id, stream)
        await client.play(chat_id)
        await client.pause(chat_id)

        # Resume stream
        await client.resume(chat_id)

        # Verify playback state
        state = client._playback_states.get(chat_id)
        assert state is not None
        assert state["is_playing"] is True
        assert state["is_paused"] is False

        await client.stop()

    @pytest.mark.asyncio
    async def test_multiple_pause_resume_cycles(self, mock_server, mock_pyrogram_client):
        """
        Test multiple pause/resume cycles.

        Verifies that state transitions work correctly across
        multiple play/pause/resume cycles.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call
        await client.join_group_call(chat_id, stream)

        # First cycle: play -> pause -> resume
        await client.play(chat_id)
        assert client._playback_states[chat_id]["is_playing"] is True

        await client.pause(chat_id)
        assert client._playback_states[chat_id]["is_paused"] is True

        await client.resume(chat_id)
        assert client._playback_states[chat_id]["is_playing"] is True

        # Second cycle: pause again
        await client.pause(chat_id)
        assert client._playback_states[chat_id]["is_paused"] is True

        await client.stop()

    @pytest.mark.asyncio
    async def test_join_group_call_without_starting_client(self, mock_server, mock_pyrogram_client):
        """
        Test joining call without starting client first.

        Verifies that AyuGramError is raised when trying to
        join a call before starting the client.
        """
        client = AyuGramClient(mock_pyrogram_client)
        # Don't start the client

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Should raise error because client is not started
        with pytest.raises(AyuGramError, match="Client is not started"):
            await client.join_group_call(chat_id, stream)

    @pytest.mark.asyncio
    async def test_join_with_invalid_stream_type(self, mock_server, mock_pyrogram_client):
        """
        Test joining call with invalid stream type.

        Verifies that AyuGramError is raised when stream
        is not AudioPiped or AudioVideoPiped.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        chat_id = -1001234567890

        # Try to join with invalid stream type
        with pytest.raises(AyuGramError, match="Invalid stream type"):
            await client.join_group_call(chat_id, "not_a_stream")  # type: ignore

        await client.stop()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self, mock_server, mock_pyrogram_client):
        """
        Test multiple concurrent voice calls.

        Verifies that the SDK can handle multiple simultaneous
        voice calls in different chats.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        # Create multiple streams for different chats
        chats = [
            (-1001111111111, AudioPiped("https://example.com/audio1.mp3")),
            (-1002222222222, AudioVideoPiped("https://example.com/video1.mp4")),
            (-1003333333333, AudioPiped("https://example.com/audio2.mp3")),
        ]

        # Join all calls
        for chat_id, stream in chats:
            await client.join_group_call(chat_id, stream)

        # Verify all calls are tracked
        assert len(client.active_calls) == 3
        for chat_id, stream in chats:
            assert chat_id in client.active_calls
            assert client.active_calls[chat_id]["stream"] == stream

        # Leave all calls
        for chat_id, _ in chats:
            await client.leave_group_call(chat_id)

        # Verify all calls are removed
        assert len(client.active_calls) == 0

        await client.stop()

    @pytest.mark.asyncio
    async def test_leave_nonexistent_call(self, mock_server, mock_pyrogram_client):
        """
        Test leaving a call that doesn't exist.

        Verifies that leaving a nonexistent call is handled
        gracefully with a warning (not an error).
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        chat_id = -1001234567890

        # Leave call that was never joined
        # Should not raise an error, just log a warning
        await client.leave_group_call(chat_id)

        # Verify no active calls
        assert len(client.active_calls) == 0

        await client.stop()

    @pytest.mark.asyncio
    async def test_playback_control_on_nonexistent_call(self, mock_server, mock_pyrogram_client):
        """
        Test playback control on a chat with no active call.

        Verifies that play/pause/resume operations raise
        CallError when there's no active call.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        chat_id = -1001234567890

        # Try to play without joining call
        with pytest.raises(CallError, match="No active call"):
            await client.play(chat_id)

        # Try to pause without joining call
        with pytest.raises(CallError, match="No active call"):
            await client.pause(chat_id)

        # Try to resume without joining call
        with pytest.raises(CallError, match="No active call"):
            await client.resume(chat_id)

        await client.stop()

    @pytest.mark.asyncio
    async def test_full_voice_call_workflow(self, mock_server, mock_pyrogram_client):
        """
        Test complete voice call workflow from join to leave.

        This test verifies the full workflow:
        1. Join voice chat
        2. Start playback
        3. Pause playback
        4. Resume playback
        5. Leave voice chat
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/song.mp3")
        chat_id = -1001234567890

        # Step 1: Join voice chat
        await client.join_group_call(chat_id, stream)
        assert chat_id in client.active_calls

        # Step 2: Start playback
        await client.play(chat_id)
        assert client._playback_states[chat_id]["is_playing"] is True

        # Step 3: Pause playback
        await client.pause(chat_id)
        assert client._playback_states[chat_id]["is_paused"] is True

        # Step 4: Resume playback
        await client.resume(chat_id)
        assert client._playback_states[chat_id]["is_playing"] is True
        assert client._playback_states[chat_id]["is_paused"] is False

        # Step 5: Leave voice chat
        await client.leave_group_call(chat_id)
        assert chat_id not in client.active_calls

        await client.stop()


class TestVoiceCallErrorHandling:
    """Test error handling in voice call operations."""

    @pytest.mark.asyncio
    async def test_leave_call_without_starting_client(self, mock_server, mock_pyrogram_client):
        """
        Test leaving call without starting client first.

        Verifies that AyuGramError is raised.
        """
        client = AyuGramClient(mock_pyrogram_client)
        # Don't start the client

        chat_id = -1001234567890

        with pytest.raises(AyuGramError, match="Client is not started"):
            await client.leave_group_call(chat_id)

    @pytest.mark.asyncio
    async def test_play_without_starting_client(self, mock_server, mock_pyrogram_client):
        """
        Test play operation without starting client.

        Verifies that AyuGramError is raised.
        """
        client = AyuGramClient(mock_pyrogram_client)
        # Don't start the client

        chat_id = -1001234567890

        with pytest.raises(AyuGramError, match="Client is not started"):
            await client.play(chat_id)

    @pytest.mark.asyncio
    async def test_pause_without_starting_client(self, mock_server, mock_pyrogram_client):
        """
        Test pause operation without starting client.

        Verifies that AyuGramError is raised.
        """
        client = AyuGramClient(mock_pyrogram_client)
        # Don't start the client

        chat_id = -1001234567890

        with pytest.raises(AyuGramError, match="Client is not started"):
            await client.pause(chat_id)

    @pytest.mark.asyncio
    async def test_resume_without_starting_client(self, mock_server, mock_pyrogram_client):
        """
        Test resume operation without starting client.

        Verifies that AyuGramError is raised.
        """
        client = AyuGramClient(mock_pyrogram_client)
        # Don't start the client

        chat_id = -1001234567890

        with pytest.raises(AyuGramError, match="Client is not started"):
            await client.resume(chat_id)


class TestVoiceCallStateManagement:
    """Test state management during voice call operations."""

    @pytest.mark.asyncio
    async def test_active_calls_property(self, mock_server, mock_pyrogram_client):
        """
        Test active_calls property.

        Verifies that active_calls returns a copy of the internal
        state dictionary (not a reference).
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call
        await client.join_group_call(chat_id, stream)

        # Get active calls
        active_calls = client.active_calls
        assert chat_id in active_calls

        # Modify the returned dict
        active_calls["modified"] = True

        # Verify internal state is not modified
        assert "modified" not in client._active_calls

        await client.stop()

    @pytest.mark.asyncio
    async def test_stream_control_state_cleanup(self, mock_server, mock_pyrogram_client):
        """
        Test that stream control state is cleaned up on leave.

        Verifies that leaving a call also cleans up any
        associated stream control state.
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")
        chat_id = -1001234567890

        # Join call and perform stream control operations
        await client.join_group_call(chat_id, stream)

        # Set some stream control state
        client._stream_control.set_volume(chat_id, 75)
        client._stream_control.seek_stream(chat_id, 30)

        # Verify stream control state exists
        assert client._stream_control.has_state(chat_id)

        # Leave call
        await client.leave_group_call(chat_id)

        # Verify stream control state is cleaned up
        assert not client._stream_control.has_state(chat_id)

        await client.stop()

    @pytest.mark.asyncio
    async def test_chat_id_type_flexibility(self, mock_server, mock_pyrogram_client):
        """
        Test that chat_id accepts both int and str types.

        Verifies that the client can handle chat IDs in different
        formats (int, str with and without -100 prefix).
        """
        client = AyuGramClient(mock_pyrogram_client)
        await client.start()

        stream = AudioPiped("https://example.com/audio.mp3")

        # Test with different chat ID formats
        chat_ids = [
            -1001234567890,  # Integer supergroup ID
            "-1001234567890",  # String supergroup ID
            "abcdefgh",  # String username
        ]

        for chat_id in chat_ids:
            # Join call
            await client.join_group_call(chat_id, stream)
            assert str(chat_id) in client.active_calls

            # Leave call
            await client.leave_group_call(chat_id)
            assert str(chat_id) not in client.active_calls

        await client.stop()
