"""
Unit tests for JSON-RPC client.

This module tests the JsonRpcClient implementation including connection
management, request/response handling, error handling, and reconnection logic.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import ClientError, ClientSession, ClientTimeout

from ayugram.rpc import JsonRpcClient
from ayugram.exceptions import AyuGramError, ConnectionError, TimeoutError as AyuTimeoutError


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_endpoint_url():
    """Provide a test RPC endpoint URL."""
    return "http://localhost:8080/jsonrpc"


@pytest.fixture
async def mock_aiohttp_session():
    """
    Create a mock aiohttp ClientSession for testing.

    Returns a mock session with async context managers for post/get requests.
    """
    mock_session = MagicMock(spec=ClientSession)

    # Mock response object
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock()
    mock_response.text = AsyncMock(return_value="Error text")

    # Mock post context manager - use regular Mock, not AsyncMock
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = Mock(return_value=mock_post_cm)

    # Mock get context manager (for connection testing)
    mock_get_cm = AsyncMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = Mock(return_value=mock_get_cm)

    # Mock close
    mock_session.close = AsyncMock()

    # Mock timeout attribute
    mock_session.timeout = ClientTimeout(total=30)

    return mock_session


@pytest.fixture
def rpc_client(test_endpoint_url):
    """Create a JsonRpcClient instance for testing."""
    return JsonRpcClient(test_endpoint_url, timeout=30, max_retries=3)


@pytest.fixture
def rpc_success_response():
    """Create a mock successful JSON-RPC response."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"status": "ok", "data": "test_data"},
    }


@pytest.fixture
def rpc_error_response():
    """Create a mock JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32600,
            "message": "Invalid Request",
        },
    }


# ============================================================================
# Initialization Tests
# ============================================================================


class TestJsonRpcClientInit:
    """Test JsonRpcClient initialization and configuration."""

    def test_init_with_valid_endpoint(self, test_endpoint_url):
        """Test initialization with valid endpoint URL."""
        client = JsonRpcClient(test_endpoint_url)
        assert client.endpoint_url == test_endpoint_url
        assert client.timeout.total == 30
        assert client.max_retries == 3
        assert client._owned_session is True
        assert client._request_id == 0
        assert client.is_connected is False

    def test_init_with_custom_timeout(self, test_endpoint_url):
        """Test initialization with custom timeout."""
        client = JsonRpcClient(test_endpoint_url, timeout=60)
        assert client.timeout.total == 60

    def test_init_with_custom_retries(self, test_endpoint_url):
        """Test initialization with custom retry count."""
        client = JsonRpcClient(test_endpoint_url, max_retries=5)
        assert client.max_retries == 5

    def test_init_with_existing_session(self, test_endpoint_url, mock_aiohttp_session):
        """Test initialization with existing aiohttp session."""
        client = JsonRpcClient(test_endpoint_url, session=mock_aiohttp_session)
        assert client._session == mock_aiohttp_session
        assert client._owned_session is False

    def test_init_trailing_slash_removal(self):
        """Test that trailing slashes are removed from endpoint URL."""
        client = JsonRpcClient("http://localhost:8080/jsonrpc/")
        assert client.endpoint_url == "http://localhost:8080/jsonrpc"

    def test_init_with_empty_endpoint_raises_error(self):
        """Test that empty endpoint URL raises ValueError."""
        with pytest.raises(ValueError, match="endpoint_url cannot be empty"):
            JsonRpcClient("")

    def test_init_with_connection_pool_settings(self, test_endpoint_url):
        """Test initialization with custom connection pool settings."""
        client = JsonRpcClient(
            test_endpoint_url,
            connection_pool_size=50,
            connection_pool_limit=10,
            keep_alive_timeout=60.0,
            enable_keep_alive=False,
        )
        assert client._connection_pool_size == 50
        assert client._connection_pool_limit == 10
        assert client._keep_alive_timeout == 60.0
        assert client._enable_keep_alive is False

    def test_init_with_reconnect_settings(self, test_endpoint_url):
        """Test initialization with custom reconnection settings."""
        client = JsonRpcClient(
            test_endpoint_url,
            max_reconnect_attempts=10,
            base_reconnect_delay=2.0,
            max_reconnect_delay=120.0,
        )
        assert client._max_reconnect_attempts == 10
        assert client._base_reconnect_delay == 2.0
        assert client._max_reconnect_delay == 120.0


# ============================================================================
# Connection Management Tests
# ============================================================================


class TestConnectionManagement:
    """Test client connection lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_session(self, rpc_client, mock_aiohttp_session):
        """Test that start() creates an aiohttp session."""
        with patch("ayugram.rpc.ClientSession", return_value=mock_aiohttp_session):
            with patch("ayugram.rpc.TCPConnector"):
                await rpc_client.start()
                assert rpc_client._is_connected is True

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, rpc_client, mock_aiohttp_session):
        """Test that calling start() multiple times doesn't cause issues."""
        with patch("ayugram.rpc.ClientSession", return_value=mock_aiohttp_session):
            with patch("ayugram.rpc.TCPConnector"):
                await rpc_client.start()
                await rpc_client.start()  # Should not raise
                assert rpc_client._is_connected is True

    @pytest.mark.asyncio
    async def test_stop_closes_owned_session(self, rpc_client):
        """Test that stop() closes owned aiohttp session."""
        mock_session = MagicMock()
        mock_session.close = AsyncMock()

        rpc_client._session = mock_session
        rpc_client._is_connected = True
        rpc_client._owned_session = True

        await rpc_client.stop()

        mock_session.close.assert_called_once()
        assert rpc_client._is_connected is False

    @pytest.mark.asyncio
    async def test_stop_does_not_close_external_session(self, rpc_client, mock_aiohttp_session):
        """Test that stop() doesn't close externally provided session."""
        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True
        rpc_client._owned_session = False

        await rpc_client.stop()

        mock_aiohttp_session.close.assert_not_called()
        assert rpc_client._is_connected is False

    @pytest.mark.asyncio
    async def test_stop_when_not_connected_is_safe(self, rpc_client):
        """Test that stop() is safe to call when not connected."""
        rpc_client._is_connected = False
        await rpc_client.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self, rpc_client, mock_aiohttp_session):
        """Test using client as async context manager."""
        with patch("ayugram.rpc.ClientSession", return_value=mock_aiohttp_session):
            with patch("ayugram.rpc.TCPConnector"):
                async with rpc_client as client:
                    assert client is rpc_client
                    assert client._is_connected is True
                assert rpc_client._is_connected is False


# ============================================================================
# Request Validation Tests
# ============================================================================


class TestRequestValidation:
    """Test JSON-RPC request validation."""

    def test_validate_valid_request(self, rpc_client):
        """Test validation of valid JSON-RPC request."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "id": 1,
            "params": {"key": "value"},
        }
        rpc_client._validate_request(payload)  # Should not raise

    def test_validate_missing_jsonrpc(self, rpc_client):
        """Test validation fails with missing jsonrpc field."""
        payload = {"method": "test", "id": 1}
        with pytest.raises(ValueError, match="Missing required field 'jsonrpc'"):
            rpc_client._validate_request(payload)

    def test_validate_invalid_jsonrpc_version(self, rpc_client):
        """Test validation fails with invalid jsonrpc version."""
        payload = {
            "jsonrpc": "1.0",
            "method": "test",
            "id": 1,
        }
        with pytest.raises(ValueError, match="Invalid jsonrpc version"):
            rpc_client._validate_request(payload)

    def test_validate_missing_method(self, rpc_client):
        """Test validation fails with missing method field."""
        payload = {"jsonrpc": "2.0", "id": 1}
        with pytest.raises(ValueError, match="Missing required field 'method'"):
            rpc_client._validate_request(payload)

    def test_validate_empty_method(self, rpc_client):
        """Test validation fails with empty method name."""
        payload = {
            "jsonrpc": "2.0",
            "method": "",
            "id": 1,
        }
        with pytest.raises(ValueError, match="must be a non-empty string"):
            rpc_client._validate_request(payload)

    def test_validate_non_string_method(self, rpc_client):
        """Test validation fails with non-string method."""
        payload = {
            "jsonrpc": "2.0",
            "method": 123,
            "id": 1,
        }
        with pytest.raises(ValueError, match="must be a non-empty string"):
            rpc_client._validate_request(payload)

    def test_validate_missing_id_for_request(self, rpc_client):
        """Test validation fails with missing id for request."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test",
        }
        with pytest.raises(ValueError, match="Missing required field 'id'"):
            rpc_client._validate_request(payload)

    def test_validate_id_allowed_for_notification(self, rpc_client):
        """Test notification can have id field (warns but doesn't fail)."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1,
        }
        # Should not raise, just log
        rpc_client._validate_request(payload, is_notification=True)

    def test_validate_invalid_params_type(self, rpc_client):
        """Test validation fails with invalid params type."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1,
            "params": "invalid",
        }
        with pytest.raises(ValueError, match="must be an object or array"):
            rpc_client._validate_request(payload)

    def test_validate_valid_dict_params(self, rpc_client):
        """Test validation accepts dict params."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1,
            "params": {"key": "value"},
        }
        rpc_client._validate_request(payload)  # Should not raise

    def test_validate_valid_list_params(self, rpc_client):
        """Test validation accepts list params."""
        payload = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1,
            "params": [1, 2, 3],
        }
        rpc_client._validate_request(payload)  # Should not raise


# ============================================================================
# RPC Call Tests
# ============================================================================


class TestRpcCall:
    """Test JSON-RPC call functionality."""

    @pytest.mark.asyncio
    async def test_call_success(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test successful RPC call."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        result = await rpc_client.call("test_method", {"param": "value"})

        assert result == rpc_success_response["result"]
        mock_aiohttp_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_without_params(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test RPC call without parameters."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        result = await rpc_client.call("test_method")

        assert result == rpc_success_response["result"]

    @pytest.mark.asyncio
    async def test_call_with_list_params(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test RPC call with list (positional) parameters."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        result = await rpc_client.call("test_method", [1, 2, 3])

        assert result == rpc_success_response["result"]

    @pytest.mark.asyncio
    async def test_call_auto_increments_request_id(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test that request IDs are auto-incremented."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.call("method1")
        assert rpc_client._request_id == 1

        await rpc_client.call("method2")
        assert rpc_client._request_id == 2

    @pytest.mark.asyncio
    async def test_call_with_custom_request_id(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test RPC call with custom request ID."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.call("test_method", request_id=999)

        # Custom ID should not affect the counter
        assert rpc_client._request_id == 0

    @pytest.mark.asyncio
    async def test_call_with_empty_method_raises_error(self, rpc_client):
        """Test that empty method name raises ValueError."""
        rpc_client._is_connected = True

        with pytest.raises(ValueError, match="method cannot be empty"):
            await rpc_client.call("")

    @pytest.mark.asyncio
    async def test_call_starts_client_if_not_connected(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test that call() automatically starts client if not connected."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        with patch.object(rpc_client, "start", new_callable=AsyncMock) as mock_start:
            rpc_client._session = mock_aiohttp_session
            rpc_client._is_connected = False

            await rpc_client.call("test_method")

            mock_start.assert_called_once()


# ============================================================================
# Response Parsing Tests
# ============================================================================


class TestResponseParsing:
    """Test JSON-RPC response parsing."""

    def test_parse_success_response(self, rpc_client, rpc_success_response):
        """Test parsing successful response."""
        result = rpc_client._parse_response(rpc_success_response)
        assert result == rpc_success_response["result"]

    def test_parse_error_response(self, rpc_client, rpc_error_response):
        """Test parsing error response."""
        with pytest.raises(AyuGramError, match="JSON-RPC error -32600"):
            rpc_client._parse_response(rpc_error_response)

    def test_parse_response_with_error_data(self, rpc_client):
        """Test parsing error response with additional data."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {"field": "chat_id", "issue": "required"},
            },
        }

        with pytest.raises(AyuGramError) as exc_info:
            rpc_client._parse_response(response)

        assert "Invalid params" in str(exc_info.value)
        assert exc_info.value.details["code"] == -32602

    def test_parse_non_dict_response(self, rpc_client):
        """Test parsing non-dict response raises error."""
        with pytest.raises(AyuGramError, match="must be an object"):
            rpc_client._parse_response("not a dict")

    def test_parse_response_missing_result_and_error(self, rpc_client):
        """Test parsing response without result or error field."""
        response = {"jsonrpc": "2.0", "id": 1}

        with pytest.raises(AyuGramError, match="missing 'result' field"):
            rpc_client._parse_response(response)

    def test_parse_invalid_error_object(self, rpc_client):
        """Test parsing response with invalid error object."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": "not a dict",
        }

        with pytest.raises(AyuGramError, match="error must be an object"):
            rpc_client._parse_response(response)

    def test_parse_response_warns_on_wrong_version(self, rpc_client, caplog):
        """Test parsing response with wrong jsonrpc version."""
        response = {
            "jsonrpc": "1.0",
            "id": 1,
            "result": "ok",
        }

        # Should parse but log warning
        result = rpc_client._parse_response(response)
        assert result == "ok"


# ============================================================================
# Notification Tests
# ============================================================================


class TestNotify:
    """Test JSON-RPC notification functionality."""

    @pytest.mark.asyncio
    async def test_notify_success(self, rpc_client, mock_aiohttp_session):
        """Test successful notification."""
        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.notify("test_event", {"status": "idle"})

        mock_aiohttp_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_without_params(self, rpc_client, mock_aiohttp_session):
        """Test notification without parameters."""
        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.notify("test_event")

        mock_aiohttp_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_with_list_params(self, rpc_client, mock_aiohttp_session):
        """Test notification with list parameters."""
        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.notify("test_event", [1, 2, 3])

        mock_aiohttp_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_payload_has_no_id(self, rpc_client, mock_aiohttp_session):
        """Test that notification payload doesn't include id field."""
        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        await rpc_client.notify("test_event")

        # Check the payload sent
        call_args = mock_aiohttp_session.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert "id" not in payload
        assert payload["method"] == "test_event"
        assert payload["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_notify_empty_method_raises_error(self, rpc_client):
        """Test that empty method name raises ValueError."""
        rpc_client._is_connected = True

        with pytest.raises(ValueError, match="method cannot be empty"):
            await rpc_client.notify("")


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in RPC operations."""

    @pytest.mark.asyncio
    async def test_http_error_response(self, rpc_client, mock_aiohttp_session):
        """Test handling of HTTP error response."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        with pytest.raises(ConnectionError, match="HTTP 500"):
            await rpc_client.call("test_method")

    @pytest.mark.asyncio
    async def test_timeout_error(self, rpc_client, mock_aiohttp_session):
        """Test handling of timeout error."""
        # Make __aenter__ raise TimeoutError every time it's called
        mock_post_cm = mock_aiohttp_session.post.return_value
        mock_post_cm.__aenter__.side_effect = asyncio.TimeoutError

        rpc_client._session = mock_aiohttp_session
        rpc_client._owned_session = False  # Prevent reconnection from creating real session
        rpc_client._is_connected = True
        rpc_client.max_retries = 0  # No retries for this test

        with pytest.raises(AyuTimeoutError, match="Request timeout"):
            await rpc_client.call("test_method")

    @pytest.mark.asyncio
    async def test_connection_error(self, rpc_client, mock_aiohttp_session):
        """Test handling of connection error."""
        # Make __aenter__ raise ClientError
        mock_post_cm = mock_aiohttp_session.post.return_value
        mock_post_cm.__aenter__.side_effect = ClientError("Connection failed")

        rpc_client._session = mock_aiohttp_session
        rpc_client._owned_session = False  # Prevent reconnection from creating real session
        rpc_client._is_connected = True
        rpc_client.max_retries = 0  # No retries for this test

        with pytest.raises(ConnectionError, match="Request failed"):
            await rpc_client.call("test_method")

    @pytest.mark.asyncio
    async def test_json_decode_error(self, rpc_client, mock_aiohttp_session):
        """Test handling of invalid JSON response."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        with pytest.raises(ConnectionError, match="Request failed"):
            await rpc_client.call("test_method")


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Test request retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, rpc_client, mock_aiohttp_session, rpc_success_response):
        """Test that request is retried on timeout."""
        mock_post_cm = mock_aiohttp_session.post.return_value
        mock_response = mock_post_cm.__aenter__.return_value

        # Create separate mock context managers for each call
        call_count = 0

        mock_post_cm1 = AsyncMock()
        mock_post_cm1.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_post_cm1.__aexit__ = AsyncMock(return_value=None)

        mock_post_cm2 = AsyncMock()
        mock_post_cm2.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm2.__aexit__ = AsyncMock(return_value=None)
        mock_response.json.return_value = rpc_success_response

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_post_cm1
            else:
                return mock_post_cm2

        mock_aiohttp_session.post.side_effect = side_effect

        rpc_client._session = mock_aiohttp_session
        rpc_client._owned_session = False  # Prevent reconnection from creating real session
        rpc_client._is_connected = True

        result = await rpc_client.call("test_method")

        assert result == rpc_success_response["result"]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, rpc_client, mock_aiohttp_session):
        """Test that retry is exhausted after max attempts."""
        # Create multiple mock context managers, all raising TimeoutError
        mock_post_cm = mock_aiohttp_session.post.return_value
        mock_post_cm.__aenter__.side_effect = asyncio.TimeoutError

        rpc_client._session = mock_aiohttp_session
        rpc_client._owned_session = False  # Prevent reconnection from creating real session
        rpc_client._is_connected = True
        rpc_client.max_retries = 2

        with pytest.raises(AyuTimeoutError):
            await rpc_client.call("test_method")

        # Should be called initial attempt + retries
        assert mock_aiohttp_session.post.call_count == 3


# ============================================================================
# Reconnection Tests
# ============================================================================


class TestReconnection:
    """Test automatic reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnect_on_connection_loss(self, rpc_client, mock_aiohttp_session, rpc_success_response):
        """Test reconnection on connection loss."""
        mock_post_cm = mock_aiohttp_session.post.return_value
        mock_response = mock_post_cm.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        rpc_client._session = mock_aiohttp_session
        rpc_client._owned_session = False  # Prevent reconnection from creating real session
        rpc_client._is_connected = True

        # Mock _try_reconnect to return True
        with patch.object(rpc_client, "_try_reconnect", new_callable=AsyncMock, return_value=True):
            # First call fails with connection error
            call_count = 0

            mock_post_cm1 = AsyncMock()
            mock_post_cm1.__aenter__ = AsyncMock(side_effect=ConnectionError("Connection lost"))
            mock_post_cm1.__aexit__ = AsyncMock(return_value=None)

            mock_post_cm2 = AsyncMock()
            mock_post_cm2.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm2.__aexit__ = AsyncMock(return_value=None)
            mock_response.json.return_value = rpc_success_response

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_post_cm1
                else:
                    return mock_post_cm2

            mock_aiohttp_session.post.side_effect = side_effect

            result = await rpc_client.call("test_method")

            assert result == rpc_success_response["result"]
            rpc_client._try_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_exponential_backoff(self, rpc_client):
        """Test exponential backoff in reconnection."""
        rpc_client._max_reconnect_attempts = 3
        rpc_client._base_reconnect_delay = 0.1  # Small for testing
        rpc_client._max_reconnect_delay = 1.0

        # Mock _test_connection to always fail
        with patch.object(rpc_client, "_test_connection", new_callable=AsyncMock, side_effect=ConnectionError("Failed")):
            result = await rpc_client._try_reconnect()

            # Should exhaust all attempts
            assert result is False
            assert rpc_client._reconnect_attempt == 3

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts(self, rpc_client):
        """Test that reconnection stops after max attempts."""
        rpc_client._max_reconnect_attempts = 2
        rpc_client._reconnect_attempt = 2

        result = await rpc_client._try_reconnect()

        assert result is False

    @pytest.mark.asyncio
    async def test_reconnect_success(self, rpc_client, mock_aiohttp_session):
        """Test successful reconnection."""
        rpc_client._is_connected = False
        rpc_client._reconnect_attempt = 1
        rpc_client._max_reconnect_attempts = 3

        rpc_client._owned_session = True
        rpc_client._session = mock_aiohttp_session

        with patch("ayugram.rpc.TCPConnector"):
            with patch("ayugram.rpc.ClientSession") as mock_session_class:
                new_session = MagicMock()
                new_session.close = AsyncMock()
                mock_session_class.return_value = new_session

                with patch.object(rpc_client, "_test_connection", new_callable=AsyncMock):
                    result = await rpc_client._try_reconnect()

                    assert result is True
                    assert rpc_client._is_connected is True
                    assert rpc_client._reconnect_attempt == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_call_lifecycle(self, rpc_client, rpc_success_response, mock_aiohttp_session):
        """Test complete lifecycle: start -> call -> stop."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = rpc_success_response

        with patch("ayugram.rpc.ClientSession", return_value=mock_aiohttp_session):
            with patch("ayugram.rpc.TCPConnector"):
                # Start client
                await rpc_client.start()
                assert rpc_client.is_connected is True

                # Make call
                result = await rpc_client.call("test_method", {"param": "value"})
                assert result == rpc_success_response["result"]

                # Stop client
                await rpc_client.stop()
                assert rpc_client.is_connected is False

    @pytest.mark.asyncio
    async def test_multiple_calls_same_session(self, rpc_client, mock_aiohttp_session):
        """Test multiple RPC calls using the same session."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value

        responses = [
            {"jsonrpc": "2.0", "id": 1, "result": "result1"},
            {"jsonrpc": "2.0", "id": 2, "result": "result2"},
            {"jsonrpc": "2.0", "id": 3, "result": "result3"},
        ]

        call_index = 0

        async def mock_json():
            nonlocal call_index
            response = responses[call_index]
            call_index += 1
            return response

        mock_response.json = mock_json

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        result1 = await rpc_client.call("method1")
        result2 = await rpc_client.call("method2")
        result3 = await rpc_client.call("method3")

        assert result1 == "result1"
        assert result2 == "result2"
        assert result3 == "result3"

    @pytest.mark.asyncio
    async def test_mixed_calls_and_notifications(self, rpc_client, mock_aiohttp_session):
        """Test mixing RPC calls and notifications."""
        mock_response = mock_aiohttp_session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": "ok"}

        rpc_client._session = mock_aiohttp_session
        rpc_client._is_connected = True

        # Call
        result = await rpc_client.call("test_method")
        assert result == "ok"

        # Notification
        await rpc_client.notify("test_event")

        # Another call
        result = await rpc_client.call("another_method")
        assert result == "ok"

        assert mock_aiohttp_session.post.call_count == 3


# ============================================================================
# Property Tests
# ============================================================================


class TestProperties:
    """Test client properties."""

    def test_is_connected_property(self, rpc_client):
        """Test is_connected property reflects connection state."""
        assert rpc_client.is_connected is False

        rpc_client._is_connected = True
        assert rpc_client.is_connected is True

        rpc_client._is_connected = False
        assert rpc_client.is_connected is False
