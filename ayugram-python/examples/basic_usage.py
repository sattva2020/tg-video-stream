"""
Basic Usage Example for AyuGram Python SDK

This example demonstrates the basic usage of the AyuGram Python SDK:
1. Client initialization with Pyrogram
2. Starting the client
3. Joining a voice chat with an audio stream
4. Controlling playback (pause/resume)
5. Leaving the call and stopping the client

Requirements:
    - Python 3.8+
    - ayugram-python SDK installed
    - Pyrogram installed (pip install pyrogram)

Usage:
    # Demo mode (no credentials required):
    python basic_usage.py

    # Real mode (requires API credentials):
    export API_ID="your_api_id"
    export API_HASH="your_api_hash"
    export CHAT_ID="-1001234567890"
    python basic_usage.py

Environment Variables:
    API_ID: Your Telegram API ID
    API_HASH: Your Telegram API hash
    SESSION_STRING: Your Pyrogram session string (optional)
    CHAT_ID: Target chat ID for voice chat
    DEMO_MODE: Set to "false" to use real credentials

Note: This example requires a running AyuGram JSON-RPC server or mock server.
For testing purposes, you can use the mock server from tests/mock_server.py.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock, AsyncMock
from typing import Optional

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to import Pyrogram
try:
    from pyrogram import Client
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    Client = None  # type: ignore

from ayugram import AyuGramClient, AudioPiped
from ayugram.exceptions import AyuGramError, CallError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("basic_usage_example")

def create_mock_pyrogram_client():
    """
    Create a mock Pyrogram client for demonstration.

    In production, you would use a real Pyrogram Client instance.
    This mock allows the example to run without API credentials.

    Note: This only works if Pyrogram is installed, even though we're
    using a mock. The AyuGramClient validates client types using isinstance().
    """
    if not PYROGRAM_AVAILABLE:
        logger.warning("Pyrogram is not installed. Mock client requires Pyrogram.")
        logger.info("Install with: pip install pyrogram")
        logger.info("Or install Tgcalls: pip install pyrogram tgcalls")
        return None

    # Create a mock that passes isinstance() checks
    # We need to mock the actual Client class, not just use MagicMock
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
        name="ayugram_example",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string or None,
        in_memory=True
    )


async def main():
    """
    Main example demonstrating basic AyuGram SDK usage.

    This function shows the complete lifecycle of an AyuGram client:
    1. Initialize the client
    2. Start the client
    3. Join a voice chat
    4. Control playback
    5. Leave the call
    6. Stop the client
    """
    # Configuration
    chat_id = int(os.getenv("CHAT_ID", "-1001234567890"))
    audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    logger.info("=" * 60)
    logger.info("AyuGram Python SDK - Basic Usage Example")
    logger.info("=" * 60)

    # ========================================================================
    # STEP 1: Initialize the client
    # ========================================================================
    logger.info("\n[Step 1] Initializing AyuGram client...")

    # Try to create real client if not in demo mode
    app = None
    if demo_mode:
        logger.info("Running in DEMO mode (showing code pattern)")
        logger.info("To run with real client:")
        logger.info("  1. Install Pyrogram: pip install pyrogram")
        logger.info("  2. Set DEMO_MODE=false")
        logger.info("  3. Set API_ID and API_HASH environment variables")
        logger.info("\nDemonstrating code pattern without actual execution...")

        # Show what the code would look like
        logger.info("\n" + "=" * 60)
        logger.info("CODE PATTERN:")
        logger.info("=" * 60)
        logger.info("""
# Step 1: Create Pyrogram client
from pyrogram import Client
app = Client(
    name="my_account",
    api_id=your_api_id,
    api_hash=your_api_hash
)

# Step 2: Initialize AyuGram client
from ayugram import AyuGramClient, AudioPiped
client = AyuGramClient(app)

# Step 3: Start the client
await client.start()

# Step 4: Join voice chat
stream = AudioPiped("https://example.com/audio.mp3")
await client.join_group_call(chat_id, stream)

# Step 5: Control playback
await client.pause(chat_id)
await client.resume(chat_id)

# Step 6: Leave call and stop
await client.leave_group_call(chat_id)
await client.stop()
""")
        logger.info("=" * 60)

        return  # Exit early in demo mode

    # Real mode (requires Pyrogram)
    if not PYROGRAM_AVAILABLE:
        logger.error("Pyrogram not available. Install with: pip install pyrogram")
        logger.info("Or run in demo mode with DEMO_MODE=true")
        return

    logger.info("Running in REAL mode (using Pyrogram client)")
    app = create_pyrogram_client()
    if app is None:
        logger.error("API credentials not provided (API_ID, API_HASH)")
        logger.info("Set environment variables:")
        logger.info("  export API_ID='your_api_id'")
        logger.info("  export API_HASH='your_api_hash'")
        logger.info("Or run in demo mode with DEMO_MODE=true")
        return

    # Initialize AyuGram client
    try:
        client = AyuGramClient(app)
        logger.info("✓ Client initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize client: {e}")
        return

    # ========================================================================
    # STEP 2: Start the client
    # ========================================================================
    logger.info("\n[Step 2] Starting client...")

    try:
        await client.start()
        logger.info("✓ Client started successfully")
    except AyuGramError as e:
        logger.error(f"✗ Failed to start client: {e}")
        return

    # ========================================================================
    # STEP 3: Create audio stream
    # ========================================================================
    logger.info("\n[Step 3] Creating audio stream...")

    stream = AudioPiped(audio_url)
    logger.info(f"✓ Audio stream created: {audio_url}")

    # ========================================================================
    # STEP 4: Join voice chat
    # ========================================================================
    logger.info("\n[Step 4] Joining voice chat...")

    try:
        await client.join_group_call(chat_id, stream)
        logger.info(f"✓ Successfully joined voice chat: {chat_id}")
    except CallError as e:
        logger.error(f"✗ Failed to join voice chat: {e}")
        await client.stop()
        return

    # ========================================================================
    # STEP 5: Monitor playback
    # ========================================================================
    logger.info("\n[Step 5] Monitoring playback for 5 seconds...")

    try:
        # Check stream state
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"✓ Stream state: playing={state.is_playing}, paused={state.is_paused}")
        else:
            logger.info("✓ Stream joined (state not available in demo mode)")

        # Simulate playback monitoring
        await asyncio.sleep(2)

        # ====================================================================
        # STEP 6: Pause playback
        # ====================================================================
        logger.info("\n[Step 6] Pausing playback...")

        await client.pause(chat_id)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"✓ Playback paused: playing={state.is_playing}, paused={state.is_paused}")
        else:
            logger.info("✓ Playback paused")

        await asyncio.sleep(1)

        # ====================================================================
        # STEP 7: Resume playback
        # ====================================================================
        logger.info("\n[Step 7] Resuming playback...")

        await client.resume(chat_id)
        state = client.get_stream_state(chat_id)
        if state:
            logger.info(f"✓ Playback resumed: playing={state.is_playing}, paused={state.is_paused}")
        else:
            logger.info("✓ Playback resumed")

        await asyncio.sleep(2)

    except CallError as e:
        logger.error(f"✗ Playback control error: {e}")

    # ========================================================================
    # STEP 8: Leave voice chat
    # ========================================================================
    logger.info("\n[Step 8] Leaving voice chat...")

    try:
        await client.leave_group_call(chat_id)
        logger.info("✓ Successfully left voice chat")
    except CallError as e:
        logger.error(f"✗ Failed to leave voice chat: {e}")

    # ========================================================================
    # STEP 9: Stop the client
    # ========================================================================
    logger.info("\n[Step 9] Stopping client...")

    try:
        await client.stop()
        logger.info("✓ Client stopped successfully")
    except AyuGramError as e:
        logger.error(f"✗ Failed to stop client: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("Example completed successfully!")
    logger.info("=" * 60)


async def example_with_event_handling():
    """
    Advanced example demonstrating event handling.

    Shows how to register event listeners for call lifecycle events.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Advanced Example - Event Handling")
    logger.info("=" * 60)

    if not PYROGRAM_AVAILABLE:
        logger.info("Event handling code pattern:")
        logger.info("""
# Register event listeners
async def on_call_joined(chat_id: int):
    print(f"Joined call: {chat_id}")

async def on_call_left(chat_id: int):
    print(f"Left call: {chat_id}")

client.on('call_joined', on_call_joined)
client.on('call_left', on_call_left)

# Events will be automatically triggered
await client.join_group_call(chat_id, stream)  # Triggers 'call_joined'
await client.leave_group_call(chat_id)         # Triggers 'call_left'
""")
        return

    # Event callbacks
    async def on_call_joined(chat_id: int):
        logger.info(f"🎉 Event: Call joined for chat {chat_id}")

    async def on_call_left(chat_id: int):
        logger.info(f"👋 Event: Call left for chat {chat_id}")

    # Initialize client
    app = create_pyrogram_client()
    if app is None:
        logger.warning("Skipping event handling demo (no API credentials)")
        return

    client = AyuGramClient(app)

    # Register event listeners
    client.on('call_joined', on_call_joined)
    client.on('call_left', on_call_left)

    logger.info("✓ Event listeners registered")

    # Start client
    await client.start()

    # Join and leave to trigger events
    chat_id = -1001234567890
    stream = AudioPiped("https://example.com/audio.mp3")

    try:
        await client.join_group_call(chat_id, stream)
        await asyncio.sleep(1)
        await client.leave_group_call(chat_id)
    except AyuGramError as e:
        logger.error(f"Error: {e}")
    finally:
        await client.stop()

    logger.info("✓ Event handling example completed")


async def run_all_examples():
    """Run all examples in sequence."""
    try:
        # Run basic example
        await main()

        # Small delay between examples
        await asyncio.sleep(1)

        # Run event handling example
        await example_with_event_handling()

    except KeyboardInterrupt:
        logger.info("\n⚠ Example interrupted by user")
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """
    Run the basic usage example.

    This will demonstrate:
    - Client initialization and lifecycle
    - Joining/leaving voice chats
    - Playback control (pause/resume)
    - Event handling
    """
    asyncio.run(run_all_examples())
