import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, func, BigInteger
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class QuotaType(str, PyEnum):
    """Types of resource quotas."""
    STREAMS = "streams"
    STORAGE_BYTES = "storage_bytes"
    BANDWIDTH_BYTES = "bandwidth_bytes"
    USERS = "users"
    API_CALLS = "api_calls"
    PLAYLISTS = "playlists"
    SCHEDULED_PLAYLISTS = "scheduled_playlists"


class ResourceQuota(Base):
    """Resource quota model for managing organization resource limits."""
    __tablename__ = "resource_quotas"
    __table_args__ = (
        {"schema": None},
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), nullable=False)
    quota_type = Column(String(50), nullable=False)
    limit = Column(BigInteger, nullable=False)
    current_usage = Column(BigInteger, nullable=False, default=0, server_default='0')
    period = Column(String(20), nullable=True)  # e.g., 'monthly', 'daily', 'hourly', None for lifetime
    reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ResourceQuota(id='{self.id}', org_id='{self.organization_id}', type='{self.quota_type}', limit={self.limit})>"

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as a percentage."""
        if self.limit == 0:
            return 0.0
        return (self.current_usage / self.limit) * 100

    @property
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.current_usage >= self.limit

    @property
    def remaining(self) -> int:
        """Get remaining quota amount."""
        return max(0, self.limit - self.current_usage)

    def increment_usage(self, amount: int = 1) -> None:
        """Increment current usage."""
        self.current_usage += amount

    def decrement_usage(self, amount: int = 1) -> None:
        """Decrement current usage (won't go below 0)."""
        self.current_usage = max(0, self.current_usage - amount)

    def reset_usage(self) -> None:
        """Reset current usage to 0."""
        self.current_usage = 0
