# API Reference

> **Spec**: 026-api-webhook-ecosystem
> **Version**: 1.0
> **Date**: 2026-01-23

## Overview

Comprehensive REST API for all platform operations including stream management, playlist control, webhook subscriptions, and API key management. The API uses versioned endpoints (currently v1) and supports authentication via both session tokens and API keys.

## Base URL

```
https://api.example.com/api/v1
```

## Authentication

The API supports two authentication methods:

### 1. Session Token (User Authentication)

For web UI and user operations:

```http
Authorization: Bearer <session_token>
```

### 2. API Key (Programmatic Access)

For integrations and third-party applications:

```http
X-API-Key: <api_key>
```

See [Authentication Guide](./authentication.md) for detailed information.

## Rate Limiting

Rate limits are enforced per API key:

| Tier | Requests | Window |
|------|----------|--------|
| Standard | 100 | 1 hour |
| Premium | 1000 | 1 hour |
| Enterprise | 10000 | 1 hour |

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706107200
X-RateLimit-Scope: api_key
```

See [Authentication Guide](./authentication.md#rate-limiting) for details.

## Core Endpoints

### Streams

#### GET /streams

List all streams with pagination and filtering.

```http
GET /api/v1/streams?limit=20&offset=0&status=active HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Number of records (1-100) |
| `offset` | int | 0 | Pagination offset |
| `status` | string | — | Filter by status (active, stopped, error) |
| `channel_id` | string | — | Filter by channel UUID |

**Response:**

```json
{
  "streams": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "active",
      "started_at": "2026-01-23T10:30:00Z",
      "viewer_count": 42
    }
  ],
  "total": 100
}
```

#### POST /streams/{stream_id}/start

Start a stream for a channel.

```http
POST /api/v1/streams/550e8400-e29b-41d4-a716-446655440000/start HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

**Required Scopes:** `write:streams`

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "started_at": "2026-01-23T10:30:00Z"
}
```

#### POST /streams/{stream_id}/stop

Stop an active stream.

```http
POST /api/v1/streams/550e8400-e29b-41d4-a716-446655440000/stop HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

**Required Scopes:** `write:streams`

#### POST /streams/{stream_id}/restart

Restart a stopped or errored stream.

```http
POST /api/v1/streams/550e8400-e29b-41d4-a716-446655440000/restart HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

**Required Scopes:** `write:streams`

### Channels

#### GET /channels

List all channels.

```http
GET /api/v1/channels HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

#### POST /channels

Create a new channel.

```http
POST /api/v1/channels HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
Content-Type: application/json

{
  "name": "My Channel",
  "description": "Music streaming channel"
}
```

**Required Scopes:** `write:channels`

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Channel",
  "description": "Music streaming channel",
  "created_at": "2026-01-23T10:00:00Z"
}
```

#### GET /channels/{channel_id}

Get channel details.

```http
GET /api/v1/channels/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

#### PATCH /channels/{channel_id}

Update channel information.

```http
PATCH /api/v1/channels/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
Content-Type: application/json

{
  "name": "Updated Channel Name"
}
```

**Required Scopes:** `write:channels`

#### DELETE /channels/{channel_id}

Delete a channel.

```http
DELETE /api/v1/channels/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

**Required Scopes:** `write:channels`

### Playlists

#### GET /playlists

List all playlists.

```http
GET /api/v1/playlists HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
```

#### POST /playlists

Create a new playlist.

```http
POST /api/v1/playlists HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
Content-Type: application/json

{
  "name": "My Playlist",
  "channel_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Required Scopes:** `write:playlists`

#### PATCH /playlists/{playlist_id}

Update playlist tracks.

```http
PATCH /api/v1/playlists/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
Content-Type: application/json

{
  "track_ids": ["track1", "track2", "track3"]
}
```

**Required Scopes:** `write:playlists`

#### POST /playlists/{playlist_id}/reorder

Reorder playlist tracks.

```http
POST /api/v1/playlists/550e8400-e29b-41d4-a716-446655440000/reorder HTTP/1.1
Host: api.example.com
X-API-Key: <api_key>
Content-Type: application/json

{
  "track_id": "track1",
  "new_position": 2
}
```

**Required Scopes:** `write:playlists`

### API Keys

#### GET /keys

List your API keys.

```http
GET /api/v1/keys HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

**Response:**

```json
{
  "keys": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Production Key",
      "scopes": ["read:streams", "write:streams"],
      "rate_limit": 1000,
      "is_active": true,
      "last_used": "2026-01-23T10:30:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 5
}
```

#### POST /keys

Create a new API key.

```http
POST /api/v1/keys HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "name": "Integration Key",
  "scopes": ["read:streams", "write:streams"],
  "rate_limit": 1000
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Integration Key",
  "key": "sk_live_abc123xyz789...",
  "scopes": ["read:streams", "write:streams"],
  "rate_limit": 1000,
  "is_active": true,
  "created_at": "2026-01-23T10:30:00Z"
}
```

> **⚠️ Security**: Copy the key value now. You won't be able to see it again.

#### DELETE /keys/{key_id}

Revoke an API key.

```http
DELETE /api/v1/keys/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

## Available Scopes

| Scope | Description |
|-------|-------------|
| `read:streams` | Read stream information |
| `write:streams` | Start/stop/restart streams |
| `read:channels` | Read channel information |
| `write:channels` | Create/update/delete channels |
| `read:playlists` | Read playlist information |
| `write:playlists` | Create/update/delete playlists |
| `read:webhooks` | Read webhook subscriptions |
| `write:webhooks` | Create/update/delete webhooks |
| `admin` | Full administrative access |

## Error Codes

| Code | Description | Retry |
|------|-------------|-------|
| 200 | Success | — |
| 400 | Bad Request | No |
| 401 | Unauthorized | No |
| 403 | Forbidden | No |
| 404 | Not Found | No |
| 422 | Validation Error | No |
| 429 | Rate Limit Exceeded | Yes |
| 500 | Server Error | Yes |
| 503 | Service Unavailable | Yes |

### Error Response Format

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Please retry later.",
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset_at": "2026-01-23T11:00:00Z"
    }
  }
}
```

## Versioning

The API uses URL-based versioning. Current version is `v1`.

### Specifying Version

**Method 1: URL Path (Recommended)**

```http
GET /api/v1/streams
```

**Method 2: Header**

```http
GET /api/streams
X-API-Version: v1
```

**Method 3: Default**

If no version is specified, the latest stable version is used.

### Version Headers

All responses include version information:

```http
X-API-Version: v1
X-API-Supported-Versions: v1, v2
X-API-Docs: https://docs.example.com/api/v1
```

See [API Versioning Guide](./versioning.md) for details.

## Code Examples

### Python

```python
from sattva_api import SattvaClient

client = SattvaClient(api_key='sk_live_abc123xyz789')

# List streams
streams = client.streams.list(status='active')
for stream in streams:
    print(f"Stream: {stream['id']}, Viewers: {stream['viewer_count']}")

# Start a stream
stream = client.streams.start('550e8400-e29b-41d4-a716-446655440000')
print(f"Stream started at {stream['started_at']}")
```

### JavaScript/TypeScript

```javascript
import { SattvaClient } from '@sattva/sdk';

const client = new SattvaClient({ apiKey: 'sk_live_abc123xyz789' });

// List streams
const streams = await client.streams.list({ status: 'active' });
streams.forEach(stream => {
  console.log(`Stream: ${stream.id}, Viewers: ${stream.viewerCount}`);
});

// Start a stream
const stream = await client.streams.start('550e8400-e29b-41d4-a716-446655440000');
console.log(`Stream started at ${stream.startedAt}`);
```

### cURL

```bash
# List streams
curl -X GET "https://api.example.com/api/v1/streams?status=active" \
  -H "X-API-Key: sk_live_abc123xyz789"

# Start a stream
curl -X POST "https://api.example.com/api/v1/streams/550e8400-e29b-41d4-a716-446655440000/start" \
  -H "X-API-Key: sk_live_abc123xyz789"
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "github.com/sattva/sattva-go-sdk"
)

func main() {
    client := sattva.NewClient("sk_live_abc123xyz789")

    // List streams
    streams, err := client.Streams().List(context.Background(), &sattva.StreamListOptions{
        Status: sattva.String("active"),
    })
    if err != nil {
        panic(err)
    }

    for _, stream := range streams {
        fmt.Printf("Stream: %s, Viewers: %d\n", stream.ID, stream.ViewerCount)
    }

    // Start a stream
    stream, err := client.Streams().Start(context.Background(), "550e8400-e29b-41d4-a716-446655440000")
    if err != nil {
        panic(err)
    }
    fmt.Printf("Stream started at %s\n", stream.StartedAt)
}
```

## Implementation

### Backend

- **Application**: `backend/src/frameworks/http/app.py`
- **API Keys Router**: `backend/src/api/api_keys.py`
- **Webhooks Router**: `backend/src/api/webhooks.py`
- **Auth Dependencies**: `backend/src/api/auth/dependencies.py`
- **Rate Limiting**: `backend/src/services/rate_limit_service.py`

### Database Schema

```sql
-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id),
    scopes JSONB NOT NULL,
    rate_limit INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_owner_id ON api_keys(owner_id);

-- Webhooks
CREATE TABLE webhooks (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES users(id),
    url VARCHAR(2048) NOT NULL,
    event_types JSONB NOT NULL,
    secret VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhooks_owner_id ON webhooks(owner_id);
```

## Related Documents

- [Authentication Guide](./authentication.md)
- [Webhooks Guide](./webhooks.md)
- [API Versioning](./versioning.md)
- [Python SDK Guide](./sdk-python.md)
- [JavaScript SDK Guide](./sdk-javascript.md)
- [Go SDK Guide](./sdk-go.md)
- [026-api-webhook-ecosystem Spec](../../specs/026-api-webhook-ecosystem/)
