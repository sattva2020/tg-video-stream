"""
Webhook Model
Spec: 026-api-webhook-ecosystem

Model for storing webhook subscriptions with event filtering and signature verification.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, text, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from src.database import Base, GUID


class JSONBCompat(TypeDecorator):
    """Use JSONB on PostgreSQL and JSON elsewhere for test compatibility."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Webhook(Base):
    """Webhook subscription for event notifications."""

    __tablename__ = "webhooks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Owner of the webhook subscription
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Webhook endpoint URL
    url = Column(String(2048), nullable=False)

    # Event types to subscribe to
    # Example: ["stream.started", "stream.stopped", "viewer.milestone"]
    event_types = Column(JSONBCompat, nullable=False, default=list)

    # Secret for HMAC-SHA256 signature verification
    # Generated on creation and used to sign webhook payloads
    secret = Column(String(255), nullable=False)

    # Webhook status
    is_active = Column(Boolean, nullable=False, server_default=text('true'), default=True)

    # Track delivery statistics
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, nullable=False, server_default=text('0'), default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", backref="webhooks")

    def __repr__(self):
        return f"<Webhook(id='{self.id}', url='{self.url}', owner_id='{self.owner_id}')>"

    def is_subscribed_to(self, event_type: str) -> bool:
        """Check if this webhook is subscribed to a specific event type."""
        if not self.event_types:
            return False
        return event_type in self.event_types

    def update_success(self) -> None:
        """Update last successful delivery timestamp and reset failure count."""
        self.last_success_at = datetime.now(timezone.utc)
        self.failure_count = 0

    def update_failure(self) -> None:
        """Update last failure timestamp and increment failure count."""
        self.last_failure_at = datetime.now(timezone.utc)
        self.failure_count = (self.failure_count or 0) + 1

    @property
    def is_healthy(self) -> bool:
        """Check if webhook is healthy (recent success or low failure count)."""
        if not self.is_active:
            return False
        # Consider unhealthy if there are more than 10 consecutive failures
        if self.failure_count and self.failure_count > 10:
            return False
        return True
