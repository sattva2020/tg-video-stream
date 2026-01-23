# Sattva API Python SDK

Official Python SDK for the Sattva API - a comprehensive streaming platform API.

## Installation

```bash
pip install sattva-api
```

## Quick Start

```python
from sattva_api import SattvaClient

# Initialize the client with your API key
client = SattvaClient(
    api_key="your-api-key-here",
    base_url="https://api.sattva.io/api/v1"
)

# List streams
streams = client.streams.list()
for stream in streams:
    print(f"Stream: {stream['name']} - {stream['status']}")

# Start a stream
response = client.streams.start(channel_id="channel-123")
print(f"Stream started: {response}")

# Create a webhook subscription
webhook = client.webhooks.create(
    url="https://example.com/webhooks",
    event_types=["stream.started", "stream.stopped"]
)
print(f"Webhook created: {webhook}")
```

## Authentication

The SDK uses API keys for authentication. You can create API keys through the Sattva dashboard or API.

```python
client = SattvaClient(
    api_key="sk_live_xxxxxxxxxxxx",  # Your API key
    base_url="https://api.sattva.io/api/v1"
)
```

### API Key Security

- Never commit API keys to version control
- Use environment variables for API keys in production
- Rotate API keys regularly
- Use different keys for development and production

## Features

- **Stream Management**: Start, stop, pause, and resume streams
- **Playlist Control**: Manage playlists, tracks, and playback
- **Channel Management**: Configure and control streaming channels
- **Webhook Subscriptions**: Subscribe to real-time events
- **API Key Management**: Create and manage API keys
- **Rate Limiting**: Built-in rate limit handling

## Resources

### Streams

```python
# List all streams
streams = client.streams.list()

# Get a specific stream
stream = client.streams.get(stream_id="stream-123")

# Start a stream
response = client.streams.start(channel_id="channel-123")

# Stop a stream
response = client.streams.stop(stream_id="stream-123")

# Pause a stream
response = client.streams.pause(stream_id="stream-123")

# Resume a stream
response = client.streams.resume(stream_id="stream-123")
```

### Playlists

```python
# List playlists
playlists = client.playlists.list()

# Get a playlist
playlist = client.playlists.get(playlist_id="playlist-123")

# Create a playlist
playlist = client.playlists.create(
    name="My Playlist",
    description="A great playlist"
)

# Update a playlist
playlist = client.playlists.update(
    playlist_id="playlist-123",
    name="Updated Name"
)

# Delete a playlist
client.playlists.delete(playlist_id="playlist-123")
```

### Channels

```python
# List channels
channels = client.channels.list()

# Get a channel
channel = client.channels.get(channel_id="channel-123")

# Create a channel
channel = client.channels.create(
    name="My Channel",
    url="https://example.com/stream"
)

# Update a channel
channel = client.channels.update(
    channel_id="channel-123",
    name="Updated Channel"
)

# Delete a channel
client.channels.delete(channel_id="channel-123")
```

### Webhooks

```python
# List webhooks
webhooks = client.webhooks.list()

# Get a webhook
webhook = client.webhooks.get(webhook_id="webhook-123")

# Create a webhook
webhook = client.webhooks.create(
    url="https://example.com/webhooks",
    event_types=["stream.started", "stream.stopped", "stream.error"]
)

# Test a webhook
result = client.webhooks.test(webhook_id="webhook-123")

# Rotate webhook secret
webhook = client.webhooks.rotate_secret(webhook_id="webhook-123")

# Delete a webhook
client.webhooks.delete(webhook_id="webhook-123")
```

### API Keys

```python
# List API keys
keys = client.api_keys.list()

# Create an API key
key = client.api_keys.create(
    name="My Integration",
    scopes=["read:streams", "write:streams"]
)
# Save the key value - it won't be shown again
api_key_value = key["key"]

# Revoke an API key
client.api_keys.revoke(key_id="key-123")
```

## Error Handling

The SDK raises exceptions for API errors:

```python
from sattva_api import SattvaClient
from sattva_api.exceptions import (
    SattvaAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError
)

client = SattvaClient(api_key="your-api-key")

try:
    stream = client.streams.get(stream_id="stream-123")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e.retry_after}")
except NotFoundError:
    print("Stream not found")
except SattvaAPIError as e:
    print(f"API error: {e}")
```

## Rate Limiting

The SDK automatically handles rate limiting:

```python
client = SattvaClient(
    api_key="your-api-key",
    max_retries=3,  # Number of retries on rate limit
    retry_delay=1.0  # Delay between retries (seconds)
)
```

## Webhook Signature Verification

Verify webhook signatures to ensure requests are from Sattva:

```python
from sattva_api import verify_webhook_signature
import json

def webhook_handler(request):
    payload = request.body
    signature = request.headers.get('X-Sattva-Signature')
    secret = 'your-webhook-secret'

    if verify_webhook_signature(payload, signature, secret):
        event = json.loads(payload)
        print(f"Received event: {event['type']}")
        # Process event
    else:
        print("Invalid signature")
```

## Development

### Installation for Development

```bash
git clone https://github.com/sattva/sattva-python-sdk.git
cd sattva-python-sdk
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v --cov=sattva_api
```

### Code Formatting

```bash
black sattva_api tests
ruff check sattva_api tests
mypy sattva_api
```

## API Reference

Full API documentation is available at [https://docs.sattva.io](https://docs.sattva.io)

## Event Types

The following webhook events are available:

- `stream.started` - Stream has started
- `stream.stopped` - Stream has stopped
- `stream.paused` - Stream has been paused
- `stream.resumed` - Stream has been resumed
- `stream.error` - Stream encountered an error
- `viewer.milestone` - Viewer milestone reached
- `viewer.joined` - Viewer joined the stream
- `viewer.left` - Viewer left the stream
- `track.started` - Track started playing
- `track.completed` - Track finished playing
- `track.failed` - Track failed to play
- `track.skipped` - Track was skipped

## Support

- Documentation: [https://docs.sattva.io](https://docs.sattva.io)
- Bug Reports: [GitHub Issues](https://github.com/sattva/sattva-python-sdk/issues)
- Email: api@sattva.io

## License

MIT License - see LICENSE file for details
