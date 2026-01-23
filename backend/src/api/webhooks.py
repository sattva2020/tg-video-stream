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


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all webhook subscriptions owned by the current user.

    Returns a list of webhook subscriptions with their metadata.
    The secret is never included in list responses.
    """
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


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new webhook subscription.

    The webhook secret is returned only once in the response.
    Make sure to save it securely, as it cannot be retrieved again.
    """
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


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific webhook subscription by ID.

    Returns the webhook metadata but not the secret value.
    """
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


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: uuid.UUID,
    webhook_update: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a webhook subscription.

    Can update url, event_types, and is_active.
    The secret cannot be changed via update (use rotate_secret instead).
    """
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


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a webhook subscription permanently.

    This action cannot be undone. The webhook will immediately stop receiving events.
    """
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


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a test event to a webhook subscription.

    This sends a test event to the webhook URL to verify it's working correctly.
    Returns the response status and details from the webhook endpoint.
    """
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


@router.post("/{webhook_id}/rotate-secret", response_model=WebhookResponse)
def rotate_webhook_secret(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rotate the webhook secret.

    Generates a new secret for the webhook subscription.
    The old secret will no longer work for signature verification.
    The new secret is returned only once in the response.
    """
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
