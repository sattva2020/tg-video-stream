"""
Pytest configuration and fixtures for ayugram-python SDK tests.

This module provides common fixtures and configuration for testing
the AyuGram Python SDK, including mock clients, test streams,
and async event loop handling.
"""

import os
import sys
import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Add parent directory to path so tests can import ayugram package
_sdk_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if _sdk_root not in sys.path:
    sys.path.insert(0, _sdk_root)

# Set testing environment variable early
os.environ["TESTING"] = "true"

# Configure warnings
warnings.filterwarnings(
    "ignore",
    message="'audioop' is deprecated",
    category=DeprecationWarning,
)

# Pydantic v2: ignore deprecation warnings for compatibility
try:
    import pydantic.warnings as pyd_warnings

    warnings.filterwarnings(
        "ignore",
        category=pyd_warnings.PydanticDeprecatedSince20,
    )
except Exception:
    pass


# ============================================================================
# Mock Pyrogram/Telethon Client Fixtures
# ============================================================================


@pytest.fixture
def mock_pyrogram_client():
    """
    Create a mock Pyrogram client for testing.

    Returns a MagicMock that mimics a pyrogram.Client instance
    with start, stop, and idle methods mocked as async functions.

    Example:
        >>> def test_with_pyrogram(mock_pyrogram_client):
        ...     client = AyuGramClient(mock_pyrogram_client)
        ...     await client.start()
    """
    mock_client = MagicMock()

    # Mock async methods
    mock_client.start = AsyncMock(return_value=None)
    mock_client.stop = AsyncMock(return_value=None)
    mock_client.idle = AsyncMock(return_value=None)

    # Set common attributes
    mock_client.name = "test_client"

    # Mark this as a Pyrogram mock for client type detection
    mock_client._is_mock_pyrogram = True

    return mock_client


@pytest.fixture
def mock_telethon_client():
    """
    Create a mock Telethon client for testing.

    Returns a MagicMock that mimics a telethon.TelegramClient instance
    with start, stop, and idle methods mocked as async functions.

    Example:
        >>> def test_with_telethon(mock_telethon_client):
        ...     client = AyuGramClient(mock_telethon_client)
        ...     await client.start()
    """
    mock_client = MagicMock()

    # Mock async methods
    mock_client.start = AsyncMock(return_value=None)
    mock_client.stop = AsyncMock(return_value=None)
    mock_client.idle = AsyncMock(return_value=None)

    # Set common attributes
    mock_client.name = "test_client"

    # Mark this as a Telethon mock for client type detection
    mock_client._is_mock_telethon = True

    return mock_client


@pytest.fixture(params=["pyrogram", "telethon"])
def mock_telegram_client(request):
    """
    Parametrized fixture that provides both Pyrogram and Telethon mock clients.

    This fixture runs tests twice: once with a mock Pyrogram client
    and once with a mock Telethon client, ensuring compatibility
    with both libraries.

    Args:
        request: Pytest request object with parameter info

    Example:
        >>> def test_with_both_clients(mock_telegram_client):
        ...     client = AyuGramClient(mock_telegram_client)
        ...     assert client.is_started == False
    """
    if request.param == "pyrogram":
        mock_client = MagicMock()
        mock_client.start = AsyncMock(return_value=None)
        mock_client.stop = AsyncMock(return_value=None)
        mock_client.idle = AsyncMock(return_value=None)
    else:
        mock_client = MagicMock()
        mock_client.start = AsyncMock(return_value=None)
        mock_client.stop = AsyncMock(return_value=None)
        mock_client.idle = AsyncMock(return_value=None)

    mock_client.name = f"test_{request.param}_client"
    return mock_client


# ============================================================================
# AyuGram Client Fixtures
# ============================================================================


@pytest.fixture
async def ayugram_client(mock_pyrogram_client):
    """
    Create an AyuGramClient instance with a mock Pyrogram client.

    The client is started before yielding and stopped after the test.
    This is the most commonly used fixture for testing AyuGram functionality.

    Args:
        mock_pyrogram_client: Mock Pyrogram client fixture

    Example:
        >>> async def test_join_call(ayugram_client):
        ...     stream = AudioPiped("https://example.com/audio.mp3")
        ...     await ayugram_client.join_group_call(-1001234567890, stream)
        ...     assert -1001234567890 in ayugram_client.active_calls
    """
    from ayugram import AyuGramClient

    client = AyuGramClient(mock_pyrogram_client)

    # Start the client
    await client.start()

    yield client

    # Cleanup: stop the client
    if client.is_started:
        await client.stop()


@pytest.fixture
def ayugram_client_unstarted(mock_pyrogram_client):
    """
    Create an AyuGramClient instance without starting it.

    Use this fixture when testing behavior that should work before
    the client is started, or when testing error handling for
    unstarted clients.

    Args:
        mock_pyrogram_client: Mock Pyrogram client fixture

    Example:
        >>> def test_unstarted_client(ayugram_client_unstarted):
        ...     assert ayugram_client_unstarted.is_started == False
    """
    from ayugram import AyuGramClient

    client = AyuGramClient(mock_pyrogram_client)
    return client


# ============================================================================
# Stream Fixtures
# ============================================================================


@pytest.fixture
def audio_stream():
    """
    Create an AudioPiped stream for testing.

    Returns an AudioPiped instance with a test audio URL.

    Example:
        >>> def test_audio_stream(audio_stream):
        ...     assert audio_stream.path == "https://example.com/test.mp3"
    """
    from ayugram.types import AudioPiped

    return AudioPiped("https://example.com/test.mp3")


@pytest.fixture
def video_stream():
    """
    Create an AudioVideoPiped stream for testing.

    Returns an AudioVideoPiped instance with a test video URL.

    Example:
        >>> def test_video_stream(video_stream):
        ...     assert video_stream.path == "https://example.com/test.mp4"
    """
    from ayugram.types import AudioVideoPiped

    return AudioVideoPiped("https://example.com/test.mp4")


@pytest.fixture
def audio_stream_with_quality():
    """
    Create an AudioPiped stream with quality settings for testing.

    Returns an AudioPiped instance with high quality audio settings.

    Example:
        >>> def test_quality_stream(audio_stream_with_quality):
        ...     assert audio_stream_with_quality.high_quality == True
    """
    from ayugram.types import AudioPiped, HighQualityAudio

    return AudioPiped(
        "https://example.com/test.mp3",
        high_quality=HighQualityAudio()
    )


@pytest.fixture
def video_stream_with_quality():
    """
    Create an AudioVideoPiped stream with quality settings for testing.

    Returns an AudioVideoPiped instance with high quality audio and video.

    Example:
        >>> def test_quality_video_stream(video_stream_with_quality):
        ...     assert video_stream_with_quality.high_quality == True
    """
    from ayugram.types import AudioVideoPiped, HighQualityAudio, HighQualityVideo

    return AudioVideoPiped(
        "https://example.com/test.mp4",
        high_quality=HighQualityAudio(),
        high_quality_video=HighQualityVideo()
    )


# ============================================================================
# Test Chat IDs
# ============================================================================


@pytest.fixture
def test_chat_id():
    """
    Provide a test chat ID for testing.

    Returns a standard test chat ID (supergroup format).

    Example:
        >>> def test_chat_operations(test_chat_id):
        ...     assert test_chat_id == -1001234567890
    """
    return -1001234567890


@pytest.fixture
def test_chat_ids():
    """
    Provide multiple test chat IDs for testing.

    Returns a list of chat IDs in different formats (int, str, positive).

    Example:
        >>> def test_multiple_chats(test_chat_ids):
        ...     assert len(test_chat_ids) == 3
    """
    return [
        -1001234567890,  # Supergroup
        "-1009876543210",  # Supergroup as string
        123456789,  # Regular group
    ]


# ============================================================================
# RPC Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_rpc_response():
    """
    Create a mock RPC response for testing.

    Returns a dictionary with a successful RPC response structure.

    Example:
        >>> def test_rpc_handling(mock_rpc_response):
        ...     assert mock_rpc_response["result"] == "ok"
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": "ok",
    }


@pytest.fixture
def mock_rpc_error():
    """
    Create a mock RPC error response for testing.

    Returns a dictionary with an RPC error response structure.

    Example:
        >>> def test_error_handling(mock_rpc_error):
        ...     assert "error" in mock_rpc_error
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32600,
            "message": "Invalid Request",
        },
    }


@pytest.fixture
def mock_rpc_session():
    """
    Create a mock RPC session for testing JSON-RPC calls.

    Returns an AsyncMock that can be used to mock aiohttp ClientSession.

    Example:
        >>> async def test_rpc_call(mock_rpc_session):
        ...     mock_rpc_session.post.return_value.__aenter__.return_value.json.return_value = {"result": "ok"}
    """
    mock_session = MagicMock()

    # Mock the context manager for post request
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"result": "ok"})
    mock_response.status = 200

    mock_post = AsyncMock()
    mock_post.return_value.__aenter__.return_value = mock_response

    mock_session.post = mock_post
    mock_session.close = AsyncMock(return_value=None)

    return mock_session


# ============================================================================
# Event Callback Fixtures
# ============================================================================


@pytest.fixture
def event_callback_mock():
    """
    Create a mock event callback function for testing.

    Returns both sync and async versions of a mock callback.

    Example:
        >>> def test_event_listener(event_callback_mock):
        ...     callback = event_callback_mock["async"]
        ...     client.on('stream_ended', callback)
    """
    async def async_callback(*args, **kwargs):
        pass

    def sync_callback(*args, **kwargs):
        pass

    return {
        "async": async_callback,
        "sync": sync_callback,
    }


# ============================================================================
# Stream State Fixtures
# ============================================================================


@pytest.fixture
def sample_stream_state():
    """
    Create a sample stream state for testing.

    Returns a dictionary with typical stream state values.

    Example:
        >>> def test_stream_state(sample_stream_state):
        ...     assert sample_stream_state["is_playing"] == True
    """
    return {
        "is_playing": True,
        "is_paused": False,
    }


# ============================================================================
# Cleanup and Helper Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_warnings():
    """
    Reset warnings filter before each test.

    This autouse fixture ensures that warning configurations
    don't leak between tests.
    """
    warnings.simplefilter("ignore", DeprecationWarning)
    yield
    warnings.resetwarnings()


@pytest.fixture
def ensure_tests_dir():
    """
    Ensure tests directory exists and is in path.

    This fixture is useful for tests that need to load test data
    from files in the tests directory.
    """
    tests_dir = os.path.dirname(__file__)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    return tests_dir


# ============================================================================
# Mock JSON-RPC Server Fixtures
# ============================================================================


@pytest.fixture
async def mock_server():
    """
    Create and start a mock JSON-RPC server for integration testing.

    This fixture provides a running MockAyuGramServer instance that
    simulates the AyuGram JSON-RPC API. The server is started before
    the test and stopped after the test completes.

    The server runs on a random port to avoid conflicts with other services.

    Returns:
        MockAyuGramServer: Running mock server instance

    Example:
        >>> async def test_with_mock_server(mock_server):
        ...     # Mock server is running at mock_server.server_url
        ...     client = JsonRpcClient(mock_server.server_url)
        ...     await client.start()
        ...     result = await client.call("auth.send_code", {"phone": "+1234567890"})
        ...     assert result["success"] == True
    """
    from tests.mock_server import MockAyuGramServer

    # Use a random port to avoid conflicts
    import socket
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()

    server = MockAyuGramServer(port=port)

    # Start the server
    await server.start()

    yield server

    # Cleanup: stop the server
    await server.stop()
    server.clear_sessions()
    server.clear_request_log()


@pytest.fixture
def mock_server_url(mock_server):
    """
    Get the URL of the running mock JSON-RPC server.

    This is a convenience fixture that returns just the server URL,
    making tests cleaner when they only need the endpoint URL.

    Args:
        mock_server: Running mock server fixture

    Returns:
        str: JSON-RPC endpoint URL

    Example:
        >>> async def test_with_url(mock_server_url):
        ...     client = JsonRpcClient(mock_server_url)
        ...     await client.start()
    """
    return mock_server.server_url


@pytest.fixture
async def mock_server_with_auth(mock_server):
    """
    Mock server with pre-authenticated session.

    This fixture creates a mock server and simulates a successful
    authentication flow, leaving an authenticated session ready for use.

    Args:
        mock_server: Running mock server fixture

    Returns:
        MockAyuGramServer: Server with authenticated session

    Example:
        >>> async def test_authenticated_call(mock_server_with_auth):
        ...     # Server has an authenticated session for +1234567890
        ...     sessions = mock_server_with_auth.get_sessions()
        ...     assert "+1234567890" in sessions
    """
    # Simulate authentication by creating a session
    phone = "+1234567890"
    session_data = {
        "phone": phone,
        "user_id": 123456789,
        "auth_key": "mock_auth_key_base64_encoded",
        "first_name": "Test",
        "last_name": "User",
    }
    mock_server._sessions[phone] = session_data

    return mock_server
