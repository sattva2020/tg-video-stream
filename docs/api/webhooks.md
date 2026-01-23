# Webhooks API

> **Spec**: 026-api-webhook-ecosystem
> **Version**: 1.0
> **Date**: 2026-01-23

## Overview

Webhooks enable real-time event notifications from the Sattva platform to external systems. When events occur (such as stream lifecycle changes, viewer milestones, or system errors), HTTP POST requests are sent to subscribed URLs with event payloads.

## How Webhooks Work

```
┌─────────────┐      Event        ┌──────────────┐     HTTP POST     ┌────────────┐
│   Sattva    │ ──────────────────> │  Webhook     │ ──────────────────> │  Your      │
│  Platform   │   Triggered        │  Worker      │   With Signature   │  Endpoint  │
└─────────────┘                    └──────────────┘                    └────────────┘
                                          │                                  │
                                          v                                  v
                                  ┌──────────────┐                  ┌────────────┐
                                  │   Delivery   │                  │  Process   │
                                  │    Retry     │<─────────────────│   Event    │
                                  │   Logic      │    200 OK        │            │
                                  └──────────────┘                  └────────────┘
```

## Webhook Endpoints

### GET /webhooks

List all webhook subscriptions.

```http
GET /api/v1/webhooks HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

**Response:**

```json
{
  "webhooks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://example.com/webhook",
      "event_types": ["stream.started", "stream.stopped"],
      "is_active": true,
      "last_success_at": "2026-01-23T10:30:00Z",
      "last_failure_at": null,
      "failure_count": 0,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 3
}
```

### POST /webhooks

Create a new webhook subscription.

```http
POST /api/v1/webhooks HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "url": "https://example.com/webhook",
  "event_types": ["stream.started", "stream.stopped", "stream.error"]
}
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Webhook endpoint URL (HTTPS required, max 2048 chars) |
| `event_types` | array | Yes | List of event types to subscribe to |

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/webhook",
  "event_types": ["stream.started", "stream.stopped", "stream.error"],
  "secret": "whsec_abc123xyz789...",
  "is_active": true,
  "created_at": "2026-01-23T10:00:00Z"
}
```

> **⚠️ Security**: Store the secret securely. You'll need it to verify webhook signatures.

### GET /webhooks/{webhook_id}

Get webhook details.

```http
GET /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

### PATCH /webhooks/{webhook_id}

Update webhook subscription.

```http
PATCH /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "url": "https://example.com/webhook-v2",
  "event_types": ["stream.started", "stream.stopped"]
}
```

### DELETE /webhooks/{webhook_id}

Delete a webhook subscription.

```http
DELETE /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

### POST /webhooks/{webhook_id}/test

Send a test webhook event.

```http
POST /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/test HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

**Response:**

```json
{
  "success": true,
  "message": "Test webhook sent successfully",
  "response": {
    "status_code": 200,
    "body": "OK"
  }
}
```

### POST /webhooks/{webhook_id}/rotate-secret

Rotate webhook secret.

```http
POST /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/rotate-secret HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "secret": "whsec_new123xyz789...",
  "message": "Secret rotated successfully"
}
```

> **⚠️ Important**: Update your endpoint with the new secret immediately after rotation.

### GET /webhooks/{webhook_id}/events

List webhook delivery events.

```http
GET /api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/events?limit=20&status=failed HTTP/1.1
Host: api.example.com
Authorization: Bearer <session_token>
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Number of records (1-100) |
| `offset` | int | 0 | Pagination offset |
| `status` | string | — | Filter by status (pending, success, failed, retrying) |

**Response:**

```json
{
  "events": [
    {
      "id": 12345,
      "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "stream.started",
      "event_id": "evt_abc123xyz789",
      "status": "success",
      "attempt_number": 1,
      "attempted_at": "2026-01-23T10:30:00Z",
      "response_status_code": 200,
      "duration_ms": 145,
      "should_retry": false
    }
  ],
  "total": 42
}
```

## Event Types

### Stream Events

| Event | Description | Payload |
|-------|-------------|---------|
| `stream.started` | Stream started successfully | Stream details |
| `stream.stopped` | Stream stopped normally | Stream details |
| `stream.paused` | Stream paused | Stream details |
| `stream.resumed` | Stream resumed after pause | Stream details |
| `stream.error` | Stream encountered error | Stream + error details |

### Viewer Events

| Event | Description | Payload |
|-------|-------------|---------|
| `viewer.milestone` | Viewer count reached milestone | Stream + milestone |
| `viewer.joined` | Viewer joined stream | Stream + viewer info |
| `viewer.left` | Viewer left stream | Stream + viewer info |

### Track Events

| Event | Description | Payload |
|-------|-------------|---------|
| `track.started` | Track started playing | Stream + track info |
| `track.completed` | Track finished playing | Stream + track info |
| `track.failed` | Track failed to play | Stream + track + error |
| `track.skipped` | Track skipped | Stream + track info |

### System Events

| Event | Description | Payload |
|-------|-------------|---------|
| `webhook.test` | Test webhook event | Test message |
| `system.status` | System status update | System info |

## Event Payload Format

All webhook payloads follow this structure:

```json
{
  "id": "evt_abc123xyz789",
  "event_type": "stream.started",
  "timestamp": "2026-01-23T10:30:00Z",
  "data": {
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "active",
    "started_at": "2026-01-23T10:30:00Z",
    "viewer_count": 42
  }
}
```

### Stream Started Example

```json
{
  "id": "evt_abc123xyz789",
  "event_type": "stream.started",
  "timestamp": "2026-01-23T10:30:00Z",
  "data": {
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel_id": "550e8400-e29b-41d4-a716-446655440001",
    "channel_name": "Music Channel",
    "status": "active",
    "started_at": "2026-01-23T10:30:00Z",
    "viewer_count": 0
  }
}
```

### Viewer Milestone Example

```json
{
  "id": "evt_def456uvw123",
  "event_type": "viewer.milestone",
  "timestamp": "2026-01-23T11:00:00Z",
  "data": {
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel_id": "550e8400-e29b-41d4-a716-446655440001",
    "viewer_count": 100,
    "milestone": 100,
    "timestamp": "2026-01-23T11:00:00Z"
  }
}
```

### Stream Error Example

```json
{
  "id": "evt_ghi789rst456",
  "event_type": "stream.error",
  "timestamp": "2026-01-23T12:00:00Z",
  "data": {
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel_id": "550e8400-e29b-41d4-a716-446655440001",
    "error": "Connection timeout",
    "error_code": "CONNECTION_TIMEOUT",
    "timestamp": "2026-01-23T12:00:00Z"
  }
}
```

## Webhook Signatures

All webhook requests include signatures for security verification.

### Headers

```http
X-Webhook-Signature: sha256=<signature>
X-Webhook-Timestamp: 1706011200
X-Webhook-ID: evt_abc123xyz789
```

### Signature Format

The signature is computed as:

```python
import hmac
import hashlib
import json

payload = json.dumps(request.json, separators=(',', ':'), sort_keys=True)
signature = hmac.new(
    secret.encode('utf-8'),
    payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

### Verifying Signatures

#### Python

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload, signature, secret):
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, computed_signature)

# Usage
payload = json.dumps(request.json, separators=(',', ':'), sort_keys=True)
signature = request.headers['X-Webhook-Signature'].replace('sha256=', '')
is_valid = verify_webhook_signature(payload, signature, WEBHOOK_SECRET)

if not is_valid:
    return 'Invalid signature', 401
```

#### JavaScript/Node.js

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
    const computedSignature = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');

    // Use constant-time comparison
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(computedSignature)
    );
}

// Usage
const payload = JSON.stringify(req.body);
const signature = req.headers['x-webhook-signature'].replace('sha256=', '');
const isValid = verifyWebhookSignature(payload, signature, WEBHOOK_SECRET);

if (!isValid) {
    return res.status(401).send('Invalid signature');
}
```

#### Go

```go
import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
)

func verifyWebhookSignature(payload []byte, signature string, secret string) bool {
    h := hmac.New(sha256.New, []byte(secret))
    h.Write(payload)
    computedSignature := hex.EncodeToString(h.Sum(nil))

    return hmac.Equal([]byte(signature), []byte(computedSignature))
}

// Usage
payload, _ := json.Marshal(req.Body)
signature := strings.TrimPrefix(req.Header.Get("X-Webhook-Signature"), "sha256=")
isValid := verifyWebhookSignature(payload, signature, webhookSecret)

if !isValid {
    http.Error(w, "Invalid signature", http.StatusUnauthorized)
    return
}
```

## Handling Webhooks

### Best Practices

1. **Return 200 OK quickly**: Process events asynchronously
2. **Verify signatures**: Always verify webhook signatures
3. **Handle duplicates**: Check `event_id` for duplicate events
4. **Retry logic**: Implement exponential backoff for retries
5. **Idempotency**: Make your handlers idempotent
6. **HTTPS only**: Always use HTTPS endpoints
7. **Timeout handling**: Respond within 30 seconds

### Example Endpoint (Python/FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json

app = FastAPI()
WEBHOOK_SECRET = "whsec_abc123xyz789..."

def verify_signature(payload: str, signature: str) -> bool:
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Get signature
    signature = request.headers.get("X-Webhook-Signature", "").replace("sha256=", "")

    # Get raw payload
    payload = await request.body()

    # Verify signature
    if not verify_signature(payload.decode(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    event = await request.json()

    # Check for duplicates (using event_id)
    event_id = event.get("id")
    if await is_duplicate_event(event_id):
        return {"status": "duplicate"}

    # Process event asynchronously
    await process_webhook_event(event)

    # Return immediately
    return {"status": "ok"}

async def is_duplicate_event(event_id: str) -> bool:
    # Check Redis/database for event_id
    return await redis.exists(f"webhook:event:{event_id}")

async def process_webhook_event(event: dict):
    # Mark as received
    event_id = event["id"]
    await redis.setex(f"webhook:event:{event_id}", 86400, "1")

    # Handle event type
    event_type = event["event_type"]

    if event_type == "stream.started":
        await handle_stream_started(event["data"])
    elif event_type == "viewer.milestone":
        await handle_viewer_milestone(event["data"])
    # ... other event types
```

### Example Endpoint (JavaScript/Express)

```javascript
const express = require('express');
const crypto = require('crypto');
const app = express();

const WEBHOOK_SECRET = 'whsec_abc123xyz789...';

function verifySignature(payload, signature) {
    const computed = crypto
        .createHmac('sha256', WEBHOOK_SECRET)
        .update(payload)
        .digest('hex');

    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(computed)
    );
}

app.post('/webhook', express.raw({type: 'application/json'}), (req, res) => {
    const signature = req.headers['x-webhook-signature'].replace('sha256=', '');
    const payload = req.body;

    // Verify signature
    if (!verifySignature(payload, signature)) {
        return res.status(401).send('Invalid signature');
    }

    const event = JSON.parse(payload);

    // Check for duplicates
    if (isDuplicateEvent(event.id)) {
        return res.status(200).json({ status: 'duplicate' });
    }

    // Process asynchronously
    processWebhookEvent(event).catch(console.error);

    // Return immediately
    res.status(200).json({ status: 'ok' });
});

function isDuplicateEvent(eventId) {
    return redis.exists(`webhook:event:${eventId}`);
}

async function processWebhookEvent(event) {
    // Mark as received
    await redis.setex(`webhook:event:${event.id}`, 86400, '1');

    // Handle event type
    switch (event.event_type) {
        case 'stream.started':
            await handleStreamStarted(event.data);
            break;
        case 'viewer.milestone':
            await handleViewerMilestone(event.data);
            break;
        // ... other event types
    }
}
```

## Delivery and Retry Logic

### Delivery Attempts

Webhooks are delivered with exponential backoff retry logic:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

### Delivery Status

You can check delivery status via the API:

```http
GET /api/v1/webhooks/{webhook_id}/events?status=failed
```

### Automatic Disabling

Webhooks are automatically disabled after **5 consecutive failures**. You'll need to investigate and re-enable the webhook manually.

### Event Deduplication

Each event has a unique `event_id`. The system prevents duplicate delivery of the same event within 24 hours.

## Testing Webhooks

### Using the Test Endpoint

```bash
curl -X POST "https://api.example.com/api/v1/webhooks/{webhook_id}/test" \
  -H "Authorization: Bearer <session_token>"
```

This sends a test event:

```json
{
  "id": "evt_test000000000000000000",
  "event_type": "webhook.test",
  "timestamp": "2026-01-23T10:30:00Z",
  "data": {
    "test": true,
    "message": "This is a test webhook event"
  }
}
```

### Using Local Tunnel for Development

Use tools like **ngrok** or **localtunnel** to test webhooks locally:

```bash
# Using ngrok
ngrok http 3000

# Create webhook with ngrok URL
curl -X POST "https://api.example.com/api/v1/webhooks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/webhook",
    "event_types": ["stream.started"]
  }'
```

## Monitoring and Debugging

### Check Webhook Health

```bash
curl -X GET "https://api.example.com/api/v1/webhooks/{webhook_id}" \
  -H "Authorization: Bearer <token>"
```

Response includes health indicators:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "is_active": true,
  "last_success_at": "2026-01-23T10:30:00Z",
  "last_failure_at": null,
  "failure_count": 0
}
```

### View Delivery Logs

```bash
curl -X GET "https://api.example.com/api/v1/webhooks/{webhook_id}/events?limit=50" \
  -H "Authorization: Bearer <token>"
```

## Implementation

### Backend

- **Router**: `backend/src/api/webhooks.py`
- **Service**: `backend/src/services/webhook_service.py`
- **Worker**: `backend/src/services/webhook_worker.py`
- **Models**: `backend/src/models/webhook.py`, `backend/src/models/webhook_event.py`

### Database Schema

```sql
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

CREATE TABLE webhook_events (
    id BIGSERIAL PRIMARY KEY,
    webhook_id UUID REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    attempt_number INTEGER NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_status_code INTEGER,
    response_body TEXT,
    response_headers JSONB,
    should_retry BOOLEAN DEFAULT FALSE,
    next_retry_at TIMESTAMPTZ,
    duration_ms INTEGER
);

CREATE INDEX idx_webhook_events_webhook_id ON webhook_events(webhook_id);
CREATE INDEX idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX idx_webhook_events_status ON webhook_events(status);
```

## Related Documents

- [API Reference](./reference.md)
- [Authentication Guide](./authentication.md)
- [Python SDK Guide](./sdk-python.md#webhooks)
- [JavaScript SDK Guide](./sdk-javascript.md#webhooks)
- [Go SDK Guide](./sdk-go.md#webhooks)
- [026-api-webhook-ecosystem Spec](../../specs/026-api-webhook-ecosystem/)
