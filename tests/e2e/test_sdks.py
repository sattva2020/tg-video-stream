"""
E2E Tests: SDK Functionality with Real API Endpoints
Spec: 026-api-webhook-ecosystem

Tests Python SDK functionality against real backend API endpoints.
These tests verify that the SDK works correctly with the actual API.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add Python SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdks" / "python"))

from sattva_api import SattvaClient, SattvaAPIError, AuthenticationError, RateLimitError


# ==================== Configuration ====================

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ==================== Fixtures ====================

@pytest.fixture
def db_session():
    """
    Database session fixture for creating test data.
    This creates a test user and API key for SDK testing.
    Uses the backend's db_session fixture if available.
    """
    from src.models.user import User
    from src.models.api_key import APIKey
    from src.services.api_key_service import APIKeyService
    from src.schemas.api_key import APIKeyCreate
    from src.database import SessionLocal

    db = SessionLocal()
    try:
        # Create test user
        user = User(
            email="sdk_e2e_test@example.com",
            google_id="sdk_e2e_test_123",
            status="approved",
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create API key for the user
        api_key_service = APIKeyService(db)
        key_data = APIKeyCreate(
            name="SDK E2E Test Key",
            scopes=["read:streams", "read:playlists", "read:channels", "read:webhooks", "write:webhooks"],
            rate_limit={"requests": 100, "window": 60}
        )
        api_key, raw_key = api_key_service.create_key(user.id, key_data)

        yield db, raw_key, api_key, user

    finally:
        # Clean up
        try:
            db.rollback()
            db.query(APIKey).filter_by(owner_id=user.id).delete()
            db.query(User).filter_by(id=user.id).delete()
            db.commit()
        except:
            pass
        finally:
            db.close()


@pytest.fixture
def api_key(db_session):
    """Extract API key from db_session fixture."""
    db, raw_key, api_key_obj, user = db_session
    return raw_key


@pytest.fixture
def sdk_client(api_key):
    """Create an SDK client instance with the test API key."""
    client = SattvaClient(
        api_key=api_key,
        base_url=BACKEND_URL,
        timeout=10
    )
    return client


# ==================== Client Initialization Tests ====================

def test_sdk_client_initialization(api_key):
    """Test that SDK client can be initialized with API key."""
    client = SattvaClient(api_key=api_key, base_url=BACKEND_URL)
    assert client is not None
    assert client.api_key == api_key
    assert client.base_url == BACKEND_URL


def test_sdk_client_context_manager(api_key):
    """Test that SDK client works as context manager."""
    with SattvaClient(api_key=api_key, base_url=BACKEND_URL) as client:
        assert client is not None
        assert client.api_key == api_key


# ==================== Authentication Tests ====================

def test_sdk_auth_with_valid_key(sdk_client):
    """Test that SDK can authenticate with valid API key."""
    # Try to access a protected endpoint
    response = sdk_client.streams.list()
    # Should succeed without authentication error
    assert isinstance(response, dict) or isinstance(response, list)


def test_sdk_auth_with_invalid_key():
    """Test that SDK fails with invalid API key."""
    client = SattvaClient(api_key="invalid_key_12345", base_url=BACKEND_URL)
    with pytest.raises(AuthenticationError):
        client.streams.list()


def test_sdk_auth_without_key():
    """Test that SDK fails without API key."""
    client = SattvaClient(base_url=BACKEND_URL)
    with pytest.raises((AuthenticationError, SattvaAPIError)):
        client.streams.list()


# ==================== Streams Resource Tests ====================

def test_sdk_streams_list(sdk_client):
    """Test listing streams via SDK."""
    response = sdk_client.streams.list()
    assert isinstance(response, dict) or isinstance(response, list)
    # Response could be empty list or dict with streams key


def test_sdk_streams_get(sdk_client):
    """Test getting stream details via SDK."""
    # First list streams to get a stream ID if available
    streams_list = sdk_client.streams.list()

    if isinstance(streams_list, dict) and "streams" in streams_list:
        streams = streams_list["streams"]
    else:
        streams = streams_list if isinstance(streams_list, list) else []

    if streams and len(streams) > 0:
        stream_id = streams[0].get("id") if isinstance(streams[0], dict) else streams[0]
        response = sdk_client.streams.get(stream_id)
        assert isinstance(response, dict)
    else:
        # No streams available, just test the method exists
        pytest.skip("No streams available to test get()")


# ==================== Channels Resource Tests ====================

def test_sdk_channels_list(sdk_client):
    """Test listing channels via SDK."""
    response = sdk_client.channels.list()
    assert isinstance(response, dict) or isinstance(response, list)


def test_sdk_channels_get(sdk_client):
    """Test getting channel details via SDK."""
    channels_list = sdk_client.channels.list()

    if isinstance(channels_list, dict) and "channels" in channels_list:
        channels = channels_list["channels"]
    else:
        channels = channels_list if isinstance(channels_list, list) else []

    if channels and len(channels) > 0:
        channel_id = channels[0].get("id") if isinstance(channels[0], dict) else channels[0]
        response = sdk_client.channels.get(channel_id)
        assert isinstance(response, dict)
    else:
        pytest.skip("No channels available to test get()")


# ==================== Playlists Resource Tests ====================

def test_sdk_playlists_list(sdk_client):
    """Test listing playlists via SDK."""
    response = sdk_client.playlists.list()
    assert isinstance(response, dict) or isinstance(response, list)


# ==================== API Keys Resource Tests ====================

def test_sdk_api_keys_list(sdk_client):
    """Test listing API keys via SDK."""
    response = sdk_client.api_keys.list()
    assert isinstance(response, dict) or isinstance(response, list)

    # Response should contain our test key but not expose the key value
    if isinstance(response, dict) and "keys" in response:
        keys = response["keys"]
        assert isinstance(keys, list)
        # Verify key value is not exposed in list
        for key in keys:
            assert "key" not in key or key.get("key") is None or key.get("key") == ""


# ==================== Webhooks Resource Tests ====================

def test_sdk_webhooks_list(sdk_client):
    """Test listing webhooks via SDK."""
    response = sdk_client.webhooks.list()
    assert isinstance(response, dict) or isinstance(response, list)


def test_sdk_webhooks_create_and_delete(sdk_client):
    """Test creating and deleting a webhook via SDK."""
    # Create a test webhook
    webhook_data = {
        "url": "https://example.com/test-webhook",
        "event_types": ["stream.started", "stream.stopped"]
    }

    create_response = sdk_client.webhooks.create(**webhook_data)
    assert isinstance(create_response, dict)
    assert "id" in create_response

    webhook_id = create_response["id"]

    try:
        # Verify webhook was created
        get_response = sdk_client.webhooks.get(webhook_id)
        assert isinstance(get_response, dict)
        assert get_response["id"] == webhook_id
        assert get_response["url"] == webhook_data["url"]
    finally:
        # Clean up: delete the webhook
        sdk_client.webhooks.delete(webhook_id)


def test_sdk_webhooks_update(sdk_client):
    """Test updating a webhook via SDK."""
    # Create a webhook first
    webhook_data = {
        "url": "https://example.com/test-webhook-update",
        "event_types": ["stream.started"]
    }

    create_response = sdk_client.webhooks.create(**webhook_data)
    webhook_id = create_response["id"]

    try:
        # Update the webhook
        update_data = {
            "url": "https://example.com/test-webhook-updated",
            "event_types": ["stream.started", "stream.stopped", "stream.error"]
        }

        update_response = sdk_client.webhooks.update(webhook_id, **update_data)
        assert isinstance(update_response, dict)
        assert update_response["id"] == webhook_id
        assert update_response["url"] == update_data["url"]

    finally:
        # Clean up
        sdk_client.webhooks.delete(webhook_id)


# ==================== Error Handling Tests ====================

def test_sdk_not_found_error(sdk_client):
    """Test that SDK properly handles 404 errors."""
    with pytest.raises((SattvaAPIError, Exception)):
        # Try to get a non-existent resource
        sdk_client.channels.get("non-existent-id-12345")


def test_sdk_validation_error(sdk_client):
    """Test that SDK properly handles validation errors."""
    with pytest.raises((SattvaAPIError, Exception)):
        # Try to create a webhook with invalid data
        sdk_client.webhooks.create(
            url="not-a-valid-url",
            event_types=["invalid.event.type"]
        )


# ==================== Rate Limiting Tests ====================

def test_sdk_rate_limiting(sdk_client):
    """Test that SDK handles rate limiting correctly."""
    # Make multiple requests rapidly
    # This might trigger rate limiting if the limit is low enough
    responses = []
    for i in range(5):
        try:
            response = sdk_client.streams.list()
            responses.append(response)
        except RateLimitError:
            # Expected if rate limit is exceeded
            break
        except Exception as e:
            # Other errors are okay for this test
            responses.append(None)

    # At least some requests should succeed
    assert len(responses) > 0


# ==================== Webhook Signature Verification Tests ====================

def test_sdk_webhook_signature_verification():
    """Test webhook signature verification using SDK utility."""
    from sattva_api import verify_webhook_signature

    # Test data
    secret = "test_webhook_secret_123"
    payload = '{"event": "stream.started", "timestamp": 1234567890}'

    # Generate a signature (simulating what the backend would send)
    import hmac
    import hashlib
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Verify the signature
    is_valid = verify_webhook_signature(payload, f"sha256={signature}", secret)
    assert is_valid is True

    # Test with invalid signature
    is_valid = verify_webhook_signature(payload, "sha256=invalid", secret)
    assert is_valid is False


# ==================== HTTP Client Tests ====================

def test_sdk_http_get_method(sdk_client):
    """Test SDK's HTTP GET method directly."""
    # Test making a raw HTTP GET request through the SDK
    response = sdk_client._get("/api/v1/streams")
    assert response is not None
    assert isinstance(response, dict) or isinstance(response, list)


def test_sdk_http_post_method(sdk_client):
    """Test SDK's HTTP POST method directly."""
    # Test making a raw HTTP POST request through the SDK
    # Create a webhook
    response = sdk_client._post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/test-http-post",
            "event_types": ["stream.started"]
        }
    )

    assert response is not None
    assert isinstance(response, dict)
    assert "id" in response

    # Clean up
    if "id" in response:
        try:
            sdk_client._delete(f"/api/v1/webhooks/{response['id']}")
        except:
            pass


# ==================== Timeout Tests ====================

def test_sdk_timeout_handling():
    """Test that SDK handles timeouts correctly."""
    client = SattvaClient(
        api_key="test_key",
        base_url="http://localhost:9999",  # Non-existent server
        timeout=1  # Short timeout
    )

    with pytest.raises((SattvaAPIError, Exception)):
        client.streams.list()


# ==================== Integration Test ====================

def test_sdk_full_workflow(sdk_client):
    """
    Test a complete workflow using the SDK:
    1. List channels
    2. List playlists
    3. Create a webhook
    4. Update the webhook
    5. List webhooks
    6. Delete the webhook
    """
    # 1. List channels
    channels = sdk_client.channels.list()
    assert channels is not None

    # 2. List playlists
    playlists = sdk_client.playlists.list()
    assert playlists is not None

    # 3. Create a webhook
    webhook = sdk_client.webhooks.create(
        url="https://example.com/e2e-test-webhook",
        event_types=["stream.started", "stream.stopped"]
    )
    assert "id" in webhook
    webhook_id = webhook["id"]

    try:
        # 4. Update the webhook
        updated = sdk_client.webhooks.update(
            webhook_id,
            url="https://example.com/e2e-test-webhook-updated",
            event_types=["stream.started", "stream.stopped", "stream.error"]
        )
        assert updated["id"] == webhook_id

        # 5. List webhooks and verify our webhook is there
        webhooks = sdk_client.webhooks.list()
        if isinstance(webhooks, dict) and "webhooks" in webhooks:
            webhook_ids = [w["id"] for w in webhooks["webhooks"]]
        elif isinstance(webhooks, list):
            webhook_ids = [w["id"] for w in webhooks]
        else:
            webhook_ids = []

        assert webhook_id in webhook_ids

    finally:
        # 6. Clean up - delete the webhook
        sdk_client.webhooks.delete(webhook_id)


# ==================== SDK Version Test ====================

def test_sdk_version():
    """Test that SDK version is accessible."""
    from sattva_api import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
