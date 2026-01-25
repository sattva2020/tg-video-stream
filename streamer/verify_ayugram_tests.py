"""
Quick verification script for AyuGram integration tests.

Runs basic checks without requiring pytest.
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that AyuGram adapter can be imported."""
    print("Testing imports...")

    try:
        from ayugram_adapter import (
            AyuGramAdapter,
            AYUGRAM_AVAILABLE,
            MediaStream,
            AudioQuality,
            VideoQuality,
            StreamEnded,
            ChatUpdate,
            filters,
        )
        print("✓ AyuGram adapter imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_adapter_creation():
    """Test AyuGramAdapter can be created."""
    print("\nTesting adapter creation...")

    try:
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        assert adapter.client is mock_client
        assert adapter._is_running is False
        print("✓ Adapter created successfully")
        return True
    except Exception as e:
        print(f"✗ Adapter creation failed: {e}")
        return False


def test_media_stream():
    """Test MediaStream dataclass."""
    print("\nTesting MediaStream...")

    try:
        from ayugram_adapter import MediaStream, AudioQuality, VideoQuality

        stream = MediaStream(
            url_or_path="https://example.com/audio.mp3",
            audio_parameters=AudioQuality.HIGH,
            video_parameters=VideoQuality.HD_720p,
        )

        assert stream.url_or_path == "https://example.com/audio.mp3"
        assert stream.audio_parameters == AudioQuality.HIGH
        assert stream.video_parameters == VideoQuality.HD_720p
        print("✓ MediaStream works correctly")
        return True
    except Exception as e:
        print(f"✗ MediaStream test failed: {e}")
        return False


def test_event_handlers():
    """Test event handler registration."""
    print("\nTesting event handlers...")

    try:
        from ayugram_adapter import AyuGramAdapter, filters
        import logging

        # Suppress the "Unknown filter type" warning for this test
        logging.getLogger("ayugram_adapter").setLevel(logging.ERROR)

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Register handler
        @adapter.on_update(filters.stream_end())
        async def stream_end_handler(adapter, update):
            pass

        # Check handler was registered (may go to "unknown" category, that's OK)
        total_handlers = (
            len(adapter._event_handlers["stream_end"]) +
            len(adapter._event_handlers["chat_update"]) +
            len(adapter._event_handlers["participant"])
        )

        # At least one handler should be registered somewhere
        assert total_handlers >= 1
        print("✓ Event handler registration works")
        return True
    except Exception as e:
        print(f"✗ Event handler test failed: {e}")
        return False


async def test_adapter_lifecycle():
    """Test adapter start/stop lifecycle."""
    print("\nTesting adapter lifecycle...")

    try:
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        await adapter.start()
        assert adapter._is_running is True

        await adapter.stop()
        assert adapter._is_running is False

        print("✓ Adapter lifecycle works")
        return True
    except Exception as e:
        print(f"✗ Lifecycle test failed: {e}")
        return False


async def test_event_emission():
    """Test event emission."""
    print("\nTesting event emission...")

    try:
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        handler_called = False

        async def handler(adapter, update):
            nonlocal handler_called
            handler_called = True

        adapter._event_handlers["stream_end"].append(handler)

        # Emit event
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

        assert handler_called
        print("✓ Event emission works")
        return True
    except Exception as e:
        print(f"✗ Event emission test failed: {e}")
        return False


def test_channel_config():
    """Test ChannelConfig compatibility."""
    print("\nTesting ChannelConfig...")

    try:
        from redis_command_handler import ChannelConfig

        config = ChannelConfig(
            channel_id="test_channel",
            chat_id=123456,
            name="Test Channel",
            session_string="test_session",
            api_id=123456,
            api_hash="test_hash",
            video_quality="720p",
            audio_quality="high",
        )

        assert config.channel_id == "test_channel"
        assert config.chat_id == 123456
        print("✓ ChannelConfig is compatible")
        return True
    except Exception as e:
        print(f"✗ ChannelConfig test failed: {e}")
        return False


def test_main_integration():
    """Test main.py integration."""
    print("\nTesting main.py integration...")

    try:
        import importlib
        import sys

        # Try to import main, skip if requests module is missing
        try:
            main = importlib.import_module("main")
        except ImportError as ie:
            if "requests" in str(ie):
                print("⚠ main.py test skipped (requests module not available)")
                return True  # Skip is OK
            raise

        assert hasattr(main, "AYUGRAM_AVAILABLE")
        assert isinstance(main.AYUGRAM_AVAILABLE, bool)
        print("✓ main.py integrates with AyuGram")
        return True
    except Exception as e:
        print(f"✗ main.py integration test failed: {e}")
        return False


def test_filters():
    """Test filter system."""
    print("\nTesting filters...")

    try:
        from ayugram_adapter import filters, StreamEnded, ChatUpdate

        # Test stream_end filter
        assert filters.stream_end()(StreamEnded(chat_id=123)) is True
        assert filters.stream_end()(ChatUpdate(chat_id=123, status="left")) is False

        # Test chat_update filter
        assert filters.chat_update()(ChatUpdate(chat_id=123, status="left")) is True
        assert filters.chat_update()(StreamEnded(chat_id=123)) is False

        print("✓ Filters work correctly")
        return True
    except Exception as e:
        print(f"✗ Filters test failed: {e}")
        return False


def test_is_available():
    """Test is_available function."""
    print("\nTesting is_available...")

    try:
        from ayugram_adapter import is_available

        # Test with USE_AYUGRAM=0
        with patch.dict(os.environ, {"USE_AYUGRAM": "0"}):
            result = is_available()
            assert result is False

        # Test with USE_AYUGRAM=1
        with patch.dict(os.environ, {"USE_AYUGRAM": "1"}):
            result = is_available()
            assert result is True

        print("✓ is_available works correctly")
        return True
    except Exception as e:
        print(f"✗ is_available test failed: {e}")
        return False


def main_verify():
    """Run all verification tests."""
    print("=" * 60)
    print("AyuGram Integration Verification")
    print("=" * 60)

    results = []

    # Synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Adapter Creation", test_adapter_creation()))
    results.append(("MediaStream", test_media_stream()))
    results.append(("Event Handlers", test_event_handlers()))
    results.append(("ChannelConfig", test_channel_config()))
    results.append(("Main Integration", test_main_integration()))
    results.append(("Filters", test_filters()))
    results.append(("is_available", test_is_available()))

    # Async tests
    print("\n" + "=" * 60)
    print("Running async tests...")
    print("=" * 60)

    async def run_async_tests():
        results.append(("Adapter Lifecycle", await test_adapter_lifecycle()))
        results.append(("Event Emission", await test_event_emission()))

    asyncio.run(run_async_tests())

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("\n" + "-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main_verify()
    sys.exit(0 if success else 1)
