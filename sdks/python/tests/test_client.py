"""Tests for Sattva API Python SDK Client."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from sattva_api import SattvaClient
from sattva_api.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SattvaAPIError,
    ValidationError,
)


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    mock = Mock(spec=requests.Response)
    mock.status_code = 200
    mock.headers = {}
    mock.content = b'{"id": "test"}'
    return mock


@pytest.fixture
def client():
    """Create a test client instance."""
    return SattvaClient(
        api_key="test_api_key_12345",
        base_url="https://api.test.com/api/v1",
        timeout=10,
        max_retries=2,
    )


class TestSattvaClientInit:
    """Tests for SattvaClient initialization."""

    def test_client_initialization(self):
        """Test client initializes with correct defaults."""
        client = SattvaClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.sattva.io/api/v1"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0

    def test_client_custom_configuration(self):
        """Test client with custom configuration."""
        client = SattvaClient(
            api_key="custom_key",
            base_url="https://custom.api.com/v2",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
        )
        assert client.api_key == "custom_key"
        assert client.base_url == "https://custom.api.com/v2"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0

    def test_client_headers(self):
        """Test client sets correct headers."""
        client = SattvaClient(api_key="test_key")
        assert "X-API-Key" in client._client.headers
        assert client._client.headers["X-API-Key"] == "test_key"
        assert client._client.headers["Content-Type"] == "application/json"
        assert "SattvaPythonSDK" in client._client.headers["User-Agent"]

    def test_client_resources_initialized(self):
        """Test all resource managers are initialized."""
        client = SattvaClient(api_key="test_key")
        assert client.streams is not None
        assert client.playlists is not None
        assert client.channels is not None
        assert client.webhooks is not None
        assert client.api_keys is not None

    def test_client_repr(self):
        """Test client string representation."""
        client = SattvaClient(api_key="test_key", base_url="https://api.test.com/v1")
        repr_str = repr(client)
        assert "SattvaClient" in repr_str
        assert "https://api.test.com/v1" in repr_str


class TestSattvaClientContextManager:
    """Tests for context manager support."""

    def test_client_context_manager(self):
        """Test client works as context manager."""
        with SattvaClient(api_key="test_key") as client:
            assert client is not None
            assert client._client is not None
        assert client._client is None


class TestHTTPMethods:
    """Tests for HTTP methods."""

    @patch("requests.Session.request")
    def test_get_request(self, mock_request, client, mock_response):
        """Test GET request."""
        mock_request.return_value = mock_response
        result = client.get("/test/")
        mock_request.assert_called_once()
        assert result == {"id": "test"}

    @patch("requests.Session.request")
    def test_post_request(self, mock_request, client, mock_response):
        """Test POST request."""
        mock_request.return_value = mock_response
        result = client.post("/test/", json_data={"name": "test"})
        mock_request.assert_called_once()
        assert result == {"id": "test"}

    @patch("requests.Session.request")
    def test_patch_request(self, mock_request, client, mock_response):
        """Test PATCH request."""
        mock_request.return_value = mock_response
        result = client.patch("/test/", json_data={"name": "updated"})
        mock_request.assert_called_once()
        assert result == {"id": "test"}

    @patch("requests.Session.request")
    def test_delete_request(self, mock_request, client, mock_response):
        """Test DELETE request."""
        mock_response.content = b""
        mock_request.return_value = mock_response
        result = client.delete("/test/")
        mock_request.assert_called_once()
        assert result == {}

    @patch("requests.Session.request")
    def test_put_request(self, mock_request, client, mock_response):
        """Test PUT request."""
        mock_request.return_value = mock_response
        result = client.put("/test/", json_data={"name": "test"})
        mock_request.assert_called_once()
        assert result == {"id": "test"}


class TestErrorHandling:
    """Tests for error handling."""

    @patch("requests.Session.request")
    def test_authentication_error_401(self, mock_request, client):
        """Test 401 raises AuthenticationError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid API key"}
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/test/")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_not_found_error_404(self, mock_request, client):
        """Test 404 raises NotFoundError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Resource not found"}
        mock_request.return_value = mock_response

        with pytest.raises(NotFoundError) as exc_info:
            client.get("/test/")

        assert exc_info.value.status_code == 404
        assert "Resource not found" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_validation_error_422(self, mock_request, client):
        """Test 422 raises ValidationError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "Validation failed"}
        mock_request.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            client.post("/test/", json_data={"invalid": "data"})

        assert exc_info.value.status_code == 422
        assert "Validation failed" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_rate_limit_error_429(self, mock_request, client):
        """Test 429 raises RateLimitError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {"X-Retry-After": "60"}
        mock_response.json.return_value = {"detail": "Rate limit exceeded"}
        mock_request.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/test/")

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60
        assert "Rate limit exceeded" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_generic_api_error_500(self, mock_request, client):
        """Test 500 raises SattvaAPIError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}
        mock_request.return_value = mock_response

        with pytest.raises(SattvaAPIError) as exc_info:
            client.get("/test/")

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_timeout_error(self, mock_request, client):
        """Test timeout raises SattvaAPIError."""
        mock_request.side_effect = requests.Timeout("Connection timed out")

        with pytest.raises(SattvaAPIError) as exc_info:
            client.get("/test/")

        assert "timed out" in str(exc_info.value.message).lower()

    @patch("requests.Session.request")
    def test_connection_error(self, mock_request, client):
        """Test connection error raises SattvaAPIError."""
        mock_request.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(SattvaAPIError) as exc_info:
            client.get("/test/")

        assert "Network error" in str(exc_info.value.message)

    def test_closed_client_error(self, client):
        """Test closed client raises error."""
        client.close()
        with pytest.raises(SattvaAPIError) as exc_info:
            client.get("/test/")

        assert "closed" in str(exc_info.value.message).lower()


class TestRateLimitRetry:
    """Tests for rate limit retry logic."""

    @patch("time.sleep")
    @patch("requests.Session.request")
    def test_rate_limit_retry_success(self, mock_request, mock_sleep, client):
        """Test successful retry after rate limit."""
        # First call: rate limited
        mock_response_429 = Mock(spec=requests.Response)
        mock_response_429.status_code = 429
        mock_response_429.headers = {"X-Retry-After": "1"}
        mock_response_429.json.return_value = {"detail": "Rate limited"}

        # Second call: success
        mock_response_200 = Mock(spec=requests.Response)
        mock_response_200.status_code = 200
        mock_response_200.content = b'{"success": true}'
        mock_response_200.json.return_value = {"success": True}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        result = client.get("/test/")

        assert mock_request.call_count == 2
        assert mock_sleep.called
        assert result == {"success": True}

    @patch("requests.Session.request")
    def test_rate_limit_retry_exhausted(self, mock_request, client):
        """Test retry exhaustion raises RateLimitError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.json.return_value = {"detail": "Rate limited"}
        mock_request.return_value = mock_response

        client.max_retries = 2

        with pytest.raises(RateLimitError):
            client.get("/test/")

        # Should be called 1 + max_retries times
        assert mock_request.call_count == 3


class TestChannelsResource:
    """Tests for ChannelsResource."""

    @patch("requests.Session.request")
    def test_list_channels(self, mock_request, client, mock_response):
        """Test listing channels."""
        mock_response.json.return_value = [
            {"id": "ch1", "name": "Channel 1"},
            {"id": "ch2", "name": "Channel 2"},
        ]
        mock_request.return_value = mock_response

        result = client.channels.list()

        assert len(result) == 2
        assert result[0]["name"] == "Channel 1"

    @patch("requests.Session.request")
    def test_get_channel(self, mock_request, client, mock_response):
        """Test getting a specific channel."""
        mock_response.json.return_value = {"id": "ch1", "name": "Channel 1"}
        mock_request.return_value = mock_response

        result = client.channels.get("ch1")

        assert result["id"] == "ch1"
        assert result["name"] == "Channel 1"

    @patch("requests.Session.request")
    def test_create_channel(self, mock_request, client, mock_response):
        """Test creating a channel."""
        mock_response.json.return_value = {
            "id": "ch1",
            "name": "New Channel",
            "chat_id": 12345,
        }
        mock_request.return_value = mock_response

        result = client.channels.create(
            account_id="acc1",
            chat_id=12345,
            name="New Channel",
        )

        assert result["name"] == "New Channel"

    @patch("requests.Session.request")
    def test_update_channel(self, mock_request, client, mock_response):
        """Test updating a channel."""
        mock_response.json.return_value = {"id": "ch1", "name": "Updated Channel"}
        mock_request.return_value = mock_response

        result = client.channels.update("ch1", name="Updated Channel")

        assert result["name"] == "Updated Channel"

    @patch("requests.Session.request")
    def test_delete_channel(self, mock_request, client, mock_response):
        """Test deleting a channel."""
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = client.channels.delete("ch1")

        assert result == {}

    @patch("requests.Session.request")
    def test_start_channel(self, mock_request, client, mock_response):
        """Test starting a channel stream."""
        mock_response.json.return_value = {"status": "streaming"}
        mock_request.return_value = mock_response

        result = client.channels.start("ch1")

        assert result["status"] == "streaming"

    @patch("requests.Session.request")
    def test_stop_channel(self, mock_request, client, mock_response):
        """Test stopping a channel stream."""
        mock_response.json.return_value = {"status": "stopped"}
        mock_request.return_value = mock_response

        result = client.channels.stop("ch1")

        assert result["status"] == "stopped"

    @patch("requests.Session.request")
    def test_restart_channel(self, mock_request, client, mock_response):
        """Test restarting a channel stream."""
        mock_response.json.return_value = {"status": "streaming"}
        mock_request.return_value = mock_response

        result = client.channels.restart("ch1")

        assert result["status"] == "streaming"


class TestStreamsResource:
    """Tests for StreamsResource."""

    @patch("requests.Session.request")
    def test_list_streams(self, mock_request, client, mock_response):
        """Test listing streams."""
        mock_response.json.return_value = [
            {"id": "str1", "name": "Stream 1"},
        ]
        mock_request.return_value = mock_response

        result = client.streams.list()

        assert len(result) == 1
        assert result[0]["name"] == "Stream 1"

    @patch("requests.Session.request")
    def test_get_stream(self, mock_request, client, mock_response):
        """Test getting a specific stream."""
        mock_response.json.return_value = {"id": "str1", "status": "active"}
        mock_request.return_value = mock_response

        result = client.streams.get("str1")

        assert result["id"] == "str1"

    @patch("requests.Session.request")
    def test_start_stream(self, mock_request, client, mock_response):
        """Test starting a stream."""
        mock_response.json.return_value = {"status": "streaming"}
        mock_request.return_value = mock_response

        result = client.streams.start("str1")

        assert result["status"] == "streaming"

    @patch("requests.Session.request")
    def test_stop_stream(self, mock_request, client, mock_response):
        """Test stopping a stream."""
        mock_response.json.return_value = {"status": "stopped"}
        mock_request.return_value = mock_response

        result = client.streams.stop("str1")

        assert result["status"] == "stopped"

    @patch("requests.Session.request")
    def test_restart_stream(self, mock_request, client, mock_response):
        """Test restarting a stream."""
        mock_response.json.return_value = {"status": "streaming"}
        mock_request.return_value = mock_response

        result = client.streams.restart("str1")

        assert result["status"] == "streaming"


class TestPlaylistsResource:
    """Tests for PlaylistsResource."""

    @patch("requests.Session.request")
    def test_list_playlist_items(self, mock_request, client, mock_response):
        """Test listing playlist items."""
        mock_response.json.return_value = [
            {"id": "pl1", "title": "Track 1"},
            {"id": "pl2", "title": "Track 2"},
        ]
        mock_request.return_value = mock_response

        result = client.playlists.list()

        assert len(result) == 2
        assert result[0]["title"] == "Track 1"

    @patch("requests.Session.request")
    def test_list_playlist_items_by_channel(self, mock_request, client, mock_response):
        """Test listing playlist items filtered by channel."""
        mock_response.json.return_value = [{"id": "pl1", "channel_id": "ch1"}]
        mock_request.return_value = mock_response

        result = client.playlists.list(channel_id="ch1")

        assert len(result) == 1

    @patch("requests.Session.request")
    def test_get_playlist_item(self, mock_request, client, mock_response):
        """Test getting a specific playlist item."""
        mock_response.json.return_value = {"id": "pl1", "title": "Track 1"}
        mock_request.return_value = mock_response

        result = client.playlists.get("pl1")

        assert result["id"] == "pl1"

    @patch("requests.Session.request")
    def test_create_playlist_item(self, mock_request, client, mock_response):
        """Test creating a playlist item."""
        mock_response.json.return_value = {
            "id": "pl1",
            "url": "https://youtube.com/watch?v=test",
            "title": "Test Track",
        }
        mock_request.return_value = mock_response

        result = client.playlists.create(
            url="https://youtube.com/watch?v=test",
            title="Test Track",
        )

        assert result["url"] == "https://youtube.com/watch?v=test"

    @patch("requests.Session.request")
    def test_update_playlist_item(self, mock_request, client, mock_response):
        """Test updating a playlist item."""
        mock_response.json.return_value = {"id": "pl1", "title": "Updated Track"}
        mock_request.return_value = mock_response

        result = client.playlists.update("pl1", title="Updated Track")

        assert result["title"] == "Updated Track"

    @patch("requests.Session.request")
    def test_delete_playlist_item(self, mock_request, client, mock_response):
        """Test deleting a playlist item."""
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = client.playlists.delete("pl1")

        assert result == {}

    @patch("requests.Session.request")
    def test_reorder_playlist(self, mock_request, client, mock_response):
        """Test reordering playlist items."""
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response

        items = [{"id": "pl1", "position": 0}, {"id": "pl2", "position": 1}]
        result = client.playlists.reorder(items)

        assert result["success"] is True

    @patch("requests.Session.request")
    def test_update_playlist_item_status(self, mock_request, client, mock_response):
        """Test updating playlist item status."""
        mock_response.json.return_value = {"id": "pl1", "status": "playing"}
        mock_request.return_value = mock_response

        result = client.playlists.update_status("pl1", status="playing")

        assert result["status"] == "playing"


class TestWebhooksResource:
    """Tests for WebhooksResource."""

    @patch("requests.Session.request")
    def test_list_webhooks(self, mock_request, client, mock_response):
        """Test listing webhooks."""
        mock_response.json.return_value = [
            {
                "id": "wh1",
                "url": "https://example.com/webhook",
                "event_types": ["stream.started"],
            },
        ]
        mock_request.return_value = mock_response

        result = client.webhooks.list()

        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/webhook"

    @patch("requests.Session.request")
    def test_get_webhook(self, mock_request, client, mock_response):
        """Test getting a specific webhook."""
        mock_response.json.return_value = {
            "id": "wh1",
            "url": "https://example.com/webhook",
        }
        mock_request.return_value = mock_response

        result = client.webhooks.get("wh1")

        assert result["id"] == "wh1"

    @patch("requests.Session.request")
    def test_create_webhook(self, mock_request, client, mock_response):
        """Test creating a webhook."""
        mock_response.json.return_value = {
            "id": "wh1",
            "url": "https://example.com/webhook",
            "secret": "webhook_secret_123",
        }
        mock_request.return_value = mock_response

        result = client.webhooks.create(
            url="https://example.com/webhook",
            event_types=["stream.started", "stream.stopped"],
        )

        assert result["url"] == "https://example.com/webhook"
        assert "secret" in result

    @patch("requests.Session.request")
    def test_update_webhook(self, mock_request, client, mock_response):
        """Test updating a webhook."""
        mock_response.json.return_value = {
            "id": "wh1",
            "url": "https://updated.com/webhook",
        }
        mock_request.return_value = mock_response

        result = client.webhooks.update("wh1", url="https://updated.com/webhook")

        assert result["url"] == "https://updated.com/webhook"

    @patch("requests.Session.request")
    def test_delete_webhook(self, mock_request, client, mock_response):
        """Test deleting a webhook."""
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = client.webhooks.delete("wh1")

        assert result == {}

    @patch("requests.Session.request")
    def test_webhook(self, mock_request, client, mock_response):
        """Test sending a test webhook event."""
        mock_response.json.return_value = {"success": True, "delivered": True}
        mock_request.return_value = mock_response

        result = client.webhooks.test("wh1")

        assert result["success"] is True
        assert result["delivered"] is True

    @patch("requests.Session.request")
    def test_rotate_webhook_secret(self, mock_request, client, mock_response):
        """Test rotating webhook secret."""
        mock_response.json.return_value = {
            "id": "wh1",
            "secret": "new_secret_456",
        }
        mock_request.return_value = mock_response

        result = client.webhooks.rotate_secret("wh1")

        assert "secret" in result

    @patch("requests.Session.request")
    def test_list_webhook_events(self, mock_request, client, mock_response):
        """Test listing webhook delivery events."""
        mock_response.json.return_value = [
            {
                "id": "evt1",
                "webhook_id": "wh1",
                "status": "success",
            },
            {
                "id": "evt2",
                "webhook_id": "wh1",
                "status": "failed",
            },
        ]
        mock_request.return_value = mock_response

        result = client.webhooks.list_events("wh1", limit=100, offset=0)

        assert len(result) == 2
        assert result[0]["status"] == "success"


class TestAPIKeysResource:
    """Tests for APIKeysResource."""

    @patch("requests.Session.request")
    def test_list_api_keys(self, mock_request, client, mock_response):
        """Test listing API keys."""
        mock_response.json.return_value = [
            {
                "id": "key1",
                "name": "Test Key",
                "scopes": ["read:streams"],
            },
        ]
        mock_request.return_value = mock_response

        result = client.api_keys.list()

        assert len(result) == 1
        assert result[0]["name"] == "Test Key"

    @patch("requests.Session.request")
    def test_get_api_key(self, mock_request, client, mock_response):
        """Test getting a specific API key."""
        mock_response.json.return_value = {
            "id": "key1",
            "name": "Test Key",
        }
        mock_request.return_value = mock_response

        result = client.api_keys.get("key1")

        assert result["id"] == "key1"

    @patch("requests.Session.request")
    def test_create_api_key(self, mock_request, client, mock_response):
        """Test creating an API key."""
        mock_response.json.return_value = {
            "id": "key1",
            "name": "New Key",
            "key": "sk_test_12345",
            "scopes": ["read:streams", "write:streams"],
        }
        mock_request.return_value = mock_response

        result = client.api_keys.create(
            name="New Key",
            scopes=["read:streams", "write:streams"],
        )

        assert result["name"] == "New Key"
        assert "key" in result

    @patch("requests.Session.request")
    def test_update_api_key(self, mock_request, client, mock_response):
        """Test updating an API key."""
        mock_response.json.return_value = {
            "id": "key1",
            "name": "Updated Key",
        }
        mock_request.return_value = mock_response

        result = client.api_keys.update("key1", name="Updated Key")

        assert result["name"] == "Updated Key"

    @patch("requests.Session.request")
    def test_delete_api_key(self, mock_request, client, mock_response):
        """Test deleting an API key."""
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = client.api_keys.delete("key1")

        assert result == {}

    @patch("requests.Session.request")
    def test_revoke_api_key(self, mock_request, client, mock_response):
        """Test revoking an API key."""
        mock_response.json.return_value = {"revoked": True}
        mock_request.return_value = mock_response

        result = client.api_keys.revoke("key1")

        assert result["revoked"] is True


class TestRequestConstruction:
    """Tests for request construction and URL handling."""

    @patch("requests.Session.request")
    def test_url_construction(self, mock_request, client, mock_response):
        """Test URLs are constructed correctly."""
        mock_request.return_value = mock_response

        client.get("/test/endpoint")

        call_args = mock_request.call_args
        url = call_args[1]["url"]
        assert url == "https://api.test.com/api/v1/test/endpoint"

    @patch("requests.Session.request")
    def test_base_url_without_trailing_slash(self, mock_request):
        """Test base_url without trailing slash."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.content = b'{"test": true}'
        mock_response.json.return_value = {"test": True}
        mock_request.return_value = mock_response

        client = SattvaClient(
            api_key="test_key",
            base_url="https://api.test.com/api/v1/",  # with trailing slash
        )
        client.get("/test/")

        call_args = mock_request.call_args
        url = call_args[1]["url"]
        # Should not have double slashes
        assert "api/v1/test/" in url

    @patch("requests.Session.request")
    def test_path_without_leading_slash(self, mock_request, client, mock_response):
        """Test path without leading slash is handled."""
        mock_request.return_value = mock_response

        client.get("test/endpoint")

        call_args = mock_request.call_args
        url = call_args[1]["url"]
        assert "test/endpoint" in url

    @patch("requests.Session.request")
    def test_query_params(self, mock_request, client, mock_response):
        """Test query parameters are passed correctly."""
        mock_request.return_value = mock_response

        client.get("/test/", params={"limit": 10, "offset": 5})

        call_args = mock_request.call_args
        params = call_args[1]["params"]
        assert params == {"limit": 10, "offset": 5}

    @patch("requests.Session.request")
    def test_json_body(self, mock_request, client, mock_response):
        """Test JSON body is passed correctly."""
        mock_request.return_value = mock_response

        client.post("/test/", json_data={"name": "test", "value": 123})

        call_args = mock_request.call_args
        json_data = call_args[1]["json"]
        assert json_data == {"name": "test", "value": 123}


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch("requests.Session.request")
    def test_empty_response_body(self, mock_request, client):
        """Test handling of empty response body."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 204
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = client.delete("/test/")

        assert result == {}

    @patch("requests.Session.request")
    def test_malformed_json_response(self, mock_request, client):
        """Test handling of malformed JSON in error response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(SattvaAPIError):
            client.get("/test/")

    @patch("requests.Session.request")
    def test_response_without_detail_field(self, mock_request, client):
        """Test error response without detail field."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_request.return_value = mock_response

        with pytest.raises(NotFoundError) as exc_info:
            client.get("/test/")

        assert "Not found" in str(exc_info.value.message)

    @patch("requests.Session.request")
    def test_custom_retry_after_header_invalid(self, mock_request, client):
        """Test invalid X-Retry-After header is handled."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {"X-Retry-After": "invalid"}
        mock_response.json.return_value = {"detail": "Rate limited"}
        mock_request.return_value = mock_response

        with pytest.raises(RateLimitError):
            client.get("/test/")

        # Should use default delay instead of crashing
