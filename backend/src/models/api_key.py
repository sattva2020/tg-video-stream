"""
API Key Model
Spec: 026-api-webhook-ecosystem

Model for storing API keys with per-key rate limiting and scopes.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, text, JSON, ForeignKey
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
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON())


class APIKeyScope(str):
    """Available API key scopes."""

    # Stream operations
    READ_STREAMS = "read:streams"
    WRITE_STREAMS = "write:streams"

    # Playlist operations
    READ_PLAYLISTS = "read:playlists"
    WRITE_PLAYLISTS = "write:playlists"

    # Schedule operations
    READ_SCHEDULES = "read:schedules"
    WRITE_SCHEDULES = "write:schedules"

    # Analytics operations
    READ_ANALYTICS = "read:analytics"

    # Webhook operations
    READ_WEBHOOKS = "read:webhooks"
    WRITE_WEBHOOKS = "write:webhooks"

    # Admin operations
    ADMIN = "admin"


class APIKey(Base):
    """API key for external access with rate limiting and scopes."""

    __tablename__ = "api_keys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # API key identifier (hashed version of the actual key)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)

    # Human-readable name for the key
    name = Column(String(255), nullable=False)

    # Owner of the API key
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Scopes - list of permissions granted to this key
    # Example: ["read:streams", "write:playlists"]
    scopes = Column(JSONBCompat, nullable=False, default=list)

    # Rate limiting configuration
    # Example: {"requests": 100, "window": 60}  (100 requests per 60 seconds)
    rate_limit = Column(JSONBCompat, nullable=True)

    # Key status
    is_active = Column(Boolean, nullable=False, server_default=text('true'), default=True)

    # Optional expiration date
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Track last usage
    last_used = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", backref="api_keys")

    def __repr__(self):
        return f"<APIKey(id='{self.id}', name='{self.name}', owner_id='{self.owner_id}')>"

    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def has_scope(self, scope: str) -> bool:
        """Check if the API key has a specific scope."""
        if not self.scopes:
            return False
        return scope in self.scopes

    def has_any_scope(self, required_scopes: list[str]) -> bool:
        """Check if the API key has any of the required scopes."""
        if not self.scopes:
            return False
        return any(scope in self.scopes for scope in required_scopes)

    def has_all_scopes(self, required_scopes: list[str]) -> bool:
        """Check if the API key has all of the required scopes."""
        if not self.scopes:
            return False
        return all(scope in self.scopes for scope in required_scopes)

    def update_last_used(self) -> None:
        """Update the last_used timestamp to current time."""
        self.last_used = datetime.now(timezone.utc)
