# API Authentication

> **Spec**: 026-api-webhook-ecosystem
> **Version**: 1.0
> **Date**: 2026-01-23

## Overview

The Sattva API supports two authentication methods:

1. **Session Tokens** - For web UI and user-facing applications
2. **API Keys** - For programmatic access and integrations

This guide covers both methods, including how to create and manage API keys, understand rate limiting, and implement secure authentication in your applications.

## Authentication Methods

### Method 1: Session Token (Bearer Authentication)

Used by web applications and authenticated users.

#### Request Format

```http
GET /api/v1/streams HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

#### How to Get a Session Token

Session tokens are obtained through the authentication endpoints:

```http
POST /api/v1/auth/login HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Token Refresh

Session tokens expire after 1 hour. Refresh them using:

```http
POST /api/v1/auth/refresh HTTP/1.1
Host: api.example.com
Authorization: Bearer <access_token>
```

### Method 2: API Key (X-API-Key Header)

Used for programmatic access, integrations, and third-party applications.

#### Request Format

```http
GET /api/v1/streams HTTP/1.1
Host: api.example.com
X-API-Key: sk_live_abc123xyz789...
```

#### How to Get an API Key

API keys are created through the API or web UI.

##### Creating via API

```http
POST /api/v1/keys HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "name": "Production Integration",
  "scopes": ["read:streams", "write:streams"],
  "rate_limit": 1000
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Production Integration",
  "key": "sk_live_abc123xyz789...",
  "scopes": ["read:streams", "write:streams"],
  "rate_limit": 1000,
  "is_active": true,
  "created_at": "2026-01-23T10:00:00Z"
}
```

> **⚠️ Critical**: Copy the key value now. You won't be able to see it again.

##### Creating via Web UI

1. Navigate to **Settings** → **API Keys**
2. Click **Create API Key**
3. Enter name, scopes, and rate limit
4. Copy the generated key

## API Key Management

### Listing API Keys

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
      "name": "Production Integration",
      "scopes": ["read:streams", "write:streams"],
      "rate_limit": 1000,
      "is_active": true,
      "last_used": "2026-01-23T10:30:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 3
}
```

### Revoking API Keys

```http
DELETE /api/v1/keys/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

### Updating API Keys

```http
PATCH /api/v1/keys/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "name": "Updated Name",
  "scopes": ["read:streams"],
  "rate_limit": 500,
  "is_active": false
}
```

## Scopes

API keys use scopes to limit access to specific resources and actions.

### Available Scopes

| Scope | Description | Example Endpoints |
|-------|-------------|-------------------|
| `read:streams` | Read stream information | `GET /streams` |
| `write:streams` | Start/stop/restart streams | `POST /streams/{id}/start` |
| `read:channels` | Read channel information | `GET /channels` |
| `write:channels` | Create/update/delete channels | `POST /channels` |
| `read:playlists` | Read playlist information | `GET /playlists` |
| `write:playlists` | Create/update/delete playlists | `POST /playlists` |
| `read:webhooks` | Read webhook subscriptions | `GET /webhooks` |
| `write:webhooks` | Create/update/delete webhooks | `POST /webhooks` |
| `admin` | Full administrative access | All endpoints |

### Scope Examples

#### Read-Only Key

```json
{
  "name": "Monitoring Dashboard",
  "scopes": ["read:streams", "read:channels", "read:playlists"]
}
```

#### Stream Management Key

```json
{
  "name": "Stream Automation",
  "scopes": ["read:streams", "write:streams"]
}
```

#### Full Access Key

```json
{
  "name": "Production Integration",
  "scopes": ["admin"]
}
```

## Rate Limiting

### How Rate Limiting Works

Rate limits are enforced **per API key** using a sliding window algorithm.

### Rate Limit Tiers

| Tier | Requests | Window | Use Case |
|------|----------|--------|----------|
| Standard | 100 | 1 hour | Development, testing |
| Premium | 1,000 | 1 hour | Production applications |
| Enterprise | 10,000 | 1 hour | High-volume integrations |

### Rate Limit Headers

All API responses include rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706107200
X-RateLimit-Scope: api_key
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Remaining requests in current window |
| `X-RateLimit-Reset` | Unix timestamp when window resets |
| `X-RateLimit-Scope` | Scope of rate limit (api_key or ip) |

### Handling Rate Limits

When you exceed the rate limit, you'll receive:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706107200
Retry-After: 3600

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

#### Automatic Retry Strategy

Implement exponential backoff for automatic retries:

##### Python

```python
import time
from requests import Session

class SattvaClient:
    def __init__(self, api_key: str):
        self.session = Session()
        self.session.headers.update({"X-API-Key": api_key})
        self.max_retries = 3

    def request_with_retry(self, method: str, url: str, **kwargs):
        for attempt in range(self.max_retries):
            response = self.session.request(method, url, **kwargs)

            if response.status_code != 429:
                return response

            # Calculate delay with exponential backoff
            retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
            time.sleep(retry_after)

        return response
```

##### JavaScript

```javascript
async function requestWithRetry(url, options, maxRetries = 3) {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        const response = await fetch(url, options);

        if (response.status !== 429) {
            return response;
        }

        // Calculate delay with exponential backoff
        const retryAfter = parseInt(response.headers.get('Retry-After') || (2 ** attempt));
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    }

    return response;
}
```

##### Go

```go
func (c *Client) requestWithRetry(req *http.Request) (*http.Response, error) {
    maxRetries := 3

    for attempt := 0; attempt < maxRetries; attempt++ {
        resp, err := c.doRequest(req)
        if err != nil {
            return nil, err
        }

        if resp.StatusCode != 429 {
            return resp, nil
        }

        // Calculate delay with exponential backoff
        retryAfter := getRetryAfter(resp.Header)
        delay := time.Duration(retryAfter) * time.Second
        time.Sleep(delay)
    }

    return resp, nil
}
```

## Security Best Practices

### 1. Secure Storage

#### Environment Variables

```bash
# .env file (never commit this)
SATTVA_API_KEY=sk_live_abc123xyz789...
```

#### Environment Variable Usage

##### Python

```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SATTVA_API_KEY")
client = SattvaClient(api_key=api_key)
```

##### JavaScript

```javascript
require('dotenv').config();

const apiKey = process.env.SATTVA_API_KEY;
const client = new SattvaClient({ apiKey });
```

##### Go

```go
import (
    "os"
    "github.com/joho/godotenv"
)

func main() {
    godotenv.Load()

    apiKey := os.Getenv("SATTVA_API_KEY")
    client := sattva.NewClient(apiKey)
}
```

### 2. Use HTTPS Only

All API requests must use HTTPS:

```bash
# ✅ Good
curl https://api.example.com/api/v1/streams \
  -H "X-API-Key: sk_live_abc123xyz789"

# ❌ Bad - Never use HTTP
curl http://api.example.com/api/v1/streams \
  -H "X-API-Key: sk_live_abc123xyz789"
```

### 3. Never Commit Keys to Git

Add to `.gitignore`:

```
.env
*.env.local
secrets.txt
api-keys.txt
```

### 4. Rotate Keys Regularly

Best practice: Rotate API keys every 90 days.

```bash
# Create new key
curl -X POST "https://api.example.com/api/v1/keys" \
  -H "Authorization: Bearer <session_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Key", "scopes": ["read:streams"]}'

# Update application with new key

# Revoke old key
curl -X DELETE "https://api.example.com/api/v1/keys/{old_key_id}" \
  -H "Authorization: Bearer <session_token>"
```

### 5. Use Least Privilege

Only grant scopes that are necessary:

```json
{
  "name": "Analytics Bot",
  "scopes": ["read:streams", "read:channels"]
}
```

### 6. Monitor API Key Usage

Regularly check key usage:

```bash
curl -X GET "https://api.example.com/api/v1/keys" \
  -H "Authorization: Bearer <session_token>"
```

Look for:
- Unusual `last_used` timestamps
- High `failure_count` on webhooks
- Unexpected IP addresses (if logged)

### 7. Implement Webhook Signature Verification

Always verify webhook signatures:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    computed = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, computed)
```

See [Webhooks Guide](./webhooks.md#webhook-signatures) for details.

## Authentication Errors

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `authentication_failed` | Invalid credentials | Check API key or session token |
| `token_expired` | Session token expired | Refresh the token |
| `insufficient_scope` | API key lacks required scope | Add required scope to API key |
| `key_revoked` | API key has been revoked | Create new API key |
| `rate_limit_exceeded` | Rate limit exceeded | Implement retry logic |

### Error Response Format

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "Invalid API key",
    "details": {
      "hint": "Check that your API key is correct and active"
    }
  }
}
```

## Code Examples

### Python SDK

```python
from sattva_api import SattvaClient

# Initialize with API key
client = SattvaClient(api_key='sk_live_abc123xyz789')

# Make requests
streams = client.streams.list()
```

### JavaScript SDK

```javascript
import { SattvaClient } from '@sattva/sdk';

// Initialize with API key
const client = new SattvaClient({
    apiKey: 'sk_live_abc123xyz789'
});

// Make requests
const streams = await client.streams.list();
```

### Go SDK

```go
import "github.com/sattva/sattva-go-sdk"

// Initialize with API key
client := sattva.NewClient("sk_live_abc123xyz789")

// Make requests
streams, err := client.Streams().List(context.Background(), nil)
```

### cURL

```bash
# List streams
curl -X GET "https://api.example.com/api/v1/streams" \
  -H "X-API-Key: sk_live_abc123xyz789"

# Start stream
curl -X POST "https://api.example.com/api/v1/streams/{id}/start" \
  -H "X-API-Key: sk_live_abc123xyz789"
```

## Implementation

### Backend

- **Auth Dependencies**: `backend/src/api/auth/dependencies.py`
- **API Keys Router**: `backend/src/api/api_keys.py`
- **Rate Limiting**: `backend/src/services/rate_limit_service.py`
- **Middleware**: `backend/src/frameworks/http/middleware/rate_limiter.py`

### Database Schema

```sql
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
```

## Related Documents

- [API Reference](./reference.md)
- [Webhooks Guide](./webhooks.md)
- [API Versioning](./versioning.md)
- [Python SDK Guide](./sdk-python.md)
- [JavaScript SDK Guide](./sdk-javascript.md)
- [Go SDK Guide](./sdk-go.md)
- [026-api-webhook-ecosystem Spec](../../specs/026-api-webhook-ecosystem/)
