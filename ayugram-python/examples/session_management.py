"""
Session Management Example for AyuGram Python SDK

This example demonstrates comprehensive session management functionality:
1. Creating sessions with phone number authentication (OTP flow)
2. Saving sessions to persistent storage
3. Loading existing sessions
4. Listing all available sessions
5. Deleting sessions
6. Session persistence verification
7. Error handling (invalid phone, invalid OTP, session corruption)
8. Optional Redis caching for faster access

Requirements:
    - Python 3.8+
    - ayugram-python SDK installed

Usage:
    # Demo mode (no credentials required):
    python session_management.py

    # Real mode (requires AyuGram JSON-RPC server):
    export AYUGRAM_ENGINE_URL="http://localhost:8080/jsonrpc"
    python session_management.py

Environment Variables:
    AYUGRAM_ENGINE_URL: AyuGram JSON-RPC server endpoint (default: http://localhost:8080/jsonrpc)
    SESSION_DIR: Directory for session files (default: ./sessions)
    REDIS_URL: Optional Redis URL for caching (default: None)
    DEMO_MODE: Set to "false" to use real AyuGram server

Note: This example can work with a mock AyuGram server for testing purposes.
The demo mode shows the code pattern without actual network operations.
"""

import asyncio
import logging
import os
import sys
import tempfile
from typing import Optional
from unittest.mock import MagicMock, AsyncMock

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ayugram.session import SessionManager
from ayugram.exceptions import AyuGramError, AuthenticationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("session_management_example")


async def example_create_session():
    """
    Example 1: Creating a new session with phone authentication.

    Demonstrates the complete authentication flow:
    1. Initialize SessionManager
    2. Request OTP code for phone number
    3. User enters OTP (via callback)
    4. Session created and saved
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 1: Creating a New Session with Phone Authentication")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing code pattern:")
        logger.info("""
# Step 1: Initialize SessionManager
from ayugram.session import SessionManager
manager = SessionManager("./sessions")

# Step 2: Define OTP callback
async def otp_callback():
    # In production, this would prompt user via bot/input
    code = input("Enter OTP code: ")
    return code

# Step 3: Create session (triggers OTP flow)
phone_number = "+1234567890"
session_data = await manager.create_session(phone_number, otp_callback)

# Step 4: Session is automatically saved
# Session data contains: phone, user_id, auth_key, timestamps
        """)
        logger.info("\n✓ Code pattern displayed")
        return

    # Real mode
    logger.info("\n🔧 REAL MODE - Creating actual session...")

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized with directory: {temp_dir}")

        # Mock OTP callback (in production, user would enter actual OTP)
        async def mock_otp_callback():
            logger.info("📱 OTP callback invoked")
            # In production: prompt user for actual OTP from Telegram
            # For demo: return a mock 5-digit code
            mock_code = "12345"
            logger.info(f"🔢 Using mock OTP code: {mock_code}")
            return mock_code

        phone_number = "+1234567890"
        logger.info(f"\n📞 Requesting OTP for phone: {phone_number}")

        try:
            # Create session (will send OTP via AyuGram, then call callback)
            session_data = await manager.create_session(phone_number, mock_otp_callback)

            logger.info("✓ Session created successfully!")
            logger.info(f"  Phone: {session_data.get('phone')}")
            logger.info(f"  User ID: {session_data.get('user_id')}")
            logger.info(f"  Created: {session_data.get('created_at')}")
            logger.info(f"  Last Used: {session_data.get('last_used')}")

            # Session is automatically saved
            logger.info("✓ Session automatically saved to disk")

        except AuthenticationError as e:
            logger.error(f"✗ Authentication failed: {e}")
        except AyuGramError as e:
            logger.error(f"✗ Session creation failed: {e}")


async def example_save_and_load():
    """
    Example 2: Saving and loading sessions manually.

    Demonstrates explicit session persistence and loading.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Saving and Loading Sessions")
    logger.info("=" * 70)

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized: {temp_dir}")

        # Create mock session data
        session_name = "my_account"
        session_data = {
            "phone": "+1234567890",
            "user_id": 123456789,
            "auth_key": "mock_auth_key_base64_encoded",
            "created_at": "2025-01-25T10:00:00Z",
            "last_used": "2025-01-25T10:00:00Z"
        }

        logger.info(f"\n💾 Saving session: {session_name}")
        await manager.save_session(session_name, session_data)
        logger.info("✓ Session saved to disk")

        logger.info(f"\n📂 Loading session: {session_name}")
        loaded_data = await manager.load_session(session_name)
        logger.info("✓ Session loaded successfully")
        logger.info(f"  Phone: {loaded_data['phone']}")
        logger.info(f"  User ID: {loaded_data['user_id']}")

        # Verify persistence
        logger.info("\n🔍 Verifying persistence...")
        exists = await manager.session_exists(session_name)
        logger.info(f"✓ Session exists check: {exists}")


async def example_list_sessions():
    """
    Example 3: Listing all available sessions.

    Demonstrates how to discover and enumerate stored sessions.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Listing All Available Sessions")
    logger.info("=" * 70)

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized: {temp_dir}")

        # Create multiple mock sessions
        sessions = {
            "account1": {"phone": "+1111111111", "user_id": 111111, "auth_key": "key1"},
            "account2": {"phone": "+2222222222", "user_id": 222222, "auth_key": "key2"},
            "account3": {"phone": "+3333333333", "user_id": 333333, "auth_key": "key3"},
        }

        logger.info("\n💾 Creating multiple sessions...")
        for name, data in sessions.items():
            await manager.save_session(name, data)
            logger.info(f"  ✓ Saved: {name}")

        logger.info("\n📋 Listing all sessions...")
        session_list = manager.list_sessions()
        logger.info(f"✓ Found {len(session_list)} session(s):")
        for session_name in session_list:
            # Load details for each session
            data = await manager.load_session(session_name)
            logger.info(f"  - {session_name}: {data['phone']} (ID: {data['user_id']})")


async def example_delete_session():
    """
    Example 4: Deleting sessions.

    Demonstrates session deletion with proper cleanup.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Deleting Sessions")
    logger.info("=" * 70)

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized: {temp_dir}")

        # Create a session
        session_name = "to_be_deleted"
        session_data = {
            "phone": "+9999999999",
            "user_id": 999999,
            "auth_key": "temp_key"
        }

        logger.info(f"\n💾 Creating session: {session_name}")
        await manager.save_session(session_name, session_data)
        logger.info("✓ Session created")

        # Verify it exists
        exists_before = await manager.session_exists(session_name)
        logger.info(f"✓ Session exists before delete: {exists_before}")

        # Delete it
        logger.info(f"\n🗑️  Deleting session: {session_name}")
        await manager.delete_session(session_name)
        logger.info("✓ Session deleted")

        # Verify it's gone
        exists_after = await manager.session_exists(session_name)
        logger.info(f"✓ Session exists after delete: {exists_after}")

        if not exists_after:
            logger.info("✓ Deletion verified - session no longer exists")


async def example_error_handling():
    """
    Example 5: Error handling for session operations.

    Demonstrates proper error handling for common failure scenarios.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Error Handling")
    logger.info("=" * 70)

    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized: {temp_dir}")

        # Test 1: Invalid phone number
        logger.info("\n📝 Test 1: Invalid phone number")
        try:
            await manager.create_session("invalid_phone", lambda: "12345")
        except (ValueError, AuthenticationError) as e:
            logger.info(f"✓ Correctly rejected invalid phone: {e}")

        # Test 2: Loading non-existent session
        logger.info("\n📝 Test 2: Loading non-existent session")
        try:
            await manager.load_session("does_not_exist")
        except AyuGramError as e:
            logger.info(f"✓ Correctly handled missing session: {e}")

        # Test 3: Deleting non-existent session (graceful)
        logger.info("\n📝 Test 3: Deleting non-existent session (graceful)")
        try:
            await manager.delete_session("does_not_exist")
            logger.info("✓ Deletion of non-existent session handled gracefully")
        except AyuGramError as e:
            logger.info(f"✓ Handled gracefully: {e}")

        # Test 4: Invalid session data
        logger.info("\n📝 Test 4: Saving invalid session data")
        try:
            invalid_data = {"phone": ""}  # Missing required fields
            await manager.save_session("invalid", invalid_data)
        except AyuGramError as e:
            logger.info(f"✓ Correctly rejected invalid data: {e}")


async def example_redis_caching():
    """
    Example 6: Redis caching for faster session access.

    Demonstrates optional Redis integration for session caching.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 6: Redis Caching (Optional)")
    logger.info("=" * 70)

    # Check if Redis is available
    from ayugram.session import REDIS_AVAILABLE

    if not REDIS_AVAILABLE:
        logger.info("\n⚠️  Redis not available - skipping this example")
        logger.info("To enable Redis caching:")
        logger.info("  pip install redis")
        return

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing Redis pattern:")
        logger.info("""
# Initialize SessionManager with Redis
manager = SessionManager(
    session_dir="./sessions",
    redis_url="redis://localhost:6379",
    redis_ttl=3600  # Cache for 1 hour
)

# First load - reads from disk, caches to Redis
session1 = await manager.load_session("my_account")

# Second load - reads from Redis (much faster)
session2 = await manager.load_session("my_account")

# Delete - removes from both disk and Redis
await manager.delete_session("my_account")
        """)
        logger.info("\n✓ Redis pattern displayed")
        return

    # Real mode with Redis
    logger.info("\n🔧 REAL MODE - Using Redis caching...")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    logger.info(f"📡 Connecting to Redis: {redis_url}")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            manager = SessionManager(temp_dir, redis_url=redis_url)
            logger.info("✓ SessionManager initialized with Redis")

            # Save a session (will be cached to Redis)
            session_name = "cached_session"
            session_data = {
                "phone": "+1234567890",
                "user_id": 123456,
                "auth_key": "cached_key"
            }

            logger.info(f"\n💾 Saving session: {session_name}")
            await manager.save_session(session_name, session_data)
            logger.info("✓ Session saved to disk and cached in Redis")

            # Load session (will read from Redis cache)
            logger.info(f"\n📥 Loading session from cache: {session_name}")
            loaded = await manager.load_session(session_name)
            logger.info("✓ Session loaded (likely from Redis cache)")
            logger.info(f"  Phone: {loaded['phone']}")

            # Clear caches
            logger.info("\n🧹 Clearing all caches...")
            await manager.clear_all_caches()
            logger.info("✓ Both memory and Redis caches cleared")

        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.info("Continuing without Redis caching...")


async def example_session_backup():
    """
    Example 7: Session backup and recovery.

    Demonstrates automatic backup creation and corruption recovery.
    """
    logger.info("\n" + "=" * 70)
    logger.info("Example 7: Session Backup and Recovery")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n📝 DEMO MODE - Showing backup pattern:")
        logger.info("""
# SessionManager automatically creates .bak backups

# Save session (creates backup if already exists)
await manager.save_session("my_account", session_data)
# Creates: my_account.json and my_account.json.bak

# If main file is corrupted, load attempts recovery:
session = await manager.load_session("my_account")
# Automatically tries to restore from .bak if main is corrupted
        """)
        logger.info("\n✓ Backup pattern displayed")
        return

    # Real mode
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SessionManager(temp_dir)
        logger.info(f"✓ SessionManager initialized: {temp_dir}")

        session_name = "backup_test"
        session_data = {
            "phone": "+1234567890",
            "user_id": 123456,
            "auth_key": "backup_test_key"
        }

        # Save initial session
        logger.info(f"\n💾 Saving session: {session_name}")
        await manager.save_session(session_name, session_data)
        logger.info("✓ Session saved (backup created)")

        # Modify and save again (updates backup)
        session_data["user_id"] = 789012
        logger.info("\n📝 Updating session...")
        await manager.save_session(session_name, session_data)
        logger.info("✓ Session updated (backup refreshed)")

        # Load session
        loaded = await manager.load_session(session_name)
        logger.info(f"✓ Loaded session with User ID: {loaded['user_id']}")


async def main():
    """
    Main entry point running all session management examples.
    """
    logger.info("\n" + "=" * 70)
    logger.info("AyuGram Python SDK - Session Management Examples")
    logger.info("=" * 70)

    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        logger.info("\n🎭 DEMO MODE")
        logger.info("Showing code patterns without requiring real AyuGram server")
        logger.info("\nTo run with real server:")
        logger.info("  1. Start AyuGram JSON-RPC server")
        logger.info("  2. Set DEMO_MODE=false")
        logger.info("  3. Set AYUGRAM_ENGINE_URL (default: http://localhost:8080/jsonrpc)")
    else:
        logger.info("\n🔧 REAL MODE")
        logger.info("Requires AyuGram JSON-RPC server to be running")
        engine_url = os.getenv("AYUGRAM_ENGINE_URL", "http://localhost:8080/jsonrpc")
        logger.info(f"  Server URL: {engine_url}")

    try:
        # Run all examples
        await example_create_session()
        await asyncio.sleep(0.5)

        await example_save_and_load()
        await asyncio.sleep(0.5)

        await example_list_sessions()
        await asyncio.sleep(0.5)

        await example_delete_session()
        await asyncio.sleep(0.5)

        await example_error_handling()
        await asyncio.sleep(0.5)

        await example_redis_caching()
        await asyncio.sleep(0.5)

        await example_session_backup()

        logger.info("\n" + "=" * 70)
        logger.info("✓ All session management examples completed!")
        logger.info("=" * 70)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Example interrupted by user")
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """
    Run the session management examples.

    This demonstrates:
    - Creating sessions with phone authentication
    - Saving and loading sessions
    - Listing available sessions
    - Deleting sessions
    - Error handling
    - Redis caching (optional)
    - Session backup and recovery
    """
    asyncio.run(main())
