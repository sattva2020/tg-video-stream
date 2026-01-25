"""
Simple test script for play, pause, and resume methods.

This script tests the playback control functionality with minimal dependencies.
"""

import asyncio
import logging
import sys
from unittest.mock import MagicMock, AsyncMock

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_playback_control():
    """Test play, pause, and resume methods."""
    # We need to mock Pyrogram before importing AyuGramClient
    import ayugram.client

    # Save original values
    original_pyrogram_available = ayugram.client.PYROGRAM_AVAILABLE
    original_pyrogram_client = ayugram.client.PyrogramClient

    try:
        # Create a mock Pyrogram client class
        class MockPyrogramClient:
            def __init__(self, *args, **kwargs):
                self._started = False

            async def start(self):
                self._started = True

            async def stop(self):
                self._started = False

            async def idle(self):
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    pass

        # Monkey-patch the module
        ayugram.client.PYROGRAM_AVAILABLE = True
        ayugram.client.PyrogramClient = MockPyrogramClient

        # Now import AyuGramClient
        from ayugram import AyuGramClient
        from ayugram.types import AudioPiped

        print("\n=== Testing Playback Control ===\n")

        # Create mock app
        mock_app = MockPyrogramClient()

        # Create AyuGram client
        client = AyuGramClient(mock_app)

        # Create test stream
        test_stream = AudioPiped("https://example.com/audio.mp3")
        test_chat_id = -1001234567890

        try:
            # Test 1: Start client
            print("Test 1: Starting client...")
            await client.start()
            assert client.is_started, "Client should be started"
            print("✓ Client started successfully\n")

            # Test 2: Join group call
            print("Test 2: Joining group call...")
            await client.join_group_call(test_chat_id, test_stream)
            assert str(test_chat_id) in client.active_calls, "Should have active call"
            print(f"✓ Joined group call for chat_id={test_chat_id}\n")

            # Test 3: Play
            print("Test 3: Testing play...")
            await client.play(test_chat_id)
            playback_state = client._playback_states.get(str(test_chat_id))
            assert playback_state is not None, "Should have playback state"
            assert playback_state["is_playing"] is True, "Should be playing"
            assert playback_state["is_paused"] is False, "Should not be paused"
            print("✓ Play successful\n")

            # Test 4: Pause
            print("Test 4: Testing pause...")
            await client.pause(test_chat_id)
            playback_state = client._playback_states.get(str(test_chat_id))
            assert playback_state is not None, "Should have playback state"
            assert playback_state["is_playing"] is False, "Should not be playing"
            assert playback_state["is_paused"] is True, "Should be paused"
            print("✓ Pause successful\n")

            # Test 5: Resume
            print("Test 5: Testing resume...")
            await client.resume(test_chat_id)
            playback_state = client._playback_states.get(str(test_chat_id))
            assert playback_state is not None, "Should have playback state"
            assert playback_state["is_playing"] is True, "Should be playing"
            assert playback_state["is_paused"] is False, "Should not be paused"
            print("✓ Resume successful\n")

            # Test 6: Play again (ensure it doesn't break)
            print("Test 6: Testing play again...")
            await client.play(test_chat_id)
            playback_state = client._playback_states.get(str(test_chat_id))
            assert playback_state["is_playing"] is True, "Should still be playing"
            print("✓ Play again successful\n")

            # Test 7: Leave group call (cleanup)
            print("Test 7: Leaving group call...")
            await client.leave_group_call(test_chat_id)
            assert str(test_chat_id) not in client.active_calls, "Should not have active call"
            assert str(test_chat_id) not in client._playback_states, "Should not have playback state"
            print("✓ Left group call and cleaned up state\n")

            # Test 8: Error handling - play without active call
            print("Test 8: Testing error handling - play without active call...")
            try:
                await client.play(test_chat_id)
                print("✗ Should have raised CallError")
                return False
            except Exception as e:
                assert "call" in str(e).lower() or "active" in str(e).lower(), f"Expected CallError, got: {e}"
                print(f"✓ Correctly raised error: {type(e).__name__}\n")

            print("=== All Tests Passed! ===\n")
            return True

        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Cleanup
            if client.is_started:
                await client.stop()

    finally:
        # Restore original values
        ayugram.client.PYROGRAM_AVAILABLE = original_pyrogram_available
        ayugram.client.PyrogramClient = original_pyrogram_client


async def test_pause_resume_cycle():
    """Test multiple pause/resume cycles."""
    import ayugram.client

    # Save original values
    original_pyrogram_available = ayugram.client.PYROGRAM_AVAILABLE
    original_pyrogram_client = ayugram.client.PyrogramClient

    try:
        # Create a mock Pyrogram client class
        class MockPyrogramClient:
            def __init__(self, *args, **kwargs):
                self._started = False

            async def start(self):
                self._started = True

            async def stop(self):
                self._started = False

        # Monkey-patch the module
        ayugram.client.PYROGRAM_AVAILABLE = True
        ayugram.client.PyrogramClient = MockPyrogramClient

        from ayugram import AyuGramClient
        from ayugram.types import AudioPiped

        print("\n=== Testing Pause/Resume Cycles ===\n")

        mock_app = MockPyrogramClient()
        client = AyuGramClient(mock_app)
        test_stream = AudioPiped("https://example.com/audio.mp3")
        test_chat_id = -1001234567890

        try:
            await client.start()
            await client.join_group_call(test_chat_id, test_stream)

            # Perform multiple pause/resume cycles
            for i in range(3):
                print(f"Cycle {i+1}:")
                await client.pause(test_chat_id)
                state = client._playback_states[str(test_chat_id)]
                assert state["is_paused"] is True, f"Cycle {i+1}: Should be paused"
                print(f"  ✓ Paused")

                await client.resume(test_chat_id)
                state = client._playback_states[str(test_chat_id)]
                assert state["is_playing"] is True, f"Cycle {i+1}: Should be playing"
                print(f"  ✓ Resumed")

            print("\n=== Pause/Resume Cycles Passed! ===\n")
            return True

        except Exception as e:
            print(f"\n✗ Cycle test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if client.is_started:
                await client.stop()

    finally:
        # Restore original values
        ayugram.client.PYROGRAM_AVAILABLE = original_pyrogram_available
        ayugram.client.PyrogramClient = original_pyrogram_client


async def main():
    """Run all tests."""
    print("Starting playback control tests...\n")

    success = True

    # Run basic playback control tests
    if not await test_playback_control():
        success = False

    # Run pause/resume cycle tests
    if not await test_pause_resume_cycle():
        success = False

    if success:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
