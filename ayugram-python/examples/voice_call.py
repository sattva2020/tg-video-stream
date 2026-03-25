"""
Voice Call Stream Control Example for AyuGram Python SDK

This example demonstrates advanced voice call stream control:
1. Joining a voice chat with audio/video stream
2. Stream position control (seek, rewind, forward)
3. Volume control
4. Playback speed control
5. Pause/Resume operations
6. Stream state monitoring
7. Leaving the call

Requirements:
    - Python 3.8+
    - ayugram-python SDK installed
    - Pyrogram installed (pip install pyrogram)

Usage:
    # Demo mode (no credentials required):
    python voice_call.py

    # Real mode (requires API credentials):
    export API_ID="your_api_id"
    export API_HASH="your_api_hash"
    export CHAT_ID="-1001234567890"
    export DEMO_MODE="false"
    python voice_call.py

Environment Variables:
    API_ID: Your Telegram API ID
    API_HASH: Your Telegram API hash
    SESSION_STRING: Your Pyrogram session string (optional)
    CHAT_ID: Target chat ID for voice chat
    DEMO_MODE: Set to "false" to use real credentials
    AUDIO_URL: Audio stream URL (default: test MP3)

Note: This example requires a running AyuGram JSON-RPC server or mock server.
For testing purposes, you can use the mock server from tests/mock_server.py.
"""

import asyncio
import logging
import os
import sys
from typing import Optional
from unittest.mock import MagicMock, AsyncMock

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to import Pyrogram
try:
    from pyrogram import Client
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    Client = None  # type: ignore

from ayugram import AyuGramClient, AudioPiped, AudioVideoPiped
from ayugram.exceptions import AyuGramError, CallError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("voice_call_example")


def create_mock_pyrogram_client():
    """
    Create a mock Pyrogram client for demonstration.

    In production, you would use a real Pyrogram Client instance.
    This mock allows the example to run without API credentials.
    """
    if not PYROGRAM_AVAILABLE:
        logger.warning("Pyrogram is not installed. Mock client requires Pyrogram.")
        logger.info("Install with: pip install pyrogram")
        return None

    # Create a mock that passes isinstance() checks
    from pyrogram import Client
    mock_client = MagicMock(spec=Client)
    mock_client.start = AsyncMock(return_value=None)
    mock_client.stop = AsyncMock(return_value=None)
    mock_client.idle = AsyncMock(return_value=None)
    mock_client.name = "demo_client"
    return mock_client


def create_pyrogram_client():
    """
    Create a real Pyrogram client with environment configuration.

    Reads credentials from environment variables:
    - API_ID: Telegram API ID
    - API_HASH: Telegram API hash
    - SESSION_STRING: Optional session string

    Returns:
        Pyrogram Client instance or None if credentials missing
    """
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    session_string = os.getenv("SESSION_STRING", "")

    if not api_id or not api_hash:
        return None

    return Client(
        name="ayugram_voice_call",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string or None,
        in_memory=True
    )


async def example_basic_stream_control():
    """
    Example 1: Basic stream control operations.

    Demonstrates:
    - Joining a voice chat
    - Pause/Resume playback
    - Leaving the call
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 1: Basic Stream Control")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing code pattern:")
        logger.info("""
# Step 1: Create Pyrogram client
from pyrogram import Client
from ayugram import AyuGramClient, AudioPiped

app = Client("my_account", api_id=123, api_hash="abc")
client = AyuGramClient(app)

# Step 2: Start client and join voice chat
await client.start()
stream = AudioPiped("https://example.com/audio.mp3")
await client.join_group_call(chat_id, stream)

# Step 3: Control playback
await client.pause(chat_id)      # Pause playback
await client.resume(chat_id)     # Resume playback

# Step 4: Leave call and stop
await client.leave_group_call(chat_id)
await client.stop()
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available. Install with: pip install pyrogram")
        logger.info("Or run in demo mode with DEMO_MODE=true")
        return

    logger.info("\n🔧 REAL MODE - Using actual client...")
    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided (API_ID, API_HASH)")
        logger.info("Set environment variables:")
        logger.info("  export API_ID='your_api_id'")
        logger.info("  export API_HASH='your_api_hash'")
        logger.info("Or run in demo mode with DEMO_MODE=true")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

    try:
        # Initialize and start client
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat
        stream = AudioPiped(audio_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat: {chat_id}")

        # Pause playback
        logger.info("\n⏸️  Pausing playback...")
        await client.pause(chat_id)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  State: playing={state.is_playing}, paused={state.is_paused}")
        await asyncio.sleep(2)

        # Resume playback
        logger.info("\n▶️  Resuming playback...")
        await client.resume(chat_id)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  State: playing={state.is_playing}, paused={state.is_paused}")
        await asyncio.sleep(3)

        # Leave call
        logger.info("\n📞 Leaving voice chat...")
        await client.leave_group_call(chat_id)
        logger.info("✓ Left voice chat")

        # Stop client
        await client.stop()
        logger.info("✓ Client stopped")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def example_seek_operations():
    """
    Example 2: Stream position control (seek operations).

    Demonstrates:
    - seek_stream: Jump to specific position
    - rewind_stream: Go back N seconds
    - forward_stream: Skip forward N seconds
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Stream Position Control (Seek)")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing seek operations:")
        logger.info("""
# Seek to specific position (in seconds)
await client.seek_stream(chat_id, 60)  # Jump to 1 minute

# Rewind by N seconds
await client.rewind_stream(chat_id, 10)  # Go back 10 seconds

# Forward by N seconds
await client.forward_stream(chat_id, 30)  # Skip forward 30 seconds

# Get current position
position = client.get_position(chat_id)  # Returns position in seconds
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available")
        return

    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

    try:
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat
        stream = AudioPiped(audio_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat: {chat_id}")

        # Monitor initial position
        initial_pos = client.get_position(chat_id)
        logger.info(f"\n📍 Initial position: {initial_pos}s")

        # Seek to 30 seconds
        logger.info("\n⏩ Seeking to 30 seconds...")
        await client.seek_stream(chat_id, 30)
        pos = client.get_position(chat_id)
        logger.info(f"  Position after seek: {pos}s")
        await asyncio.sleep(2)

        # Rewind 10 seconds
        logger.info("\n⏪ Rewinding 10 seconds...")
        await client.rewind_stream(chat_id, 10)
        pos = client.get_position(chat_id)
        logger.info(f"  Position after rewind: {pos}s")
        await asyncio.sleep(2)

        # Forward 20 seconds
        logger.info("\n⏩ Forwarding 20 seconds...")
        await client.forward_stream(chat_id, 20)
        pos = client.get_position(chat_id)
        logger.info(f"  Position after forward: {pos}s")

        # Cleanup
        await client.leave_group_call(chat_id)
        await client.stop()
        logger.info("✓ Example completed")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def example_volume_control():
    """
    Example 3: Volume control operations.

    Demonstrates:
    - set_volume: Set volume level (0-100 or 0.0-1.0)
    - get_volume: Get current volume level
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Volume Control")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing volume control:")
        logger.info("""
# Set volume using 0-100 range (user-friendly)
await client.set_volume(chat_id, 50)   # 50% volume
await client.set_volume(chat_id, 75)   # 75% volume

# Or use 0.0-1.0 range (normalized)
await client.set_volume(chat_id, 0.5)  # Also 50% volume

# Get current volume
volume = client.get_volume(chat_id)  # Returns 0.0-1.0
print(f"Volume: {volume * 100:.0f}%")

# Mute (set to 0)
await client.set_volume(chat_id, 0)

# Full volume (100%)
await client.set_volume(chat_id, 100)
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available")
        return

    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

    try:
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat
        stream = AudioPiped(audio_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat: {chat_id}")

        # Get initial volume
        initial_volume = client.get_volume(chat_id)
        logger.info(f"\n🔊 Initial volume: {initial_volume * 100:.0f}%")

        # Set volume to 50%
        logger.info("\n🔉 Setting volume to 50%...")
        await client.set_volume(chat_id, 50)
        vol = client.get_volume(chat_id)
        logger.info(f"  Current volume: {vol * 100:.0f}%")
        await asyncio.sleep(2)

        # Set volume to 75%
        logger.info("\n🔊 Setting volume to 75%...")
        await client.set_volume(chat_id, 75)
        vol = client.get_volume(chat_id)
        logger.info(f"  Current volume: {vol * 100:.0f}%")
        await asyncio.sleep(2)

        # Mute (0%)
        logger.info("\n🔇 Muting (0%)...")
        await client.set_volume(chat_id, 0)
        vol = client.get_volume(chat_id)
        logger.info(f"  Current volume: {vol * 100:.0f}%")
        await asyncio.sleep(2)

        # Full volume (100%)
        logger.info("\n🔊 Setting to full volume (100%)...")
        await client.set_volume(chat_id, 100)
        vol = client.get_volume(chat_id)
        logger.info(f"  Current volume: {vol * 100:.0f}%")

        # Cleanup
        await client.leave_group_call(chat_id)
        await client.stop()
        logger.info("✓ Example completed")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def example_speed_control():
    """
    Example 4: Playback speed control.

    Demonstrates:
    - set_speed: Set playback speed (0.5x to 2.0x)
    - Stream state monitoring with speed
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Playback Speed Control")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing speed control:")
        logger.info("""
# Set playback speed (0.5x to 2.0x)
await client.set_speed(chat_id, 1.5)  # 1.5x speed
await client.set_speed(chat_id, 0.75) # 0.75x speed (slower)

# Normal speed
await client.set_speed(chat_id, 1.0)  # 1.0x (normal)

# Double speed (fast)
await client.set_speed(chat_id, 2.0)  # 2.0x (fastest)

# Half speed (slow)
await client.set_speed(chat_id, 0.5)  # 0.5x (slowest)

# Get stream state (includes speed)
state = client.get_stream_state(chat_id)
print(f"Speed: {state.speed}x")
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available")
        return

    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

    try:
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat
        stream = AudioPiped(audio_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat: {chat_id}")

        # Get initial state
        state = client.get_stream_state(chat_id)
        initial_speed = state.speed if state else 1.0
        logger.info(f"\n⚡ Initial speed: {initial_speed}x")

        # Set to 1.5x speed
        logger.info("\n⏩ Setting speed to 1.5x...")
        await client.set_speed(chat_id, 1.5)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  Current speed: {state.speed}x")
        await asyncio.sleep(3)

        # Set to 0.75x speed (slower)
        logger.info("\n⏪ Setting speed to 0.75x...")
        await client.set_speed(chat_id, 0.75)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  Current speed: {state.speed}x")
        await asyncio.sleep(3)

        # Reset to normal speed
        logger.info("\n⚡ Resetting to normal speed (1.0x)...")
        await client.set_speed(chat_id, 1.0)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  Current speed: {state.speed}x")

        # Cleanup
        await client.leave_group_call(chat_id)
        await client.stop()
        logger.info("✓ Example completed")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def example_stream_state_monitoring():
    """
    Example 5: Comprehensive stream state monitoring.

    Demonstrates:
    - get_stream_state: Get complete stream state
    - Monitoring position, volume, speed, and playback status
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Stream State Monitoring")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing state monitoring:")
        logger.info("""
# Get complete stream state
state = client.get_stream_state(chat_id)

if state:
    print(f"Position: {state.position_ms // 1000}s")
    print(f"Duration: {state.duration_ms // 1000}s")
    print(f"Playing: {state.is_playing}")
    print(f"Paused: {state.is_paused}")
    print(f"Volume: {state.volume * 100:.0f}%")
    print(f"Speed: {state.speed}x")
    print(f"Updated: {state.updated_at}")

# Individual getters
position = client.get_position(chat_id)      # Current position in seconds
volume = client.get_volume(chat_id)          # Volume (0.0-1.0)
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available")
        return

    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

    try:
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat
        stream = AudioPiped(audio_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat: {chat_id}")

        # Monitor stream state
        logger.info("\n📊 Current Stream State:")
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  Position: {state.position_ms // 1000}s")
            logger.info(f"  Duration: {state.duration_ms // 1000}s")
            logger.info(f"  Playing: {state.is_playing}")
            logger.info(f"  Paused: {state.is_paused}")
            logger.info(f"  Volume: {state.volume * 100:.0f}%")
            logger.info(f"  Speed: {state.speed}x")
            logger.info(f"  Updated: {state.updated_at}")
        else:
            logger.info("  No state available")

        # Make some changes and monitor
        logger.info("\n🔧 Modifying stream parameters...")

        await client.set_volume(chat_id, 60)
        await client.set_speed(chat_id, 1.25)
        await client.seek_stream(chat_id, 45)

        logger.info("\n📊 Updated Stream State:")
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"  Position: {state.position_ms // 1000}s")
            logger.info(f"  Volume: {state.volume * 100:.0f}%")
            logger.info(f"  Speed: {state.speed}x")

        # Cleanup
        await client.leave_group_call(chat_id)
        await client.stop()
        logger.info("✓ Example completed")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def example_video_stream_control():
    """
    Example 6: Video stream with audio control.

    Demonstrates stream control with AudioVideoPiped.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 6: Video Stream Control")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing video stream control:")
        logger.info("""
# Video stream works the same as audio
from ayugram import AudioVideoPiped

stream = AudioVideoPiped("https://example.com/video.mp4")
await client.join_group_call(chat_id, stream)

# All stream controls work the same:
await client.pause(chat_id)
await client.resume(chat_id)
await client.set_volume(chat_id, 75)
await client.seek_stream(chat_id, 120)
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available")
        return

    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided")
        return

    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    # Use a test video URL
    video_url = os.getenv("VIDEO_URL", "https://www.w3schools.com/html/mov_bbb.mp4")

    try:
        client = AyuGramClient(app)
        await client.start()
        logger.info("✓ Client started")

        # Join voice chat with video
        stream = AudioVideoPiped(video_url)
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Joined voice chat with video: {chat_id}")

        # Control video playback
        logger.info("\n⏸️  Pausing video playback...")
        await client.pause(chat_id)
        await asyncio.sleep(2)

        logger.info("\n▶️  Resuming video playback...")
        await client.resume(chat_id)
        await asyncio.sleep(2)

        logger.info("\n🔊 Setting volume to 80%...")
        await client.set_volume(chat_id, 80)

        # Cleanup
        await client.leave_group_call(chat_id)
        await client.stop()
        logger.info("✓ Example completed")

    except AyuGramError as e:
        logger.error(f"✗ Error: {e}")
        try:
            await client.stop()
        except:
            pass


async def main():
    """
    Main entry point running all voice call stream control examples.
    """
    logger.info("\n" + "=" * 70)
    logger.info("AyuGram Python SDK - Voice Call Stream Control Examples")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n🎭 DEMO MODE")
        logger.info("Showing code patterns without requiring real AyuGram server")
        logger.info("\nTo run with real server:")
        logger.info("  1. Install Pyrogram: pip install pyrogram")
        logger.info("  2. Set DEMO_MODE=false")
        logger.info("  3. Set API_ID and API_HASH environment variables")
        logger.info("  4. Set CHAT_ID to your target voice chat")
    else:
        logger.info("\n🔧 REAL MODE")
        logger.info("Using actual Pyrogram client and AyuGram SDK")
        logger.info("  Make sure AyuGram JSON-RPC server is running")

    try:
        # Run all examples
        await example_basic_stream_control()
        await asyncio.sleep(0.5)

        await example_seek_operations()
        await asyncio.sleep(0.5)

        await example_volume_control()
        await asyncio.sleep(0.5)

        await example_speed_control()
        await asyncio.sleep(0.5)

        await example_stream_state_monitoring()
        await asyncio.sleep(0.5)

        await example_video_stream_control()

        logger.info("\n" + "=" * 70)
        logger.info("✓ All voice call stream control examples completed!")
        logger.info("=" * 70)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Example interrupted by user")
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """
    Run the voice call stream control examples.

    This demonstrates:
    - Basic stream control (pause/resume)
    - Stream position control (seek, rewind, forward)
    - Volume control
    - Playback speed control
    - Stream state monitoring
    - Video stream control
    """
    asyncio.run(main())
