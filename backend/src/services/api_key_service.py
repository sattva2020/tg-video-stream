"""
API Key Service
Spec: 026-api-webhook-ecosystem

Service for API key management including generation, hashing, and validation.
"""
import hashlib
import secrets
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.api_key import APIKey
from src.schemas.api_key import APIKeyCreate, APIKeyUpdate

logger = logging.getLogger(__name__)

# API key prefix and length
API_KEY_PREFIX = "sk_"
API_KEY_LENGTH = 32  # 32 bytes = 256 bits


class APIKeyService:
    """Service for API key management."""

    def __init__(self, db: Session):
        self.db = db

    def list_keys(
        self,
        owner_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> List[APIKey]:
        """List API keys with optional filters."""
        query = self.db.query(APIKey)
        if owner_id is not None:
            query = query.filter(APIKey.owner_id == owner_id)
        if is_active is not None:
            query = query.filter(APIKey.is_active == is_active)
        return query.order_by(APIKey.created_at.desc()).all()

    def get_key(self, key_id: UUID) -> Optional[APIKey]:
        """Get an API key by ID."""
        return self.db.get(APIKey, key_id)

    def get_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get an API key by its hash (used for authentication)."""
        return self.db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    def create_key(self, owner_id: UUID, data: APIKeyCreate) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Returns:
            tuple: (APIKey object, raw_key value)
            Note: The raw key is only returned once during creation.
        """
        # Generate the API key
        raw_key = self._generate_key()

        # Hash the key for storage
        key_hash = self._hash_key(raw_key)

        # Create the API key record
        api_key = APIKey(
            key_hash=key_hash,
            name=data.name,
            owner_id=owner_id,
            scopes=data.scopes,
            rate_limit=data.rate_limit,
            expires_at=data.expires_at,
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        logger.info(f"Created API key {api_key.id} for owner {owner_id}")
        return api_key, raw_key

    def update_key(self, key_id: UUID, data: APIKeyUpdate) -> Optional[APIKey]:
        """Update an existing API key."""
        api_key = self.get_key(key_id)
        if not api_key:
            return None

        # Update fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(api_key, field, value)

        self.db.commit()
        self.db.refresh(api_key)

        logger.info(f"Updated API key {key_id}")
        return api_key

    def delete_key(self, key_id: UUID) -> bool:
        """Delete an API key."""
        api_key = self.get_key(key_id)
        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()

        logger.info(f"Deleted API key {key_id}")
        return True

    def revoke_key(self, key_id: UUID) -> Optional[APIKey]:
        """Revoke an API key by setting is_active to False."""
        api_key = self.get_key(key_id)
        if not api_key:
            return None

        api_key.is_active = False
        self.db.commit()
        self.db.refresh(api_key)

        logger.info(f"Revoked API key {key_id}")
        return api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key string

        Returns:
            APIKey object if valid, None otherwise
        """
        # Check key format
        if not raw_key.startswith(API_KEY_PREFIX):
            logger.warning(f"Invalid API key format: missing prefix")
            return None

        # Hash the key
        key_hash = self._hash_key(raw_key)

        # Look up the key
        api_key = self.get_key_by_hash(key_hash)
        if not api_key:
            logger.warning(f"API key not found")
            return None

        # Check if key is valid (active and not expired)
        if not api_key.is_valid():
            logger.warning(f"API key {api_key.id} is inactive or expired")
            return None

        # Update last used timestamp
        api_key.update_last_used()
        self.db.commit()

        return api_key

    def check_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if an API key has a specific scope."""
        return api_key.has_scope(required_scope)

    def check_scopes(self, api_key: APIKey, required_scopes: List[str], require_all: bool = False) -> bool:
        """
        Check if an API key has the required scopes.

        Args:
            api_key: The API key to check
            required_scopes: List of required scopes
            require_all: If True, all scopes must be present. If False, any scope is sufficient.

        Returns:
            True if the key has the required scopes, False otherwise
        """
        if require_all:
            return api_key.has_all_scopes(required_scopes)
        else:
            return api_key.has_any_scope(required_scopes)

    def _generate_key(self) -> str:
        """
        Generate a new API key.

        The key format is: sk_<random_bytes>
        where random_bytes are URL-safe base64 encoded.
        """
        # Generate cryptographically secure random bytes
        random_bytes = secrets.token_urlsafe(API_KEY_LENGTH)

        # Combine with prefix
        return f"{API_KEY_PREFIX}{random_bytes}"

    def _hash_key(self, raw_key: str) -> str:
        """
        Hash an API key for storage.

        Uses SHA-256 to create a one-way hash of the key.
        """
        return hashlib.sha256(raw_key.encode()).hexdigest()
