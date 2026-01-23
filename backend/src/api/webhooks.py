"""
Webhook Management Endpoints
Spec: 026-api-webhook-ecosystem

Endpoints for creating, listing, updating, deleting, and testing webhook subscriptions.
"""
import logging
import uuid
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.webhook import Webhook
from src.schemas.webhook import WebhookCreate, WebhookResponse, WebhookUpdate
from src.services.webhook_service import WebhookService
from src.api.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=list[WebhookResponse],
    summary="List all webhook subscriptions",
    description="""
Retrieves all webhook subscriptions owned by the currently authenticated user.

**Important:** The webhook secret is NEVER included in list responses for security reasons.
The secret is only returned once when you create a new webhook.

**Response includes:**
- Webhook metadata (id, url, event_types, is_active)
- Delivery statistics (last_success_at, last_failure_at, failure_count)
- Timestamps (created_at, updated_at)

**Authentication:** Requires valid JWT token or session cookie
    """,
    responses={
        200: {
            "description": "List of webhook subscriptions owned by the user",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                            "url": "https://example.com/webhooks",
                            "event_types": ["stream.started", "stream.ended", "stream.error"],
                            "is_active": True,
                            "last_success_at": "2025-01-15T10:30:00Z",
                            "last_failure_at": None,
                            "failure_count": 0,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-15T10:30:00Z",
                            "secret": None
                        }
                    ]
                }
            }
        }
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.get(
    "http://localhost:8000/api/webhooks/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
webhooks = response.json()
print(webhooks)
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/', {
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});
const webhooks = await response.json();
console.log(webhooks);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X GET "http://localhost:8000/api/webhooks/" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
                """
            }
        ]
    }
)
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)
    webhooks = service.list_webhooks(owner_id=current_user.id)

    # Convert to response format (secret field is None for list)
    result = []
    for webhook in webhooks:
        webhook_dict = {
            "id": webhook.id,
            "owner_id": webhook.owner_id,
            "url": webhook.url,
            "event_types": webhook.event_types,
            "is_active": webhook.is_active,
            "last_success_at": webhook.last_success_at,
            "last_failure_at": webhook.last_failure_at,
            "failure_count": webhook.failure_count,
            "created_at": webhook.created_at,
            "updated_at": webhook.updated_at,
            "secret": None,  # Never include secret in list
        }
        result.append(WebhookResponse(**webhook_dict))

    return result


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook subscription",
    description="""
Creates a new webhook subscription to receive real-time events.

**⚠️ IMPORTANT:** The webhook secret is returned ONLY ONCE in this response.
Make sure to save it securely, as it cannot be retrieved again.

**Event Types:**
Subscribe to specific event types to filter the events you receive:

- **Stream Events:**
  - `stream.started` - A stream has started
  - `stream.ended` - A stream has ended
  - `stream.error` - A stream encountered an error
  - `stream.paused` - A stream has been paused
  - `stream.resumed` - A paused stream has resumed

- **Channel Events:**
  - `channel.created` - A channel was created
  - `channel.deleted` - A channel was deleted
  - `channel.updated` - A channel was updated

- **Viewer Events:**
  - `viewer.milestone` - Viewer count milestone reached
  - `viewer.joined` - A new viewer joined (if tracking enabled)
  - `viewer.left` - A viewer left (if tracking enabled)

- **Playlist Events:**
  - `playlist.started` - A playlist playback started
  - `playlist.ended` - A playlist playback ended
  - `playlist.item_changed` - Current item in playlist changed

**Webhook Security:**
All webhook requests include:
- `X-Webhook-Signature` - HMAC-SHA256 signature using your secret
- `X-Webhook-Event` - The event type
- `X-Webhook-ID` - Unique delivery ID
- `X-Webhook-Timestamp` - Unix timestamp of the event

**Verify Signatures:**
```python
import hmac
import hashlib

signature = hmac.new(
    secret.encode(),
    request_body.encode(),
    hashlib.sha256
).hexdigest()

# Compare with X-Webhook-Signature header
```

**Authentication:** Requires valid JWT token or session cookie
    """,
    responses={
        201: {
            "description": "Webhook subscription created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "url": "https://example.com/webhooks",
                        "event_types": ["stream.started", "stream.ended", "stream.error"],
                        "is_active": True,
                        "last_success_at": None,
                        "last_failure_at": None,
                        "failure_count": 0,
                        "created_at": "2025-01-15T10:30:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "secret": "whsec_abc123xyz456"
                    }
                }
            }
        }
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.post(
    "http://localhost:8000/api/webhooks/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},
    json={
        "url": "https://example.com/webhooks",
        "event_types": ["stream.started", "stream.ended", "stream.error"]
    }
)
webhook = response.json()
print(f"Webhook Secret (save this!): {webhook['secret']}")
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url: 'https://example.com/webhooks',
        event_types: ['stream.started', 'stream.ended', 'stream.error']
    })
});
const webhook = await response.json();
console.log('Webhook Secret (save this!):', webhook.secret);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X POST "http://localhost:8000/api/webhooks/" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://example.com/webhooks",
    "event_types": ["stream.started", "stream.ended", "stream.error"]
  }'
                """
            }
        ]
    }
)
def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)

    # Create the webhook
    webhook, secret = service.create_webhook(current_user.id, webhook_data)

    # Build response with the secret (only time it's returned)
    response_data = {
        "id": webhook.id,
        "owner_id": webhook.owner_id,
        "url": webhook.url,
        "event_types": webhook.event_types,
        "is_active": webhook.is_active,
        "last_success_at": webhook.last_success_at,
        "last_failure_at": webhook.last_failure_at,
        "failure_count": webhook.failure_count,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
        "secret": secret,  # Include secret only on creation
    }

    logger.info(f"User {current_user.id} created webhook {webhook.id}")
    return WebhookResponse(**response_data)


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook subscription details",
    description="""
Retrieves detailed information about a specific webhook subscription.

**Note:** This endpoint does NOT return the webhook secret.
Only the metadata and delivery statistics are returned.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the webhook
    """,
    responses={
        200: {
            "description": "Webhook subscription details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "url": "https://example.com/webhooks",
                        "event_types": ["stream.started", "stream.ended", "stream.error"],
                        "is_active": True,
                        "last_success_at": "2025-01-15T10:30:00Z",
                        "last_failure_at": None,
                        "failure_count": 0,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "secret": None
                    }
                }
            }
        },
        404: {"description": "Webhook not found"},
        403: {"description": "Access denied - you don't own this webhook"}
    }
)
def get_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Verify ownership
    if webhook.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Build response without the secret value
    response_data = {
        "id": webhook.id,
        "owner_id": webhook.owner_id,
        "url": webhook.url,
        "event_types": webhook.event_types,
        "is_active": webhook.is_active,
        "last_success_at": webhook.last_success_at,
        "last_failure_at": webhook.last_failure_at,
        "failure_count": webhook.failure_count,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
        "secret": None,  # Never return secret value in GET
    }

    return WebhookResponse(**response_data)


@router.patch(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook subscription",
    description="""
Updates an existing webhook subscription.

**Editable fields:**
- `url` - The webhook endpoint URL
- `event_types` - List of event types to subscribe to
- `is_active` - Enable or disable the webhook

**Note:** The webhook secret CANNOT be changed via this endpoint.
Use the `/rotate-secret` endpoint to generate a new secret.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the webhook
    """,
    responses={
        200: {
            "description": "Webhook subscription updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "url": "https://example.com/webhooks/v2",
                        "event_types": ["stream.started", "stream.ended"],
                        "is_active": True,
                        "last_success_at": "2025-01-15T10:30:00Z",
                        "last_failure_at": None,
                        "failure_count": 0,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-16T14:20:00Z",
                        "secret": None
                    }
                }
            }
        },
        404: {"description": "Webhook not found"},
        403: {"description": "Access denied"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.patch(
    "http://localhost:8000/api/webhooks/{webhook_id}",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},
    json={
        "url": "https://example.com/webhooks/v2",
        "event_types": ["stream.started", "stream.ended"],
        "is_active": True
    }
)
updated_webhook = response.json()
print(updated_webhook)
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/{webhook_id}', {
    method: 'PATCH',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url: 'https://example.com/webhooks/v2',
        event_types: ['stream.started', 'stream.ended'],
        is_active: true
    })
});
const updatedWebhook = await response.json();
console.log(updatedWebhook);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X PATCH "http://localhost:8000/api/webhooks/{webhook_id}" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://example.com/webhooks/v2",
    "event_types": ["stream.started", "stream.ended"],
    "is_active": true
  }'
                """
            }
        ]
    }
)
def update_webhook(
    webhook_id: uuid.UUID,
    webhook_update: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)

    # First verify ownership
    webhook = service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    if webhook.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update the webhook
    updated_webhook = service.update_webhook(webhook_id, webhook_update)
    if not updated_webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Build response without the secret value
    response_data = {
        "id": updated_webhook.id,
        "owner_id": updated_webhook.owner_id,
        "url": updated_webhook.url,
        "event_types": updated_webhook.event_types,
        "is_active": updated_webhook.is_active,
        "last_success_at": updated_webhook.last_success_at,
        "last_failure_at": updated_webhook.last_failure_at,
        "failure_count": updated_webhook.failure_count,
        "created_at": updated_webhook.created_at,
        "updated_at": updated_webhook.updated_at,
        "secret": None,
    }

    logger.info(f"User {current_user.id} updated webhook {webhook_id}")
    return WebhookResponse(**response_data)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook subscription",
    description="""
Permanently deletes a webhook subscription.

**⚠️ WARNING:** This action cannot be undone.
The webhook will immediately stop receiving events.

**Alternative:** Consider setting `is_active` to `false` if you want to
temporarily disable the webhook without deleting it.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the webhook
    """,
    responses={
        204: {"description": "Webhook subscription deleted successfully"},
        404: {"description": "Webhook not found"},
        403: {"description": "Access denied"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.delete(
    "http://localhost:8000/api/webhooks/{webhook_id}",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

if response.status_code == 204:
    print("Webhook deleted successfully")
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/{webhook_id}', {
    method: 'DELETE',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});

if (response.status === 204) {
    console.log('Webhook deleted successfully');
}
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X DELETE "http://localhost:8000/api/webhooks/{webhook_id}" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
                """
            }
        ]
    }
)
def delete_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)

    # First verify ownership
    webhook = service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    if webhook.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete the webhook
    success = service.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    logger.info(f"User {current_user.id} deleted webhook {webhook_id}")
    return None


@router.post(
    "/{webhook_id}/test",
    summary="Test a webhook subscription",
    description="""
Sends a test event to the webhook URL to verify it's working correctly.

**Use this endpoint to:**
- Verify your webhook endpoint is reachable
- Test signature verification
- Check response handling
- Debug webhook delivery issues

**Test Event Format:**
```json
{
  "id": "uuid",
  "type": "test",
  "test": true,
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "message": "This is a test webhook event",
    "webhook_id": "uuid"
  }
}
```

**Response includes:**
- `success` - Whether the test succeeded (HTTP 2xx status)
- `status_code` - HTTP status code from webhook endpoint
- `response_body` - Response body (truncated to 1000 chars)
- `webhook_id` - The webhook ID that was tested
- `event_id` - Unique test event ID
- `timestamp` - When the test was sent

**Note:** A successful test updates the webhook's `last_success_at` timestamp.
A failed test updates `last_failure_at` and increments `failure_count`.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the webhook
    """,
    responses={
        200: {
            "description": "Test completed (check success field for result)",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Successful test",
                            "value": {
                                "success": True,
                                "status_code": 200,
                                "response_body": "{\"received\": true}",
                                "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
                                "event_id": "test-event-uuid",
                                "timestamp": "2025-01-15T10:30:00Z"
                            }
                        },
                        "failure": {
                            "summary": "Failed test",
                            "value": {
                                "success": False,
                                "status_code": 404,
                                "response_body": "Not Found",
                                "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
                                "event_id": "test-event-uuid",
                                "timestamp": "2025-01-15T10:30:00Z"
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Webhook not found"},
        403: {"description": "Access denied"},
        408: {"description": "Webhook URL timed out"},
        500: {"description": "Failed to send test event"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.post(
    "http://localhost:8000/api/webhooks/{webhook_id}/test",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
result = response.json()

if result["success"]:
    print(f"✓ Test succeeded! Status: {result['status_code']}")
    print(f"  Response: {result['response_body']}")
else:
    print(f"✗ Test failed! Status: {result['status_code']}")
    print(f"  Error: {result['response_body']}")
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/{webhook_id}/test', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});
const result = await response.json();

if (result.success) {
    console.log(`✓ Test succeeded! Status: ${result.status_code}`);
    console.log(`  Response: ${result.response_body}`);
} else {
    console.log(`✗ Test failed! Status: ${result.status_code}`);
    console.log(`  Error: ${result.response_body}`);
}
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X POST "http://localhost:8000/api/webhooks/{webhook_id}/test" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
                """
            }
        ]
    }
)
async def test_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)

    # Verify ownership
    webhook = service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    if webhook.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Create test event payload
    test_event = {
        "id": str(uuid.uuid4()),
        "type": "test",
        "test": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook event",
            "webhook_id": str(webhook.id),
        }
    }

    # Generate signature
    signature = service.generate_signature(webhook, test_event)

    try:
        # Send test event to webhook URL
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=test_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": "test",
                    "User-Agent": "Sattva-Webhook/1.0"
                }
            )

        # Update webhook stats based on response
        if 200 <= response.status_code < 300:
            webhook.update_success()
            logger.info(f"Test webhook {webhook_id} succeeded with status {response.status_code}")
        else:
            webhook.update_failure()
            logger.warning(f"Test webhook {webhook_id} failed with status {response.status_code}")

        db.commit()

        # Return test results
        return {
            "success": response.status_code >= 200 and response.status_code < 300,
            "status_code": response.status_code,
            "response_body": response.text[:1000] if response.text else None,  # Limit response size
            "webhook_id": str(webhook.id),
            "event_id": test_event["id"],
            "timestamp": test_event["timestamp"],
        }

    except httpx.TimeoutError:
        webhook.update_failure()
        db.commit()

        logger.error(f"Test webhook {webhook_id} timed out")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Webhook URL timed out"
        )

    except httpx.HTTPError as e:
        webhook.update_failure()
        db.commit()

        logger.error(f"Test webhook {webhook_id} failed with error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test event: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Test webhook {webhook_id} failed with unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post(
    "/{webhook_id}/rotate-secret",
    response_model=WebhookResponse,
    summary="Rotate webhook secret",
    description="""
Rotates the webhook secret by generating a new one.

**⚠️ IMPORTANT:** The new secret is returned ONLY ONCE in this response.
Make sure to save it securely and update your webhook endpoint immediately.

**What happens:**
- A new secret is generated
- The old secret immediately becomes invalid
- The new secret is returned in this response (only time)

**When to use:**
- You suspect the secret has been compromised
- Regular security maintenance (recommended: rotate every 90 days)
- After a security incident

**After rotation:**
1. Update your webhook endpoint with the new secret
2. Use the new secret to verify X-Webhook-Signature headers
3. The old secret will no longer work for signature verification

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the webhook
    """,
    responses={
        200: {
            "description": "Secret rotated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "url": "https://example.com/webhooks",
                        "event_types": ["stream.started", "stream.ended", "stream.error"],
                        "is_active": True,
                        "last_success_at": "2025-01-15T10:30:00Z",
                        "last_failure_at": None,
                        "failure_count": 0,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-16T15:00:00Z",
                        "secret": "whsec_new_secret_xyz789"
                    }
                }
            }
        },
        404: {"description": "Webhook not found"},
        403: {"description": "Access denied"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.post(
    "http://localhost:8000/api/webhooks/{webhook_id}/rotate-secret",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
result = response.json()

print(f"New secret (update your endpoint immediately!): {result['secret']}")
# Update your webhook endpoint to use this new secret
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/webhooks/{webhook_id}/rotate-secret', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});
const result = await response.json();

console.log('New secret (update your endpoint immediately!):', result.secret);
// Update your webhook endpoint to use this new secret
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X POST "http://localhost:8000/api/webhooks/{webhook_id}/rotate-secret" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
# Response will contain the new secret - save it immediately!
                """
            }
        ]
    }
)
def rotate_webhook_secret(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WebhookService(db)

    # First verify ownership
    webhook = service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    if webhook.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Rotate the secret
    result = service.rotate_secret(webhook_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    updated_webhook, new_secret = result

    # Build response with the new secret (only time it's returned)
    response_data = {
        "id": updated_webhook.id,
        "owner_id": updated_webhook.owner_id,
        "url": updated_webhook.url,
        "event_types": updated_webhook.event_types,
        "is_active": updated_webhook.is_active,
        "last_success_at": updated_webhook.last_success_at,
        "last_failure_at": updated_webhook.last_failure_at,
        "failure_count": updated_webhook.failure_count,
        "created_at": updated_webhook.created_at,
        "updated_at": updated_webhook.updated_at,
        "secret": new_secret,  # Include new secret only on rotation
    }

    logger.info(f"User {current_user.id} rotated secret for webhook {webhook_id}")
    return WebhookResponse(**response_data)
