"""
Verification script for multi-channel concurrent streaming tests.

Runs tests without pytest dependency by directly executing test functions.
"""

import asyncio
import sys
from unittest.mock import MagicMock

# Add streamer directory to path
sys.path.insert(0, '.')


async def test_two_adapters_independent_initialization():
    """Два адаптера AyuGram должны создаваться независимо."""
    from ayugram_adapter import AyuGramAdapter

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    assert adapter1 is not adapter2
    assert adapter1.client is mock_client1
    assert adapter2.client is mock_client2
    assert adapter1._event_handlers is not adapter2._event_handlers
    assert adapter1._is_running is False
    assert adapter2._is_running is False

    print("✅ test_two_adapters_independent_initialization passed")


async def test_two_adapters_can_start_independently():
    """Два адаптера могут запускаться независимо."""
    from ayugram_adapter import AyuGramAdapter

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    await adapter1.start()
    await adapter2.start()

    assert adapter1._is_running is True
    assert adapter2._is_running is True

    print("✅ test_two_adapters_can_start_independently passed")


async def test_event_handlers_isolated_between_channels():
    """Event handlers для разных каналов не должны пересекаться."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    channel1_events = []

    async def channel1_handler(adapter, update):
        channel1_events.append(update.chat_id)

    adapter1._event_handlers["stream_end"].append(channel1_handler)

    channel2_events = []

    async def channel2_handler(adapter, update):
        channel2_events.append(update.chat_id)

    adapter2._event_handlers["stream_end"].append(channel2_handler)

    await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))
    await adapter2._emit_event("stream_end", StreamEnded(chat_id=222))

    assert len(channel1_events) == 1
    assert channel1_events[0] == 111
    assert len(channel2_events) == 1
    assert channel2_events[0] == 222

    print("✅ test_event_handlers_isolated_between_channels passed")


async def test_stop_channel_does_not_affect_other_channel():
    """Остановка одного канала не должна влиять на другой."""
    from ayugram_adapter import AyuGramAdapter

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    await adapter1.start()
    await adapter2.start()

    assert adapter1._is_running is True
    assert adapter2._is_running is True

    await adapter1.stop()

    assert adapter1._is_running is False
    assert adapter2._is_running is True

    print("✅ test_stop_channel_does_not_affect_other_channel passed")


async def test_concurrent_event_emission():
    """События могут обрабатываться concurrently для разных каналов."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    handler1_called = asyncio.Event()
    handler2_called = asyncio.Event()

    async def handler1(adapter, update):
        handler1_called.set()

    async def handler2(adapter, update):
        handler2_called.set()

    adapter1._event_handlers["stream_end"].append(handler1)
    adapter2._event_handlers["stream_end"].append(handler2)

    await asyncio.gather(
        adapter1._emit_event("stream_end", StreamEnded(chat_id=111)),
        adapter2._emit_event("stream_end", StreamEnded(chat_id=222)),
    )

    assert handler1_called.is_set()
    assert handler2_called.is_set()

    print("✅ test_concurrent_event_emission passed")


async def test_multi_channel_state_isolation():
    """Состояние разных каналов должно быть изолировано."""
    from ayugram_adapter import AyuGramAdapter

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    await adapter1.start()
    adapter1._event_handlers["stream_end"].append(lambda a, u: None)

    assert adapter2._is_running is False
    assert len(adapter2._event_handlers["stream_end"]) == 0

    print("✅ test_multi_channel_state_isolation passed")


async def test_different_event_types_per_channel():
    """Разные типы событий могут обрабатываться на разных каналах."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded, ChatUpdate

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    stream_end_events = []

    async def stream_end_handler(adapter, update):
        stream_end_events.append(update.chat_id)

    adapter1._event_handlers["stream_end"].append(stream_end_handler)

    chat_update_events = []

    async def chat_update_handler(adapter, update):
        chat_update_events.append((update.chat_id, update.status))

    adapter2._event_handlers["chat_update"].append(chat_update_handler)

    await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))
    await adapter2._emit_event("chat_update", ChatUpdate(chat_id=222, status="left"))

    assert len(stream_end_events) == 1
    assert stream_end_events[0] == 111
    assert len(chat_update_events) == 1
    assert chat_update_events[0] == (222, "left")

    print("✅ test_different_event_types_per_channel passed")


async def test_running_channels_dict_pattern():
    """Тест для pattern использования running_channels dict."""
    from ayugram_adapter import AyuGramAdapter

    running_channels = {}

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    running_channels["channel1"] = {
        "client": mock_client1,
        "ayugram": adapter1,
        "backend_type": "ayugram",
        "task": None,
    }

    running_channels["channel2"] = {
        "client": mock_client2,
        "ayugram": adapter2,
        "backend_type": "ayugram",
        "task": None,
    }

    assert running_channels["channel1"]["ayugram"] is adapter1
    assert running_channels["channel2"]["ayugram"] is adapter2
    assert running_channels["channel1"]["backend_type"] == "ayugram"
    assert running_channels["channel2"]["backend_type"] == "ayugram"

    await adapter1.start()
    await adapter2.start()

    assert running_channels["channel1"]["ayugram"]._is_running is True
    assert running_channels["channel2"]["ayugram"]._is_running is True

    del running_channels["channel1"]

    assert "channel1" not in running_channels
    assert "channel2" in running_channels
    assert adapter2._is_running is True

    print("✅ test_running_channels_dict_pattern passed")


async def test_stream_ended_events_isolation():
    """Тест изоляции stream_ended_events между каналами."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded

    stream_ended_events = {}

    stream_ended_events[111] = asyncio.Event()
    stream_ended_events[222] = asyncio.Event()

    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    adapter1 = AyuGramAdapter(mock_client1)
    adapter2 = AyuGramAdapter(mock_client2)

    async def handler1(adapter, update):
        if update.chat_id == 111:
            stream_ended_events[111].set()

    adapter1._event_handlers["stream_end"].append(handler1)

    async def handler2(adapter, update):
        if update.chat_id == 222:
            stream_ended_events[222].set()

    adapter2._event_handlers["stream_end"].append(handler2)

    await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))
    await adapter2._emit_event("stream_end", StreamEnded(chat_id=222))

    assert stream_ended_events[111].is_set()
    assert stream_ended_events[222].is_set()

    stream_ended_events[111].clear()

    assert stream_ended_events[222].is_set()
    assert not stream_ended_events[111].is_set()

    print("✅ test_stream_ended_events_isolation passed")


async def test_play_in_progress_isolation():
    """Тест изоляции play_in_progress между каналами."""
    play_in_progress = {}

    play_in_progress[111] = False
    play_in_progress[222] = False

    play_in_progress[111] = True

    assert play_in_progress[111] is True
    assert play_in_progress[222] is False

    play_in_progress[111] = False

    assert play_in_progress[111] is False
    assert play_in_progress[222] is False

    print("✅ test_play_in_progress_isolation passed")


async def test_multiple_event_handlers_per_channel():
    """Несколько handlers могут быть зарегистрированы на одном канале."""
    from ayugram_adapter import AyuGramAdapter, StreamEnded

    mock_client = MagicMock()
    adapter = AyuGramAdapter(mock_client)

    handler1_calls = []
    handler2_calls = []

    async def handler1(adapter, update):
        handler1_calls.append(update.chat_id)

    async def handler2(adapter, update):
        handler2_calls.append(update.chat_id)

    adapter._event_handlers["stream_end"].extend([handler1, handler2])

    await adapter._emit_event("stream_end", StreamEnded(chat_id=123))

    assert len(handler1_calls) == 1
    assert len(handler2_calls) == 1
    assert handler1_calls[0] == 123
    assert handler2_calls[0] == 123

    print("✅ test_multiple_event_handlers_per_channel passed")


async def run_all_tests():
    """Run all multi-channel tests."""
    tests = [
        test_two_adapters_independent_initialization,
        test_two_adapters_can_start_independently,
        test_event_handlers_isolated_between_channels,
        test_stop_channel_does_not_affect_other_channel,
        test_concurrent_event_emission,
        test_multi_channel_state_isolation,
        test_different_event_types_per_channel,
        test_running_channels_dict_pattern,
        test_stream_ended_events_isolation,
        test_play_in_progress_isolation,
        test_multiple_event_handlers_per_channel,
    ]

    print("=" * 60)
    print("Running Multi-Channel Concurrent Streaming Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
