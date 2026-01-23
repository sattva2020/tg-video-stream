"""
Webhook Service
Spec: 026-api-webhook-ecosystem

Service for webhook subscription management, signature generation, and event triggering.
"""
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.webhook import Webhook
from src.models.webhook_event import WebhookEvent
from src.schemas.webhook import WebhookCreate, WebhookUpdate

logger = logging.getLogger(__name__)

# Webhook secret length
WEBHOOK_SECRET_LENGTH = 32  # 32 bytes = 256 bits

# Maximum retries for webhook delivery
MAX_WEBHOOK_RETRIES = 5


class WebhookService:
    """Service for webhook subscription management."""

    def __init__(self, db: Session):
        self.db = db

    def list_webhooks(
        self,
        owner_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        event_type: Optional[str] = None,
    ) -> List[Webhook]:
        """List webhook subscriptions with optional filters."""
        query = self.db.query(Webhook)
        if owner_id is not None:
            query = query.filter(Webhook.owner_id == owner_id)
        if is_active is not None:
            query = query.filter(Webhook.is_active == is_active)
        if event_type is not None:
            # Use JSON contains for PostgreSQL/SQLite compatibility
            query = query.filter(Webhook.event_types.contains(event_type))
        return query.order_by(Webhook.created_at.desc()).all()

    def get_webhook(self, webhook_id: UUID) -> Optional[Webhook]:
        """Get a webhook subscription by ID."""
        return self.db.get(Webhook, webhook_id)

    def create_webhook(self, owner_id: UUID, data: WebhookCreate) -> tuple[Webhook, str]:
        """
        Create a new webhook subscription.

        Returns:
            tuple: (Webhook object, secret value)
            Note: The secret is only returned once during creation.
        """
        # Generate the webhook secret
        secret = self._generate_secret()

        # Create the webhook subscription
        webhook = Webhook(
            url=data.url,
            event_types=data.event_types,
            secret=secret,
            owner_id=owner_id,
            is_active=True,
            failure_count=0,
        )

        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Created webhook {webhook.id} for owner {owner_id}")
        return webhook, secret

    def update_webhook(self, webhook_id: UUID, data: WebhookUpdate) -> Optional[Webhook]:
        """Update an existing webhook subscription."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        # Update fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(webhook, field, value)

        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Updated webhook {webhook_id}")
        return webhook

    def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook subscription."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False

        self.db.delete(webhook)
        self.db.commit()

        logger.info(f"Deleted webhook {webhook_id}")
        return True

    def disable_webhook(self, webhook_id: UUID) -> Optional[Webhook]:
        """Disable a webhook subscription by setting is_active to False."""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        webhook.is_active = False
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Disabled webhook {webhook_id}")
        return webhook

    def get_webhooks_for_event(self, event_type: str, owner_id: Optional[UUID] = None) -> List[Webhook]:
        """
        Get all active webhook subscriptions for a specific event type.

        Args:
            event_type: The event type (e.g., "stream.started")
            owner_id: Optional owner ID to filter by

        Returns:
            List of active webhook subscriptions subscribed to this event type
        """
        query = self.db.query(Webhook).filter(
            Webhook.is_active == True,
            Webhook.event_types.contains(event_type)
        )

        # Only return healthy webhooks
        webhooks = []
        for webhook in query.all():
            if webhook.is_healthy:
                webhooks.append(webhook)
            else:
                logger.warning(f"Webhook {webhook.id} is unhealthy, skipping delivery")

        return webhooks

    def trigger_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        event_id: Optional[str] = None,
        owner_id: Optional[UUID] = None,
    ) -> List[WebhookEvent]:
        """
        Trigger an event to all subscribed webhooks.

        This method creates WebhookEvent records for each subscription.
        The actual delivery is handled by the webhook worker.

        Args:
            event_type: The event type (e.g., "stream.started")
            event_data: The event payload data
            event_id: Optional unique event ID for deduplication
            owner_id: Optional owner ID to filter webhooks

        Returns:
            List of created WebhookEvent records
        """
        # Get all webhooks subscribed to this event
        webhooks = self.get_webhooks_for_event(event_type, owner_id)

        if not webhooks:
            logger.info(f"No webhooks subscribed to event type: {event_type}")
            return []

        events = []
        for webhook in webhooks:
            # Create a webhook event record for delivery tracking
            webhook_event = WebhookEvent(
                webhook_id=webhook.id,
                event_type=event_type,
                event_id=event_id,
                status="pending",
                attempt_number=1,
            )

            self.db.add(webhook_event)
            events.append(webhook_event)

        self.db.commit()

        # Refresh to get IDs
        for event in events:
            self.db.refresh(event)

        logger.info(f"Created {len(events)} webhook event records for {event_type}")
        return events

    def get_webhook_events(
        self,
        webhook_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[WebhookEvent]:
        """
        Get webhook event records with optional filters.

        Args:
            webhook_id: Filter by webhook ID
            event_type: Filter by event type
            status: Filter by status (pending, success, failed, retrying)
            limit: Maximum number of records to return

        Returns:
            List of webhook event records
        """
        query = self.db.query(WebhookEvent)

        if webhook_id is not None:
            query = query.filter(WebhookEvent.webhook_id == webhook_id)
        if event_type is not None:
            query = query.filter(WebhookEvent.event_type == event_type)
        if status is not None:
            query = query.filter(WebhookEvent.status == status)

        return query.order_by(WebhookEvent.attempted_at.desc()).limit(limit).all()

    def generate_signature(self, webhook: Webhook, payload: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for a webhook payload.

        Args:
            webhook: The webhook subscription
            payload: The payload data to sign

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        # Convert payload to JSON string
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)

        # Generate HMAC signature using the webhook secret
        signature = hmac.new(
            webhook.secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, webhook: Webhook, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature for a webhook payload.

        Args:
            webhook: The webhook subscription
            payload: The payload data to verify
            signature: The signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        # Generate the expected signature
        expected_signature = self.generate_signature(webhook, payload)

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)

    def rotate_secret(self, webhook_id: UUID) -> Optional[tuple[Webhook, str]]:
        """
        Rotate the webhook secret.

        This generates a new secret for the webhook subscription.
        The old secret will no longer work for signature verification.

        Args:
            webhook_id: The webhook ID

        Returns:
            tuple: (Webhook object, new_secret) or None if webhook not found
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        # Generate new secret
        new_secret = self._generate_secret()
        webhook.secret = new_secret

        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Rotated secret for webhook {webhook_id}")
        return webhook, new_secret

    def get_delivery_stats(self, webhook_id: UUID) -> Dict[str, Any]:
        """
        Get delivery statistics for a webhook subscription.

        Args:
            webhook_id: The webhook ID

        Returns:
            Dictionary with delivery statistics
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return {}

        # Get recent events
        recent_events = self.get_webhook_events(
            webhook_id=webhook_id,
            limit=100
        )

        # Calculate statistics
        total_events = len(recent_events)
        successful_events = sum(1 for e in recent_events if e.status == "success")
        failed_events = sum(1 for e in recent_events if e.status == "failed")
        pending_events = sum(1 for e in recent_events if e.status == "pending")

        # Calculate success rate
        success_rate = (successful_events / total_events * 100) if total_events > 0 else 0

        # Get average response time (for successful events)
        response_times = [e.duration_ms for e in recent_events if e.duration_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        return {
            "webhook_id": str(webhook_id),
            "total_events": total_events,
            "successful_events": successful_events,
            "failed_events": failed_events,
            "pending_events": pending_events,
            "success_rate": round(success_rate, 2),
            "average_response_time_ms": avg_response_time,
            "current_failure_count": webhook.failure_count,
            "is_healthy": webhook.is_healthy,
            "last_success_at": webhook.last_success_at,
            "last_failure_at": webhook.last_failure_at,
        }

    def _generate_secret(self) -> str:
        """
        Generate a new webhook secret.

        Returns a URL-safe base64 encoded random string.
        """
        # Generate cryptographically secure random bytes
        random_bytes = secrets.token_urlsafe(WEBHOOK_SECRET_LENGTH)

        return random_bytes
