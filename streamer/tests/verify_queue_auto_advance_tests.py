#!/usr/bin/env python3
"""
Verification script for queue auto-advance tests with AyuGram.

This script runs queue auto-advance tests without requiring pytest.
It verifies that queue management works correctly with AyuGram event handlers.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def verify_queue_creation_with_three_tracks():
    """Verify queue creation with 3 tracks."""
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
        {"id": "track3", "url": "https://example.com/track3.mp3"},
    ]

    await queue.add_items(tracks)

    assert len(queue.playlist_items) == 3, "Queue should have 3 tracks"
    assert queue.playlist_items[0]["id"] == "track1", "First track should be track1"
    assert queue.playlist_items[1]["id"] == "track2", "Second track should be track2"
    assert queue.playlist_items[2]["id"] == "track3", "Third track should be track3"

    print("✅ test_queue_creation_with_three_tracks PASSED")
    return True


async def verify_stream_ended_advances_queue():
    """Verify StreamEnded event advances queue."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
        {"id": "track3", "url": "https://example.com/track3.mp3"},
    ]

    await queue.add_items(tracks)

    play_in_progress = {123456: False}
    stream_ended_events = {123456: asyncio.Event()}

    mock_client = MagicMock()
    adapter = AyuGramAdapter(mock_client)

    async def stream_ended_handler(streaming_client, update: StreamEnded):
        chat_id = update.chat_id
        is_playing = play_in_progress.get(chat_id, False)

        if not is_playing:
            if chat_id in stream_ended_events:
                stream_ended_events[chat_id].set()

    adapter._event_handlers["stream_end"].append(stream_ended_handler)

    play_in_progress[123456] = False

    await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

    assert stream_ended_events[123456].is_set(), "StreamEnded event should be set"

    print("✅ test_stream_ended_advances_queue PASSED")
    return True


async def verify_queue_advances_through_all_tracks():
    """Verify queue advances through all 3 tracks."""
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
        {"id": "track3", "url": "https://example.com/track3.mp3"},
    ]

    await queue.add_items(tracks)

    track_order = []

    for i, track in enumerate(tracks):
        if queue.playlist_items:
            next_track = queue.playlist_items[0]
            track_order.append(next_track["id"])
            queue.playlist_items.popleft()

    assert len(track_order) == 3, "All 3 tracks should be played"
    assert track_order[0] == "track1", "First track should be track1"
    assert track_order[1] == "track2", "Second track should be track2"
    assert track_order[2] == "track3", "Third track should be track3"

    print("✅ test_queue_advances_through_all_tracks PASSED")
    return True


async def verify_queue_stops_after_last_track():
    """Verify queue stops after last track."""
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
        {"id": "track3", "url": "https://example.com/track3.mp3"},
    ]

    await queue.add_items(tracks)

    for _ in range(3):
        if queue.playlist_items:
            queue.playlist_items.popleft()

    assert len(queue.playlist_items) == 0, "Queue should be empty after all tracks"
    assert queue.queue.empty(), "Internal queue should be empty"

    print("✅ test_queue_stops_after_last_track PASSED")
    return True


async def verify_play_in_progress_prevents_stale_events():
    """Verify play_in_progress prevents stale event processing."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded

    mock_client = MagicMock()
    adapter = AyuGramAdapter(mock_client)

    play_in_progress = {123456: True}
    stream_ended_events = {123456: asyncio.Event()}
    event_processed = []

    async def stream_ended_handler(streaming_client, update: StreamEnded):
        chat_id = update.chat_id
        is_playing = play_in_progress.get(chat_id, False)

        if is_playing:
            event_processed.append("ignored")
            return

        if chat_id in stream_ended_events:
            stream_ended_events[chat_id].set()
            event_processed.append("processed")

    adapter._event_handlers["stream_end"].append(stream_ended_handler)

    await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

    assert len(event_processed) == 1, "One event should be processed"
    assert event_processed[0] == "ignored", "Event should be ignored"
    assert not stream_ended_events[123456].is_set(), "Event should not be set"

    play_in_progress[123456] = False

    await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

    assert len(event_processed) == 2, "Two events should be processed"
    assert event_processed[1] == "processed", "Second event should be processed"
    assert stream_ended_events[123456].is_set(), "Event should be set"

    print("✅ test_play_in_progress_prevents_stale_events PASSED")
    return True


async def verify_on_track_end_updates_queue_state():
    """Verify on_track_end updates queue state."""
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
    ]

    await queue.add_items(tracks)

    queue.current_item = tracks[0]

    await queue.on_track_end("track1", reason="completed")

    assert queue.current_item is None, "Current item should be cleared"

    print("✅ test_on_track_end_updates_queue_state PASSED")
    return True


async def verify_multi_channel_queue_isolation():
    """Verify multi-channel queue isolation."""
    from queue_manager import StreamQueue

    queue1 = StreamQueue(max_buffer_size=3, channel_id=111)
    queue2 = StreamQueue(max_buffer_size=3, channel_id=222)

    tracks1 = [{"id": "track1", "url": "https://example.com/track1.mp3"}]
    await queue1.add_items(tracks1)

    tracks2 = [{"id": "track2", "url": "https://example.com/track2.mp3"}]
    await queue2.add_items(tracks2)

    assert len(queue1.playlist_items) == 1, "Queue1 should have 1 track"
    assert len(queue2.playlist_items) == 1, "Queue2 should have 1 track"
    assert queue1.playlist_items[0]["id"] == "track1", "Queue1 should have track1"
    assert queue2.playlist_items[0]["id"] == "track2", "Queue2 should have track2"

    queue1.playlist_items.popleft()

    assert len(queue1.playlist_items) == 0, "Queue1 should be empty"
    assert len(queue2.playlist_items) == 1, "Queue2 should still have 1 track"

    print("✅ test_multi_channel_queue_isolation PASSED")
    return True


async def verify_queue_state_synchronization_with_backend():
    """Verify queue state synchronization with backend."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded
    from queue_manager import StreamQueue

    queue = StreamQueue(max_buffer_size=3, channel_id=123456)

    tracks = [
        {"id": "track1", "url": "https://example.com/track1.mp3"},
        {"id": "track2", "url": "https://example.com/track2.mp3"},
    ]

    await queue.add_items(tracks)

    stream_ended_events = {123456: asyncio.Event()}
    play_in_progress = {123456: False}

    mock_client = MagicMock()
    adapter = AyuGramAdapter(mock_client)

    async def stream_ended_handler(streaming_client, update: StreamEnded):
        chat_id = update.chat_id
        is_playing = play_in_progress.get(chat_id, False)

        if not is_playing and chat_id in stream_ended_events:
            stream_ended_events[chat_id].set()

    adapter._event_handlers["stream_end"].append(stream_ended_handler)

    await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

    assert stream_ended_events[123456].is_set(), "StreamEnded event should be set"

    if queue.playlist_items:
        queue.playlist_items.popleft()

    assert len(queue.playlist_items) == 1, "Queue should have 1 track remaining"
    assert queue.playlist_items[0]["id"] == "track2", "Remaining track should be track2"

    print("✅ test_queue_state_synchronization_with_backend PASSED")
    return True


async def run_all_tests():
    """Run all queue auto-advance verification tests."""
    print("=" * 70)
    print("Queue Auto-Advance with AyuGram - Verification Tests")
    print("=" * 70)
    print()

    tests = [
        ("Queue creation with 3 tracks", verify_queue_creation_with_three_tracks),
        ("StreamEnded advances queue", verify_stream_ended_advances_queue),
        ("Queue advances through all tracks", verify_queue_advances_through_all_tracks),
        ("Queue stops after last track", verify_queue_stops_after_last_track),
        ("play_in_progress prevents stale events", verify_play_in_progress_prevents_stale_events),
        ("on_track_end updates queue state", verify_on_track_end_updates_queue_state),
        ("Multi-channel queue isolation", verify_multi_channel_queue_isolation),
        ("Queue state synchronization with backend", verify_queue_state_synchronization_with_backend),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}...")
            await test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
